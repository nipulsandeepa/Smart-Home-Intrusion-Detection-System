import asyncio
import cv2
import firebase_admin
from firebase_admin import credentials, db
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update, Message
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import time
from queue import Queue
from telegram.error import TelegramError, TimedOut
import os

# --- CONFIG ---
BOT_TOKEN = '7959551140:AAGKgNRWLl2DDZKub1L0szSOj2AsTD8bfjQ'
CHAT_ID = '7620745039'
FIREBASE_KEY_PATH = 'serviceAccountKey.json'
FIREBASE_DB_URL = 'https://intrusionsystem-b0338-default-rtdb.firebaseio.com/'

# --- GLOBALS ---
waiting_for_user = False
user_responded = False
response_timeout = 30  # seconds
motion_queue = Queue()
telegram_queue = Queue()

# --- INIT FIREBASE WITH RETRY ---
def initialize_firebase():
    max_retries = 3
    retry_delay = 5
    for attempt in range(max_retries):
        print(f"[SYSTEM] Initializing Firebase (Attempt {attempt + 1}/{max_retries})...")
        try:
            cred = credentials.Certificate(FIREBASE_KEY_PATH)
            firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_DB_URL})
            db.reference('test').set('connected')
            print("[SYSTEM] Firebase test write successful.")
            return True
        except Exception as e:
            print(f"[ERROR] Firebase initialization failed: {e}")
            if attempt < max_retries - 1:
                print(f"[SYSTEM] Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("[ERROR] Max retries reached. Firebase not initialized.")
                return False
    return False

firebase_initialized = initialize_firebase()
if not firebase_initialized:
    print("[SYSTEM] Proceeding without Firebase. Motion detection will not work.")

# --- INIT TELEGRAM BOT ---
bot = Bot(token=BOT_TOKEN)  # Removed defaults for compatibility
print("[SYSTEM] Telegram bot initialized.")

# --- COMPRESS SNAPSHOT ---
def compress_snapshot(filename='snapshot.jpg', quality=50):
    try:
        img = cv2.imread(filename)
        cv2.imwrite(filename, img, [cv2.IMWRITE_JPEG_QUALITY, quality])
        file_size = os.path.getsize(filename) / 1024  # Size in KB
        print(f"[CAMERA] Snapshot compressed with quality {quality}, size: {file_size:.2f} KB")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to compress snapshot: {e}")
        return False

# --- TAKE SNAPSHOT ---
def capture_snapshot(filename='snapshot.jpg'):
    print("[CAMERA] Activating webcam...")
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[ERROR] Webcam not accessible.")
            return False
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(filename, frame)
            print("[CAMERA] Snapshot saved.")
            compress_snapshot(filename)  # Compress the image
            cap.release()
            return True
        else:
            print("[ERROR] Failed to capture snapshot.")
            cap.release()
            return False
    except Exception as e:
        print(f"[ERROR] Snapshot capture failed: {e}")
        if 'cap' in locals():
            cap.release()
        return False

# --- SEND SNAPSHOT TO TELEGRAM WITH COUNTDOWN ---
async def send_photo_with_buttons():
    global waiting_for_user, user_responded
    waiting_for_user = True
    user_responded = False

    print("[BOT] Preparing to send photo to Telegram...")
    if not capture_snapshot():
        print("[ERROR] Aborting send due to snapshot failure.")
        waiting_for_user = False
        telegram_queue.put(('text', "Snapshot capture failed."))
        return

    buttons = [
        [InlineKeyboardButton("✅ Accept", callback_data='accept')],
        [InlineKeyboardButton("❌ Reject", callback_data='reject')]
    ]
    markup = InlineKeyboardMarkup(buttons)

    max_retries = 3
    base_delay = 2
    for attempt in range(max_retries):
        try:
            with open('snapshot.jpg', 'rb') as photo:
                sent_msg: Message = await bot.send_photo(
                    chat_id=CHAT_ID,
                    photo=photo,
                    caption=f"Time left: {response_timeout}s",
                    reply_markup=markup
                )
            print("[BOT] Snapshot sent with buttons and countdown.")
            break
        except TimedOut as e:
            delay = base_delay * (2 ** attempt)  # Exponential backoff: 2, 4, 8 seconds
            print(f"[ERROR] Photo send timed out (Attempt {attempt + 1}/{max_retries}): {e}, retrying in {delay}s")
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
            else:
                print("[ERROR] Max retries reached. Sending fallback text message.")
                telegram_queue.put(('text', "Failed to send snapshot due to timeout."))
                waiting_for_user = False
                return
        except TelegramError as e:
            print(f"[ERROR] Telegram error: {e}")
            waiting_for_user = False
            telegram_queue.put(('text', f"Failed to send snapshot: {e}"))
            return

    for i in range(response_timeout, -1, -1):
        if user_responded:
            print("[BOT] User responded within time.")
            return
        try:
            await sent_msg.edit_caption(
                caption=f"Time left: {i}s",
                reply_markup=markup
            )
            print(f"[BOT] Updated countdown: {i}s")
        except TelegramError as e:
            print(f"[ERROR] Failed to update countdown: {e}")
        await asyncio.sleep(1)

    if not user_responded:
        print("[TIMEOUT] No response within 30 seconds.")
        try:
            telegram_queue.put(('text', "⏱ Timeout. No response received."))
            await sent_msg.edit_caption(
                caption="⏱ Timeout. No response received.",
                reply_markup=None
            )
            if firebase_initialized:
                db.reference('motion').set(False)
                db.reference('choice').set(False)
                print("[FIREBASE] 'motion' and 'choice' reset due to timeout.")
        except TelegramError as e:
            print(f"[ERROR] Failed to handle timeout: {e}")
        waiting_for_user = False

# --- TELEGRAM QUEUE PROCESSOR ---
async def process_telegram_queue():
    while True:
        if not telegram_queue.empty():
            msg_type, content = telegram_queue.get()
            try:
                if msg_type == 'text':
                    await bot.send_message(chat_id=CHAT_ID, text=content)
                    print(f"[BOT] Sent text message: {content}")
            except TelegramError as e:
                print(f"[ERROR] Failed to send text message: {e}")
        await asyncio.sleep(0.1)

# --- HANDLE BUTTON CLICKS ---
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global waiting_for_user, user_responded
    query = update.callback_query
    print(f"[DEBUG] Button clicked: callback_data={query.data}, user={query.from_user.id}")
    choice = query.data
    await query.answer()

    user_responded = True
    waiting_for_user = False

    if firebase_initialized:
        try:
            choice_ref = db.reference('choice')
            motion_ref = db.reference('motion')
            if choice == 'accept':
                print("[USER] ✅ Access accepted by user.")
                choice_ref.set(True)
                print("[FIREBASE] 'choice' set to true.")
                await asyncio.sleep(5)
            else:
                print("[USER] ❌ Access rejected by user.")
                choice_ref.set(False)
                print("[FIREBASE] 'choice' set to false.")

            motion_ref.set(False)
            choice_ref.set(False)
            print("[FIREBASE] 'motion' and 'choice' reset after response.")
        except Exception as e:
            print(f"[ERROR] Failed to update Firebase: {e}")

# --- HANDLE GENERIC UPDATES FOR DEBUGGING ---
async def handle_updates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"[DEBUG] Update received: {update}")
    if update.message:
        print(f"[DEBUG] Chat ID: {update.message.chat_id}")

