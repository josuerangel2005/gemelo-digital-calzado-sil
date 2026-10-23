"""Planta virtual: banda con piezas (SimPy) y cámara virtual que publica por MQTT."""
import json
import os
import time

import numpy as np
import paho.mqtt.client as mqtt
import simpy

from vision.detector import encode_png_b64

HOST = os.getenv("MQTT_HOST", "localhost")
INTERVALO_S = float(os.getenv("INTERVALO_S", "1.0"))
P_DEFECTO = float(os.getenv("P_DEFECTO", "0.2"))
N_PIEZAS = int(os.getenv("N_PIEZAS", "50"))


def generar_imagen(rng: np.random.Generator, defectuosa: bool) -> np.ndarray:
    img = rng.normal(180, 8, (128, 128)).clip(0, 255).astype(np.uint8)
    if defectuosa:
        x, y = rng.integers(20, 90, 2)
        img[y : y + 24, x : x + 24] = rng.integers(10, 40)
    return img


def banda(env, client, rng):
    for pieza_id in range(N_PIEZAS):
        yield env.timeout(INTERVALO_S)
        img = generar_imagen(rng, rng.random() < P_DEFECTO)
        msg = {"pieza_id": pieza_id, "timestamp": time.time(), "imagen_png_b64": encode_png_b64(img)}
        client.publish("planta/camara/captura", json.dumps(msg))


if __name__ == "__main__":
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(HOST, 1883)
    client.loop_start()
    env = simpy.rt.RealtimeEnvironment(factor=1.0, strict=False)
    env.process(banda(env, client, np.random.default_rng(42)))
    env.run()
    client.loop_stop()
