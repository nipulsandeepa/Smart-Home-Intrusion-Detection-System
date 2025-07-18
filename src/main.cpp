#define BLYNK_TEMPLATE_ID "TMPL617XqbQtd"
#define BLYNK_TEMPLATE_NAME "Smart Home Security System"
#define BLYNK_AUTH_TOKEN "kpLOjqRl0gw1CRu-z0V84iPTeJ24uXSm"

#define BLYNK_PRINT Serial

#include <WiFi.h>
#include <WiFiClient.h>
#include <BlynkSimpleEsp32.h>
#include <Keypad.h>
#include <LiquidCrystal_I2C.h>
//#include <ESP32Servo.h>
#include <FirebaseESP32.h>
#include "addons/TokenHelper.h"
// Provide the RTDB payload printing info and other helper functions.
#include "addons/RTDBHelper.h"

// Firebase configuration
#define FIREBASE_HOST "intrusionsystem-b0338-default-rtdb.firebaseio.com"
#define API_KEY "AIzaSyDSDEeU0Z6WlJbtXtCLgFu7BTj635PjyzM"

const char* ssid = "Wokwi-GUEST";
const char* pass = "";
bool signupOK = false;

int relay1 = 4;
const int motionsensor = 33;
int pinStateCurrent = LOW;
int pinStatePrevious = LOW;
int status1 = LOW;
int inputPin = 27;

BlynkTimer timer;
FirebaseData fbdo;
FirebaseConfig config;
FirebaseAuth auth;

LiquidCrystal_I2C lcd(0x27, 20, 4);

const byte ROWS = 4;
const byte COLS = 4;
char keys[ROWS][COLS] = {
  {'1', '2', '3', 'A'},
  {'4', '5', '6', 'B'},
  {'7', '8', '9', 'C'},
  {'*', '0', '#', 'D'}
};
byte rowPins[ROWS] = {12, 13, 14, 19};
byte colPins[COLS] = {32, 18, 25, 26};

Keypad keypad = Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);
//Servo myServo;
// const int servoPin = 27;
bool locked = true;
char enteredCode[5];
int codeIndex = 0;

int gled = 5;

void updateLockStatus();
void handleKeypadInput(char key);
void unlockDoor();
void lockDoor();
void checkFirebaseChoice();

BLYNK_CONNECTED() {
  Blynk.syncVirtual(V0);
  Blynk.syncVirtual(V1);
  Blynk.syncVirtual(V2);
  Blynk.syncVirtual(V3);
}

void setup() {
  Serial.begin(115200);
  Blynk.begin(BLYNK_AUTH_TOKEN, ssid, pass);

  pinMode(gled, OUTPUT);
  pinMode(motionsensor, INPUT);
  pinMode(relay1, OUTPUT);
  digitalWrite(relay1, HIGH);
  delay(1000);
  digitalWrite(relay1, LOW);

  //myServo.attach(servoPin);
  lcd.init();
  lcd.backlight();
  updateLockStatus();

  config.api_key = API_KEY;
  config.database_url = FIREBASE_HOST;
  
  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);

  timer.setInterval(5000L, checkFirebaseChoice);
  Serial.println("Setup complete");

  if (Firebase.signUp(&config, &auth, "", "")) {
    Serial.println("Firebase signup OK");
    signupOK = true;
  } else {
    Serial.printf("Firebase signup failed: %s\n", config.signer.signupError.message.c_str());
  }
  
  // Assign the callback function for the long running token generation task
  config.token_status_callback = tokenStatusCallback;
  
  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);
}

