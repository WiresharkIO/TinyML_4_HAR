#include <M5StickCPlus.h>
#include "BLEDevice.h"
#include "BLEServer.h"
#include "BLEUtils.h"
#include "BLE2902.h"
#include <ArduinoJson.h>

// BLE Setup..
BLEServer* pServer = NULL;
BLECharacteristic* pCharacteristic = NULL;
bool deviceConnected = false;

// UUIDs for BLE service and characteristic - 128 bit numbers (generated from https://www.uuidgenerator.net/version4)..
#define SERVICE_UUID        "4fe76cf0-8c00-4e81-b3e7-3e12c89106f2"
#define CHARACTERISTIC_UUID "99e68ef6-225d-4ca7-ae62-d90e3df5368e"

// Data acquisition parameters..
const int SAMPLE_RATE = 20;
const int DELAY_MS = 1000 / SAMPLE_RATE; // 50ms
unsigned long last_sample_time = 0;
bool recording = false;

// Activity management..
String activities[] = {"Walking", "Eating", "Standing", "Sitting", "Typing"};
int current_activity_index = 0;
int sample_count = 0;

// BLE Server callbacks..
class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
      deviceConnected = true;
      M5.Lcd.fillScreen(BLACK);
      M5.Lcd.setCursor(0, 0);
      M5.Lcd.setTextColor(GREEN);
      M5.Lcd.println("BLE Connected!");
      M5.Lcd.setTextColor(WHITE);
      M5.Lcd.println("Ready to stream data");
    };

    void onDisconnect(BLEServer* pServer) {
      deviceConnected = false;
      M5.Lcd.fillScreen(BLACK);
      M5.Lcd.setCursor(0, 0);
      M5.Lcd.setTextColor(RED);
      M5.Lcd.println("BLE Disconnected");
      M5.Lcd.setTextColor(WHITE);
      M5.Lcd.println("Waiting for connection...");
      pServer->startAdvertising(); // Restart advertising..
    }
};

void setup() {
  M5.begin();
  M5.IMU.Init();
  M5.Lcd.setRotation(3);
  
  // Initialize BLE..
  BLEDevice::init("M5StickC_Data_acquisition");
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  // Create BLE service..
  BLEService *pService = pServer->createService(SERVICE_UUID);

  // Create BLE characteristic..
  pCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_READ |
                      BLECharacteristic::PROPERTY_WRITE |
                      BLECharacteristic::PROPERTY_NOTIFY
                    );

  pCharacteristic->addDescriptor(new BLE2902());

  // Start the service..
  pService->start();

  // Start advertising..
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(false);
  pAdvertising->setMinPreferred(0x0);
  BLEDevice::startAdvertising();

  displayCurrentActivity();
}

void loop() {
  M5.update();
  
  // Button A (BTN): Start/Stop recording..
  if (M5.BtnA.wasPressed()) {
    M5.Lcd.fillRect(0, 100, 240, 20, BLACK);
    M5.Lcd.setCursor(0, 100);
    M5.Lcd.setTextColor(YELLOW);
    M5.Lcd.println("BTN pressed!");
    delay(100); // Show message briefly..
    
    if (!recording) {
      startRecording();
    } else {
      stopRecording();
    }
  }
  
  // Button B (PWR): Change activity (only when not recording)
  if (M5.BtnB.wasPressed() && !recording) {
    M5.Lcd.fillRect(0, 100, 240, 20, BLACK);
    M5.Lcd.setCursor(0, 100);
    M5.Lcd.setTextColor(CYAN);
    M5.Lcd.println("PWR pressed!");
    delay(500); // Show message briefly
    
    current_activity_index = (current_activity_index + 1) % 5;
    displayCurrentActivity();
  }
  
  // Stream data at 20Hz when recording and connected..
  if (recording && deviceConnected && (millis() - last_sample_time >= DELAY_MS)) {
    streamSensorData();
    last_sample_time = millis();
  }
  
  // delay(10);
}

void startRecording() {
  if (!deviceConnected) {
    M5.Lcd.fillScreen(BLACK);
    M5.Lcd.setCursor(0, 0);
    M5.Lcd.setTextColor(RED);
    M5.Lcd.println("No BLE Connection!");
    M5.Lcd.setTextColor(WHITE);
    M5.Lcd.println("Connect device first");
    delay(2000);
    displayCurrentActivity();
    return;
  }
  
  recording = true;
  sample_count = 0;
  
  M5.Lcd.fillScreen(BLACK);
  M5.Lcd.setCursor(0, 0);
  M5.Lcd.setTextColor(GREEN);
  M5.Lcd.println("STREAMING:");
  M5.Lcd.setTextColor(YELLOW);
  M5.Lcd.println(activities[current_activity_index]);
  M5.Lcd.setTextColor(CYAN);
  M5.Lcd.println("Rate: 20Hz");
  M5.Lcd.setTextColor(WHITE);
  M5.Lcd.println("Samples: 0");
}