# --- TEST TELEGRAM CONNECTIVITY ---
async def test_telegram():
    try:
        await bot.send_message(chat_id=CHAT_ID, text="Test message from bot")
        print("[TEST] Telegram test message sent successfully.")
    except TelegramError as e:
        print(f"[ERROR] Telegram test failed: {e}")

# --- MONITOR FIREBASE MOTION ---
async def monitor_firebase():
    global waiting_for_user
    if not firebase_initialized:
        print("[ERROR] Firebase not initialized. Cannot monitor motion.")
        return

    async def process_motion_queue():
        while True:
            if not motion_queue.empty():
                status = motion_queue.get()
                print(f"[FIREBASE] Processing motion event: {status}, type: {type(status)}, waiting_for_user: {waiting_for_user}")
                if status is True and not waiting_for_user:
                    print("[FIREBASE] Motion detected (motion: True)")
                    await send_photo_with_buttons()
                elif status is True and waiting_for_user:
                    print("[SYSTEM] Motion True, but waiting for user response. Ignored.")
                else:
                    print(f"[DEBUG] No action needed for status: {status}")
            await asyncio.sleep(0.1)

    def stream_handler(event):
        status = event.data
        print(f"[FIREBASE] Stream event received: {status}, type: {type(status)}")
        motion_queue.put(status)

    try:
        motion_ref = db.reference('motion')
        motion_ref.listen(stream_handler)
        print("[SYSTEM] Firebase motion stream started.")
        await process_motion_queue()
    except Exception as e:
        print(f"[ERROR] Firebase stream failed: {e}")

# --- MAIN APP ---
async def main():
    print("[SYSTEM] Starting main application...")
    await test_telegram()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_updates))

    if firebase_initialized:
        def choice_listener(event):
            print(f"[FIREBASE] 'choice' updated: {event.data}")
        db.reference('choice').listen(choice_listener)

    async with app:
        print("[SYSTEM] Telegram bot running. Polling for updates...")
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        asyncio.create_task(process_telegram_queue())
        await monitor_firebase()

if __name__ == '__main__':
    asyncio.run(main())