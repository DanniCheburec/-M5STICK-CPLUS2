#define POS_X 0
#define POS_Y 1
#define X_DEFAULT_MID 2088 // +-5
#define Y_DEFAULT_MID 2162 // +-5

#include "M5StickCPlus2.h"
#include "UNIT_MiniJoyC.h" 
#include "WiFi.h"
#include <Preferences.h>

Preferences storage;


UNIT_JOYC sensor;
LGFX_Sprite spr = LGFX_Sprite(&M5.Lcd);

const char* ssid = "SoloReg";
const char* password = "Stranachudes3";
bool waitingAck = false;
uint32_t globalRecordID = 0;


enum Screen {
  SCREEN_MENU,
  SCREEN_WIFI,
  SCREEN_DATA,
  SCREEN_SETTINGS,
  SCREEN_HAPPINESS,  // теперь это общий экран эмоций
  SCREEN_SADNESS
};

Screen currentScreen = SCREEN_HAPPINESS;
byte menuIndex = 0;


// === Эмоции ===
const uint8_t EMOTIONS_COUNT = 6;

const char* emotionsList[EMOTIONS_COUNT] = {
  "Happiness",
  "Sadness",
  "Anger",
  "Stress",
  "Energy",
  "Calm"
};

const uint16_t emotionTitleColors[EMOTIONS_COUNT] = {
  GREEN,     // Happiness
  BLUE,      // Sadness
  RED,       // Anger
  ORANGE,    // Stress
  YELLOW,    // Energy
  CYAN       // Calm
};

uint8_t emotionLevels[EMOTIONS_COUNT] = {
  5,  // Happiness
  5,  // Sadness
  5,  // Anger
  5,  // Stress
  5,  // Energy
  5   // Calm
};

uint8_t currentEmotionIdx = 0;  // текущая эмоция 0 = Mood, 1 = Sadness ...

const uint8_t MENU_ITEMS = 4;

// === Струткура записи данных ===
#define MAX_RECORDS 1000

struct EmotionRecord {
  uint32_t id;
  uint32_t timestamp;
  uint8_t levels[EMOTIONS_COUNT];
};

EmotionRecord records[MAX_RECORDS];
uint16_t recordCount = 0;

//  Главное меню 
void drawMenu() {
  spr.fillSprite(BLACK);
  spr.setTextSize(2);

  const char* menuItems[MENU_ITEMS] = { "WiFi", "Info", "Settings", "Emotions" };

  for (uint8_t i = 0; i < MENU_ITEMS; i++) {
    spr.setTextColor(menuIndex == i ? GREEN : WHITE);
    spr.setCursor(10, 20 + i * 40);
    spr.print(menuIndex == i ? "> " : "  ");
    spr.println(menuItems[i]);
  }

  spr.pushSprite(0, 0);
}

//  Экран эмоции 
void drawEmotionScreen(uint8_t emotionIdx) {
  spr.fillSprite(BLACK);

  // Название эмоции
  spr.setTextSize(2);
  spr.setTextColor(emotionTitleColors[emotionIdx]);
  spr.setCursor(10, 20);
  spr.println(emotionsList[emotionIdx]);


  // Шкала
  int barX = 15;
  int barY = 80;
  int barWidth = 110;
  int barHeight = 50;

  spr.fillRoundRect(barX, barY, barWidth, barHeight, 8, DARKGREY);

  int filledWidth = map(emotionLevels[emotionIdx], 1, 10, 0, barWidth);
  uint16_t fillColor = (emotionLevels[emotionIdx] <= 3) ? RED :
                       (emotionLevels[emotionIdx] <= 7) ? YELLOW : GREEN;
  spr.fillRoundRect(barX, barY, filledWidth, barHeight, 8, fillColor);

  // Треугольник-указатель
  int markerX = barX + filledWidth - 4;
  spr.fillTriangle(markerX, barY - 10, markerX + 8, barY - 10, markerX + 4, barY - 2, WHITE);

  // Большая цифра
  spr.setTextSize(3);
  spr.setTextColor(WHITE);
  spr.setCursor(60, 150);
  spr.printf("%d", emotionLevels[emotionIdx]);

  spr.pushSprite(0, 0);
}

// Экран с координатами
void drawDataScreen() {
  spr.fillSprite(BLACK);
  spr.setTextSize(2);
  spr.setTextColor(GREEN);
  spr.setCursor(10, 20);
  spr.println("Joystick");

  spr.setTextSize(2);
  spr.setCursor(10, 60);
  spr.printf("X: %d", sensor.getADCValue(POS_X));
  spr.setCursor(10, 100);
  spr.printf("Y: %d", sensor.getADCValue(POS_Y));

  spr.pushSprite(0, 0);
}

