#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>

const char* ssid = "ELANG 5324";
const char* password = "a7Q57{16";
String url = "http://192.168.137.1:3000/insert/lectura";

const int trigger = D7;
const int echo = D6;
const float sound_velocity = 0.0346; // cm/us

long duration_travel_time;
float measuredDistance;

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting...");
  }
  Serial.println("Connected to WiFi");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  pinMode(trigger, OUTPUT);
  pinMode(echo, INPUT);
  digitalWrite(trigger, LOW);
}

void loop() {
  // Medición de distancia
  digitalWrite(trigger, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigger, LOW);

  duration_travel_time = pulseIn(echo, HIGH, 30000);
  measuredDistance = duration_travel_time * sound_velocity / 2;

  Serial.print("Distance (cm): ");
  Serial.println(measuredDistance);

  // Envío de datos vía HTTP POST (form-url-encoded)
  if (WiFi.status() == WL_CONNECTED) {
    WiFiClient client;
    HTTPClient http;

    http.begin(client, url);
    http.addHeader("Content-Type", "application/x-www-form-urlencoded");

    String payload = "sensor_id=1&valor=" + String(measuredDistance);
    int httpCode = http.POST(payload);

    if (httpCode > 0) {
      Serial.printf("POST code: %d\n", httpCode);
      String response = http.getString();
      Serial.println("Server response:");
      Serial.println(response);
    } else {
      Serial.printf("POST failed: %s\n", http.errorToString(httpCode).c_str());
    }

    http.end();
  }

  delay(3000); // Esperar xxxxxx milisegundos antes de la siguiente medición
}
