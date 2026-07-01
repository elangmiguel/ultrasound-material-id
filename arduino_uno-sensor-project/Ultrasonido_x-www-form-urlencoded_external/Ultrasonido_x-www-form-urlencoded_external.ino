#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <LiquidCrystal.h>

// Pines LCD (ajustados según configuración física)
const int rs = D5;
const int en = D4;
const int d4 = D0;
const int d5 = D1;
const int d6 = D2;
const int d7 = D3;

LiquidCrystal lcd(rs, en, d4, d5, d6, d7);

// Pines sensor ultrasónico
const int trigger = D7;
const int echo = D6;

// Parámetros red WiFi
//const char* ssid = "OBLIGAMEPRRO1";
//const char* password = "Trump123_";
const char* ssid = "ELANG 5324";
const char* password = "a7Q57{16";

// URL del servidor
//String url = "http://200.100.10.50:3000/insert/lectura";
String url = "http://192.168.137.1:3000/sensor/insert/lectura";

// Constantes
const float sound_velocity = 0.0346; // cm/us

// Variables
long duration_travel_time;
float measuredDistance;

void setup() {
  Serial.begin(115200);

  // LCD
  lcd.begin(16, 2);
  lcd.print("Conectando WiFi");

  // WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Conectando...");
  }

  Serial.println("Conectado a WiFi");
  lcd.clear();
  lcd.print("WiFi OK");
  lcd.setCursor(0, 1);
  lcd.print("IP:");
  lcd.print(WiFi.localIP());

  // Sensor
  pinMode(trigger, OUTPUT);
  pinMode(echo, INPUT);
  digitalWrite(trigger, LOW);
  delay(1000);
}

void loop() {
  // Medición
  digitalWrite(trigger, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigger, LOW);
  duration_travel_time = pulseIn(echo, HIGH, 30000);
  measuredDistance = duration_travel_time * sound_velocity / 2;

  Serial.print("Distancia (cm): ");
  Serial.println(measuredDistance);

  lcd.clear();
  lcd.print("Distancia:");
  lcd.setCursor(0, 1);
  lcd.print(measuredDistance, 1);
  lcd.print(" cm");

  // Envío al servidor
  if (WiFi.status() == WL_CONNECTED) {
    WiFiClient client;
    HTTPClient http;

    http.begin(client, url);
    http.addHeader("Content-Type", "application/json");

    // JSON payload
    String payload = "{\"sensor_id\":1,\"valor\":" + String(measuredDistance) + "}";

    int httpCode = http.POST(payload);

    if (httpCode > 0) {
      Serial.printf("POST code: %d\n", httpCode);
      String response = http.getString();
      Serial.println("Respuesta servidor:");
      Serial.println(response);
    } else {
      Serial.printf("Error POST: %s\n", http.errorToString(httpCode).c_str());
    }

    http.end();
  }

  delay(2000); // Cada 2 segundos
}
