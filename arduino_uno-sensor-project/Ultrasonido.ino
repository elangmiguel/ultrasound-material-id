#include <ESP8266WiFi.h> 
#include <ESP8266WebServer.h>

ESP8266WebServer server(80);

void handleRoot() {
    String html = R"rawliteral(
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>WebServer</title>
        </head>
        <body>
            <h1>Distance: <span id="distance">--</span> cm</h1>
            <script>
                setInterval(() => {
                    fetch('/distance').then(response => response.text()).then(data => {
                        document.getElementById('distance').innerText = data;
                    });
                }, 1000);
            </script>
        </body>
        </html>
    )rawliteral";
    
    server.send(200, "text/html", html);
}

const char* ssid = "ELANG 5324";
const char* password = "a7Q57{16";

const float sound_velocity = 0.0346; // cm/us
long duration_travel_time; 
float measuredDistance;

void handleDistance() { 
    server.send(200, "text/plain", String(measuredDistance));
}

const int trigger = D7; 
const int echo = D6;

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

  server.on("/", handleRoot); // Ruta para la página principal
  server.on("/distance", handleDistance); // Ruta para la distancia
  server.begin();

  pinMode(echo, INPUT);
  pinMode(trigger, OUTPUT);
  digitalWrite(trigger, LOW);
}

void loop() {
  server.handleClient();
  
  digitalWrite(trigger, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigger, LOW);
  
  duration_travel_time = pulseIn(echo, HIGH, 30000); 
  measuredDistance = duration_travel_time * sound_velocity / 2;
  
  // Print the distance to the serial monitor
  Serial.print("Distance (cm): ");
  Serial.println(measuredDistance);

  delay(100);
}
