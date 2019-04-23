// This example uses an Adafruit Huzzah ESP8266
// to connect to shiftr.io.
//
// You can check on your device after a successful
// connection here: https://shiftr.io/try.
//
// by Joël Gähwiler
// https://github.com/256dpi/arduino-mqtt

#include <ESP8266WiFi.h>
#include <MQTT.h>
#include "wificonfig.h"

WiFiClient net;
MQTTClient client;

unsigned long lastMillis = 0;

void setup() {
  Serial.begin(115200);
  WiFi.begin(WIFI_SSID, WIFI_PSK);

  client.begin(MQTT_URL, MQTT_PORT, net);

	Serial.print("checking wifi...");
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(1000);
  }

  Serial.print("\nconnecting...");
  while (!client.connect(HOSTNAME, MQTT_USER, MQTT_PASSW)) {
    Serial.print(".");
    delay(1000);
  }

  Serial.println("\nconnected!");

	client.publish(TOPIC, WiFi.macAddress());

}

void loop() {
	static int count = 0;

	client.loop();
	delay(10);

	if (++count > 10) {
		Serial.println("\nDone...");
		ESP.deepSleep(0);
	}
}
