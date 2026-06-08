Шаг 1: Очистка и открытие редактора
killall -9 python3 2>/dev/null
fuser -k /dev/ttyUSB0 2>/dev/null
nano /root/mesh_to_mqtt/mesh_bridge_direct.py
далее вставить в файл эту программу


import asyncio, json, time
import paho.mqtt.client as mqtt
from meshcore import MeshCore, EventType

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

MQTT_BROKER = "192.168.0.116"
TOPIC_MSG = "meshcore/messages"
TOPIC_STATUS = "meshcore/status"
TOPIC_CMD = "meshcore/command/send"

cmd_queue = asyncio.Queue()
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.will_set(TOPIC_STATUS, "offline", qos=1, retain=True)
def on_mqtt_msg(client, userdata, msg):
    try:
        cmd_queue.put_nowait(json.loads(msg.payload.decode('utf-8')))
        log("MQTT cmd received")
    except Exception as e:
        log(f"MQTT err: {e}")

async def process_cmds(mesh):
    while True:
        cmd = await cmd_queue.get()
        try:
            if cmd.get("type") == "channel":
                await mesh.send_message(int(cmd["target"]), cmd["text"])
                log(f"Sent to ch {cmd['target']}")
            elif cmd.get("type") == "direct":
                await mesh.send_direct_message(str(cmd["target"]), cmd["text"])
                log(f"Sent to dm {cmd['target']}")
        except Exception as e:
            log(f"Send err: {e}")
        finally:
            cmd_queue.task_done()
          async def main():
    log("Starting...")
    client.on_message = on_mqtt_msg
    client.connect(MQTT_BROKER, 1883, 60)
    client.loop_start()
    client.publish(TOPIC_STATUS, "online", qos=1, retain=True)
    client.subscribe(TOPIC_CMD)
    log("MQTT OK")
    
    mesh = await MeshCore.create_serial("/dev/ttyUSB0", 115200)
    log("Heltec OK")
    
    async def on_ch(ev):
        d = ev.payload
        log(f"CH {d.get('channel_idx')}: {d.get('text')}")
        client.publish(TOPIC_MSG, json.dumps({"type":"channel", "ch":d.get('channel_idx'), "text":d.get('text')}, ensure_ascii=False))
        
    async def on_dm(ev):
        d = ev.payload
        log(f"DM {d.get('pubkey_prefix')}: {d.get('text')}")
        client.publish(TOPIC_MSG, json.dumps({"type":"direct", "sender":d.get('pubkey_prefix'), "text":d.get('text')}, ensure_ascii=False))

    mesh.subscribe(EventType.CHANNEL_MSG_RECV, on_ch)
    mesh.subscribe(EventType.CONTACT_MSG_RECV, on_dm)
      asyncio.create_task(process_cmds(mesh))
    await mesh.start_auto_message_fetching()
    log("Running.")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        log("Stop.")
    finally:
        await mesh.stop_auto_message_fetching()
        client.publish(TOPIC_STATUS, "offline", qos=1, retain=True)
        client.loop_stop()

if __name__ == '__main__':
    asyncio.run(main())

Проверка
# 1. Проверка синтаксиса (если ошибок нет, команда просто вернет пустую строку)
python3 -m py_compile /root/mesh_to_mqtt/mesh_bridge_direct.py

# 2. Если предыдущая команда молчит (это хорошо!), запускаем вручную:
/usr/bin/python3 /root/mesh_to_mqtt/mesh_bridge_direct.py

Запуск сервиса
/etc/init.d/mesh-mqtt-bridge restart
logread -e mesh_bridge -f
