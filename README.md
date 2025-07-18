# 🔐 Smart Home Intrusion Detection System

A smart security system built using **ESP32**, **Firebase**, **Blynk IoT**, and **keypad authentication**. It detects motion, controls a relay-based locking mechanism, and updates status on an LCD and mobile app. The system also supports remote monitoring and control.

---

## 🚀 Features

- 🕵️ Motion detection using PIR sensor
- 🔐 Keypad-based PIN authentication for door lock/unlock
- 📱 Remote control and monitoring via Blynk App
- ☁️ Real-time Firebase integration for storing motion and lock status
- 🔊 Relay triggers (e.g., for alarms or lights)
- 💡 LCD feedback for lock status and motion alerts

---

## 🛠️ Technologies Used

- **Hardware**:
  - ESP32 Dev Board
  - PIR Motion Sensor
  - 4x4 Matrix Keypad
  - 20x4 I2C LCD
  - Relay Module
  - LEDs (Green for unlock indicator)
  
- **Software**:
  - PlatformIO / Arduino IDE
  - Blynk Library
  - FirebaseESP32 Library
  - Keypad & LiquidCrystal_I2C Libraries

---

## 📲 Blynk Setup

1. Create a new project in the Blynk app.
2. Set up the following virtual pins:
   - `V0` – Motion Indicator (LED)
   - `V1` – Motion Status (Label)
   - `V2` – Lock/Unlock (Button)
   - `V3` – Choice Selector (Button or Switch)
3. Use this template info:
   - **Template ID**: `TMPL617XqbQtd`
   - **Template Name**: `Smart Home Security System`
   - **Auth Token**: *(Get from Blynk app and update in code)*

---

## 🔧 Firebase Setup

1. Go to [Firebase Console](https://console.firebase.google.com/).
2. Create a new Realtime Database project.
3. Enable **Realtime Database** and set rules to public for testing (or configure secure rules for production).
4. Copy your database URL and API Key:
   - **Database URL**: `https://intrusionsystem-b0338-default-rtdb.firebaseio.com`
   - **API Key**: *(Get from Firebase project settings)*

---

## 📟 Keypad Functionality

- Enter 4-digit PIN followed by `#` to unlock (Default PIN: `125D`)
- Press `*` to lock the door again
- Press `C` to clear/delete a character

---

## 🔌 Wiring Overview

| Component         | ESP32 Pin |
|------------------|-----------|
| PIR Sensor       | GPIO 33   |
| Relay            | GPIO 4    |
| Keypad Rows      | 12, 13, 14, 19 |
| Keypad Columns   | 32, 18, 25, 26 |
| Green LED        | GPIO 5    |
| I2C LCD          | SDA/SCL (default: 0x27) |

---

## 🔁 How It Works

1. System waits for motion input.
2. On motion detected:
   - Activates relay and LED
   - Displays message on LCD
   - Sends alert to Blynk
   - Updates Firebase `/motion` value
3. Door unlocks on valid PIN input or Blynk app command.
4. Door locks via keypad `*` or Blynk toggle.
5. Firebase `/choice` value is synced periodically.

---

## 🧠 Future Improvements

- Add camera module for snapshots
- SMS/email alerts via IFTTT
- Biometric or RFID-based access
- Add encryption for Firebase and Blynk communication

---

## 📸 Screenshot

> *<img width="1449" height="608" alt="image" src="https://github.com/user-attachments/assets/c9e30328-e30c-4608-bef3-e8ba74c89583" />*
> *<img width="1568" height="831" alt="image" src="https://github.com/user-attachments/assets/a53a8882-bd4e-4d41-9bf9-955824687607" />*


---