// Экран эмоций
void drawSettingsScreen() {
  spr.fillSprite(BLACK);
  spr.setTextColor(YELLOW);
  spr.setTextSize(2);
  spr.setCursor(10, 20);
  spr.println("Settings");
  spr.pushSprite(0, 0);
}

// Экран подключения к вайфай
void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  spr.fillSprite(BLACK);
  spr.setTextColor(CYAN);
  spr.setTextSize(2);
  spr.setCursor(5, 10);
  spr.println("Connecting to WiFi...");
  spr.pushSprite(0, 0);

  int timeout = 0;
  while (WiFi.status() != WL_CONNECTED && timeout < 60) {
    delay(500);
    timeout++;
    spr.setCursor(5, 40 + timeout * 5);
    spr.println(".");
    spr.pushSprite(0, 0);
  }

  spr.fillSprite(BLACK);
  spr.setCursor(5, 10);
  if (WiFi.status() == WL_CONNECTED) {
    spr.println("Connected!");
    spr.setCursor(5, 40);
    spr.println("IP:");
    spr.println(WiFi.localIP());
  } else {
    spr.println("WiFi FAILED :(");
  }
  spr.pushSprite(0, 0);
}

void drawWifiScreen() {
  connectWiFi();
}

//  Отрисовка текущего экрана 
void renderScreen() {
  switch (currentScreen) {
    case SCREEN_MENU:      drawMenu(); break;
    case SCREEN_WIFI:      drawWifiScreen(); break;
    case SCREEN_SETTINGS:  drawSettingsScreen(); break;
    case SCREEN_DATA:      drawDataScreen(); break;
    case SCREEN_HAPPINESS:
    case SCREEN_SADNESS:
      drawEmotionScreen(currentEmotionIdx);
      break;
  }
}


// === Сохранение ===
void saveSnapshot() {
  if (recordCount >= MAX_RECORDS) return;

  EmotionRecord &rec = records[recordCount];
  globalRecordID = storage.getUInt("lastID", 0);


  rec.timestamp = getTimestamp();

  for (uint8_t i = 0; i < EMOTIONS_COUNT; i++)
    rec.levels[i] = emotionLevels[i];

  recordCount++;
  rec.id = globalRecordID++;

  storage.putUInt("count", recordCount);
  storage.putBytes("data", records, sizeof(EmotionRecord) * recordCount);
  storage.putUInt("lastID", globalRecordID);
}



void setup() {
  auto cfg = M5.config();
  StickCP2.begin(cfg);
  Serial.begin(9600);

  spr.createSprite(135, 240);
  spr.fillSprite(BLACK);
  spr.pushSprite(0, 0);

  // Инициализация джойстика
  while (!(sensor.begin(&Wire, JoyC_ADDR, 0, 26, 100000UL))) {
    delay(100);
    Serial.println("I2C Error!");
  }

  // Проверка RTC
  if (!StickCP2.Rtc.isEnabled()) {
    Serial.println("RTC not found.");
    for (;;) vTaskDelay(500);
  }

  // Стартуем с первой эмоции
  currentScreen = SCREEN_HAPPINESS;
  currentEmotionIdx = 0;
  renderScreen();

  storage.begin("emotiondb", false);

  recordCount = storage.getUInt("count", 0);

  if (recordCount > 0) {
    storage.getBytes("data", records, sizeof(EmotionRecord) * recordCount);
  }

}


// === Получение времени ===
uint32_t getTimestamp() {
  auto timeinfo = StickCP2.Rtc.getTime();
  auto dateinfo = StickCP2.Rtc.getDate();

  tm t;
  t.tm_year = dateinfo.year - 1900;
  t.tm_mon  = dateinfo.month - 1;
  t.tm_mday = dateinfo.date;
  t.tm_hour = timeinfo.hours;
  t.tm_min  = timeinfo.minutes;
  t.tm_sec  = timeinfo.seconds;

  return mktime(&t);
}

//=== Отправить одну запсись ===
void sendRecord(const EmotionRecord &rec) {
  Serial.print("{\"id\":");
  Serial.print(rec.id);
  Serial.print("{\"ts\":");
  Serial.print(rec.timestamp);

  for (uint8_t i = 0; i < EMOTIONS_COUNT; i++) {
    Serial.print(",\"");
    Serial.print(emotionsList[i]);
    Serial.print("\":");
    Serial.print(rec.levels[i]);
  }

  Serial.println("}");
}