void loop() {
  Blynk.run();
  timer.run();

  pinStatePrevious = pinStateCurrent;
  pinStateCurrent = digitalRead(motionsensor);

  if (pinStatePrevious == LOW && pinStateCurrent == HIGH) {
    Serial.println("Motion detected, turning relay ON");
    digitalWrite(relay1, HIGH);
    Blynk.virtualWrite(V0, 1);
    Blynk.virtualWrite(V1, "Motion Detected");
    Blynk.logEvent("Alert", "Motion Detected");
    lcd.clear();
    lcd.print("Motion Detected");
    if (Firebase.setBool(fbdo, "/motion", true)) {
      Serial.println("Motion data sent to Firebase");
    } else {
      Serial.println(fbdo.errorReason());
    }
  } else if (pinStatePrevious == HIGH && pinStateCurrent == LOW) {
    Serial.println("Motion stopped, turning relay OFF");
    digitalWrite(relay1, LOW);
    Blynk.virtualWrite(V0, 0);
    Blynk.virtualWrite(V1, "Motion Stopped");
    lcd.clear();
    lcd.print("Motion Stopped");
    if (Firebase.setBool(fbdo, "/motion", false)) {
      Serial.println("Motion data sent to Firebase");
    } else {
      Serial.println(fbdo.errorReason());
    }
  }

  char key = keypad.getKey();
  if (key) {
    Serial.print("Key pressed: ");
    Serial.println(key);
    handleKeypadInput(key);
  }
}

BLYNK_WRITE(V2) {
  int state = param.asInt();
  if (state) unlockDoor();
  else lockDoor();
}

BLYNK_WRITE(V3) {
  int choice = param.asInt();
  if (choice) {
    unlockDoor();
    // if (Firebase.setBool(fbdo, "/choice", true)) {
    //   Serial.println("Choice data sent to Firebase");
    // } else {
    //   Serial.println(fbdo.errorReason());
    // }
  } else {
    lockDoor();
    // if (Firebase.setBool(fbdo, "/choice", false)) {
    //   Serial.println("Choice data sent to Firebase");
    // } else {
    //   Serial.println(fbdo.errorReason());
    // }
  }
}

void updateLockStatus() {
  if (locked) {
    lcd.print("Welcome Home ");
    delay(2000);
    lcd.clear();
    lcd.print("Door Locked");
    Serial.println("Door Locked");
  } else {
    lcd.clear();
    lcd.print("Door Unlocked");
    Serial.println("Door Unlocked");
  }
}

void handleKeypadInput(char key) {
  if (locked) {
    if (key == '#' && codeIndex > 0) {
      enteredCode[codeIndex] = '\0';
      codeIndex = 0;
      Serial.print("Entered code: ");
      Serial.println(enteredCode);
      if (strcmp(enteredCode, "125D") == 0) {
        unlockDoor();
      } else {
        lcd.clear();
        lcd.print("Incorrect Pin!");
        delay(2000);
        lcd.clear();
        lcd.print("Door Locked");
      }
      memset(enteredCode, 0, sizeof(enteredCode));
    } else if (key == 'C' && codeIndex > 0) {
      lcd.setCursor(codeIndex - 1, 1);
      lcd.print(' ');
      codeIndex--;
      enteredCode[codeIndex] = '\0';
    } else if (key != '#' && key != 'C' && codeIndex < sizeof(enteredCode) - 1) {
      enteredCode[codeIndex] = key;
      lcd.setCursor(codeIndex, 1);
      lcd.print('*');
      codeIndex++;
    }
  } else {
    if (key == '*') {
      lockDoor();
    }
  }
}

void unlockDoor() {
  locked = false;
  //myServo.write(0);
  digitalWrite(gled, HIGH); // Assuming LOW unlocks the door
  Serial.println("Unlocking door to 0 degrees");
  lcd.clear();
  lcd.print("Door Unlocked");
  if (Firebase.setBool(fbdo, "/choice", true)) {
      Serial.println("Choice data sent to Firebase");
    } else {
      Serial.println(fbdo.errorReason());
    }
}

void lockDoor() {
  locked = true;
   digitalWrite(gled, LOW);
 // myServo.write(90);
  Serial.println("Locking door to 90 degrees");
  lcd.clear();
     if (Firebase.setBool(fbdo, "/choice", false)) {
      Serial.println("Choice data sent to Firebase");
    } else {
      Serial.println(fbdo.errorReason());
    }
  lcd.print("Door Locked");
}

void checkFirebaseChoice() {
  if (Firebase.getBool(fbdo, "/choice", &locked)) {
    Serial.println("Choice data retrieved from Firebase");
    if (locked) {
    
      unlockDoor();
    } else {
      
      lockDoor();
    }
  } else {
    Serial.println(fbdo.errorReason());
  }
}

