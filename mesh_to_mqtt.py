Вызываем программу
nano /home/openhabian/mesh_to_mqtt.py

Вставляем туда этот код

import json
import re
import subprocess
import paho.mqtt.client as mqtt

def log_print(msg):
    print(msg, flush=True)

MQTT_BROKER = "192.168.0.116"
MQTT_PORT = 1883
MQTT_TOPIC_MSG = "meshcore/messages"
MQTT_TOPIC_STATUS = "meshcore/status"

# Исходная строгая регулярка
msg_pattern = re.compile(r"(Family|Public|Private|Group|Channel).*?:\s*([^:]+):\s*(.*)")

client = mqtt.Client()
client.will_set(MQTT_TOPIC_STATUS, "offline", qos=1, retain=True)
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()
client.publish(MQTT_TOPIC_STATUS, "online", qos=1, retain=True)
log_print("[MQTT] Подключено к брокеру.")

CMD = [
    "script", "-q", "-c", 
    "/home/openhabian/mesh_env/bin/python3 -m meshcore_cli -s /dev/ttyUSB0", 
    "/dev/null"
]

log_print("🚀 Запуск meshcore_cli через виртуальный TTY...")

try:
    process = subprocess.Popen(CMD, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=0)
    
    for line in iter(process.stdout.readline, ''):
        line = line.strip()
        if not line:
            continue

        if any(x in line for x in ["INFO:meshcore", "Fetching", "Interactive", "Warning", "Exiting", "Use ", "Some ", "WARNING", "ndrew", "", "will end interactive mode"]):
            continue
        
        match = msg_pattern.search(line)
        if match:
            ch = match.group(1).strip()
            sender = match.group(2).strip()
            text = match.group(3).strip()
            
            log_print(f" >>> [УСПЕХ] {ch} | {sender}: {text}")
            
            payload = {"type": "chat_message", "sender": sender, "channel": ch, "text": text}
            client.publish(MQTT_TOPIC_MSG, json.dumps(payload, ensure_ascii=False))
            
except KeyboardInterrupt:
    log_print("\nОстановка процесса...")
finally:
    if 'process' in locals():
        process.terminate()
    client.publish(MQTT_TOPIC_STATUS, "offline", qos=1, retain=True)
    client.loop_stop()
    client.disconnect()

# Глушим службу
sudo systemctl stop mesh-mqtt-bridge.service

# Вычищаем процессы script и старые сессии клиета
sudo pkill -9 -f script
sudo pkill -9 -f meshcore_cli

# Жестко освобождаем сам порт USB
sudo fuser -k /dev/ttyUSB0

Запуск

sudo systemctl start mesh-mqtt-bridge.service
sudo journalctl -u mesh-mqtt-bridge.service -f

Полный перезапуск одной командой

sudo systemctl stop mesh-mqtt-bridge.service && sudo pkill -9 -f script && sudo pkill -9 -f meshcore_cli && sudo fuser -k /dev/ttyUSB0 && sudo systemctl start mesh-mqtt-bridge.service

Просмотр лога

sudo journalctl -u mesh-mqtt-bridge.service -f

необходимо подключит хелтек через хаб с питанием. без этого плата вырубается