//=== Отправить всё ===
void sendAllRecords() {
  for (uint16_t i = 0; i < recordCount; i++) {
    sendRecord(records[i]);
    delay(5);   // защита от переполнения порта
  }

  Serial.println("END");
}

void checkSerialCommands() {
  if (!Serial.available()) return;

  String cmd = Serial.readStringUntil('\n');
  cmd.trim();

  if (cmd == "SEND" && !waitingAck) {
    sendAllRecords();
    waitingAck = true;
  }

  if (cmd == "OK") {
    recordCount = 0;
    storage.putUInt("count", 0);
    waitingAck = false;
  }
}


void loop() {
  StickCP2.update();


  if (StickCP2.BtnB.wasPressed()) {
    currentScreen = SCREEN_MENU;
    menuIndex = 3;  
    renderScreen();
    delay(200);
  }

  //  Главное меню 
  if (currentScreen == SCREEN_MENU) {
    if (sensor.getADCValue(POS_Y) < (Y_DEFAULT_MID - 750)) {  // Вверх
      if (menuIndex < MENU_ITEMS - 1) menuIndex++;
      else menuIndex = 0;
      renderScreen();
      delay(200);
    }

    if (sensor.getADCValue(POS_Y) > (Y_DEFAULT_MID + 750)) {  // Вниз
      if (menuIndex > 0) menuIndex--;
      else menuIndex = MENU_ITEMS - 1;
      renderScreen();
      delay(200);
    }

    if (StickCP2.BtnA.wasPressed()) {
      switch (menuIndex) {
        case 0: currentScreen = SCREEN_WIFI; break;
        case 1: currentScreen = SCREEN_DATA; break;
        case 2: currentScreen = SCREEN_SETTINGS; break;
        case 3:
          currentScreen = SCREEN_HAPPINESS;
          currentEmotionIdx = 0;  // Mood
          break;
      }
      renderScreen();
      StickCP2.BtnA.wasPressed();  
      delay(200);
    }
  }

  //  Экраны эмоций 
  if (currentScreen == SCREEN_HAPPINESS || currentScreen == SCREEN_SADNESS) {

    // Переключение эмоций: вверх/вниз по Y
    if (sensor.getADCValue(POS_Y) < (Y_DEFAULT_MID - 750)) {  // Вверх
      if (currentEmotionIdx < EMOTIONS_COUNT - 1) currentEmotionIdx++;
      else currentEmotionIdx = 0;
      renderScreen();
      delay(300);
    }

    if (sensor.getADCValue(POS_Y) > (Y_DEFAULT_MID + 750)) {  // Вниз
      if (currentEmotionIdx > 0) currentEmotionIdx--;
      else currentEmotionIdx = EMOTIONS_COUNT - 1;
      renderScreen();
      delay(300);
    }

    // Изменение уровня: влево/вправо по X
    if (sensor.getADCValue(POS_X) > (X_DEFAULT_MID + 750)) {  // Вправо — +
      if (emotionLevels[currentEmotionIdx] < 10) emotionLevels[currentEmotionIdx]++;
      renderScreen();
      delay(200);
    }

    if (sensor.getADCValue(POS_X) < (X_DEFAULT_MID - 750)) {  // Влево — -
      if (emotionLevels[currentEmotionIdx] > 1) emotionLevels[currentEmotionIdx]--;
      renderScreen();
      delay(200);
    }

    // Сохранение по кнопке A
    if (StickCP2.BtnA.wasPressed()) {
      saveSnapshot();

      spr.fillRect(20, 170, 100, 40, GREEN);
      spr.setTextColor(BLACK);
      spr.setTextSize(2);
      spr.setCursor(35, 180);
      spr.println("Saved!");
      spr.pushSprite(0, 0);
      delay(800);
      renderScreen();
      StickCP2.BtnA.wasPressed();
    }
  }

  // Обновление экрана Info (джойстик)
  if (currentScreen == SCREEN_DATA) {
    static int lastX = 0, lastY = 0;
    int x = sensor.getADCValue(POS_X);
    int y = sensor.getADCValue(POS_Y);
    if (abs(x - lastX) > 50 || abs(y - lastY) > 50) {
      renderScreen();
      lastX = x;
      lastY = y;
    }
    spr.setCursor(35, 180);
    Serial.println(recordCount);
  }

  

  checkSerialCommands();
  delay(10);
}