void stopRecording() {
  recording = false;
  
  M5.Lcd.fillScreen(BLACK);
  M5.Lcd.setCursor(0, 0);
  M5.Lcd.setTextColor(RED);
  M5.Lcd.println("Streaming Stopped");
  M5.Lcd.setTextColor(WHITE);
  M5.Lcd.println("Samples sent: " + String(sample_count));
  
  delay(2000);
  displayCurrentActivity();
}

const float G_TO_MS2 = 9.81;
const float DEGREES_TO_RADS = 0.017453292519943295;

void streamSensorData() {
  float accX, accY, accZ;
  float gyroX, gyroY, gyroZ;
  
  // Read IMU data (M5StickC returns: accel in g, gyro in deg/s)
  M5.IMU.getAccelData(&accX, &accY, &accZ);
  M5.IMU.getGyroData(&gyroX, &gyroY, &gyroZ);
  
  // Convert units..
  float accX_ms2 = accX * G_TO_MS2;        // g to m/s²..
  float accY_ms2 = accY * G_TO_MS2;
  float accZ_ms2 = accZ * G_TO_MS2;
  
  float gyroX_rads = gyroX * DEGREES_TO_RADS;   // deg/s to rad/s..
  float gyroY_rads = gyroY * DEGREES_TO_RADS;
  float gyroZ_rads = gyroZ * DEGREES_TO_RADS;
  
  // Calculate gravity magnitude..
  float gravity_magnitude = sqrt(accX_ms2*accX_ms2 + accY_ms2*accY_ms2 + accZ_ms2*accZ_ms2);
  
  // Create JSON data..
  JsonDocument doc;
  doc["timestamp"] = millis();
  doc["activity"] = activities[current_activity_index];
  doc["acc_x"] = accX_ms2;      // m/s²..
  doc["acc_y"] = accY_ms2;
  doc["acc_z"] = accZ_ms2;
  doc["gyro_x"] = gyroX_rads;   // rad/s..
  doc["gyro_y"] = gyroY_rads;
  doc["gyro_z"] = gyroZ_rads;
  doc["sample_id"] = sample_count;
  
  doc["acc_x_raw"] = accX;      // Original g-force..
  doc["acc_y_raw"] = accY;
  doc["acc_z_raw"] = accZ;
  doc["gyro_x_raw"] = gyroX;    // Original deg/s..
  doc["gyro_y_raw"] = gyroY;
  doc["gyro_z_raw"] = gyroZ;
  doc["gravity_mag"] = gravity_magnitude;  // For verification..
  
  // Converting to string..
  String jsonString;
  serializeJson(doc, jsonString);
  
  // Sending via BLE..
  pCharacteristic->setValue(jsonString.c_str());
  pCharacteristic->notify();
  
  sample_count++;
  
  // Update display every 20 samples (1 second)..
  if (sample_count % 20 == 0) {
    M5.Lcd.fillRect(0, 60, 240, 20, BLACK);
    M5.Lcd.setCursor(0, 60);
    M5.Lcd.println("Samples: " + String(sample_count));
    
    // live data..
    M5.Lcd.fillRect(0, 80, 240, 60, BLACK);
    M5.Lcd.setCursor(0, 80);
    M5.Lcd.setTextSize(1);
    M5.Lcd.printf("Acc: %.2f,%.2f,%.2f m/s2\n", accX_ms2, accY_ms2, accZ_ms2);
    M5.Lcd.printf("Gyro: %.2f,%.2f,%.2f rad/s\n", gyroX_rads, gyroY_rads, gyroZ_rads);
    M5.Lcd.printf("Grav: %.2f m/s2", gravity_magnitude);
  }
}


void displayCurrentActivity() {
  M5.Lcd.fillScreen(BLACK);
  M5.Lcd.setCursor(0, 0);
  M5.Lcd.setTextColor(WHITE);
  M5.Lcd.setTextSize(2);
  M5.Lcd.println("BLE Streaming");
  
  M5.Lcd.setTextSize(1);
  M5.Lcd.setTextColor(deviceConnected ? GREEN : RED);
  M5.Lcd.println(deviceConnected ? "Connected" : "Waiting for connection...");
  
  M5.Lcd.setTextColor(YELLOW);
  M5.Lcd.println("");
  M5.Lcd.println("Activity:");
  M5.Lcd.setTextColor(CYAN);
  M5.Lcd.setTextSize(2);
  M5.Lcd.println(activities[current_activity_index]);
  
  M5.Lcd.setTextSize(1);
  M5.Lcd.setTextColor(WHITE);
  M5.Lcd.println("");
  M5.Lcd.println("BtnA: Start/Stop Stream");
  M5.Lcd.println("BtnB: Next Activity");
  
  // battery-level..
  M5.Lcd.setTextColor(GREEN);
  M5.Lcd.println("");
  M5.Lcd.println("Battery: " + String(M5.Axp.GetBatVoltage(), 2) + "V");
}