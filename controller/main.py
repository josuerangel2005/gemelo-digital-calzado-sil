import json
import os

import paho.mqtt.client as mqtt

from controller.inspection import InspectionController
from twin.store import TwinStore

HOST = os.getenv("MQTT_HOST", "localhost")
ctrl = InspectionController()
store = TwinStore()


def on_message(client, userdata, msg):
    decision = ctrl.process(json.loads(msg.payload))
    store.save(decision)
    client.publish("planta/control/decision", json.dumps(decision))
    print(f"pieza {decision['pieza_id']}: {decision['decision']} ({decision['label']})")


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_message = on_message
client.connect(HOST, 1883)
client.subscribe("planta/camara/captura")
client.loop_forever()
