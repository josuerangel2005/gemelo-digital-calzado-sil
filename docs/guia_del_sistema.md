# Guía del sistema: cómo funciona todo

Esta guía es para que cualquiera del equipo entienda el prototipo sin leer todo el código.

## 1. La idea en una frase

Una banda transportadora virtual trae zapatos. Una cámara virtual les toma una foto, un módulo de visión decide si tienen defecto, y un controlador ordena aprobar o rechazar la pieza. Todo corre como software (SIL, Software-in-the-Loop), sin PLC ni cámara reales. El **gemelo digital** es la copia viva de ese estado: contadores, decisiones e historial.

## 2. Arquitectura

```
 simulator/            MQTT                controller/ + vision/          twin/            dashboard/
 Banda (SimPy)   --planta/camara/captura-->  Máquina de estados    --->  SQLite (twin.db) --> Streamlit
 Cámara virtual                              + Detector (stub)
                  <--planta/control/decision-- publica OK / RECHAZO
```

Los componentes **no se llaman entre sí**: se comunican por mensajes MQTT (broker Mosquitto). Así se puede cambiar uno sin tocar los otros.

## 3. Qué hay en cada carpeta

| Ruta | Qué hace |
|---|---|
| `simulator/main.py` | Planta virtual con SimPy. Cada `INTERVALO_S` segundos genera una imagen 128×128 (ruido gris; con probabilidad `P_DEFECTO` lleva un cuadrado oscuro) y la publica. La función `generar_imagen()` es el punto donde luego se conectan imágenes de Blender o de un dataset real. |
| `vision/detector.py` | Clase `Detector` con `predict(image) -> {label, score}`. Hoy es una heurística (cuenta píxeles oscuros). **Es el stub a reemplazar por YOLO/Anomalib** manteniendo la misma interfaz. También tiene helpers para codificar/decodificar PNG en base64. |
| `controller/inspection.py` | `InspectionController`: máquina de estados `espera → captura → inferencia → decisión → espera`. `process(captura)` devuelve el mensaje de decisión. No depende de MQTT, por eso es fácil de probar. |
| `controller/main.py` | Conecta el controlador a MQTT: escucha capturas, procesa, guarda en el gemelo y publica la decisión. |
| `twin/store.py` | `TwinStore`: guarda cada decisión en SQLite (`twin.db`). Es la memoria del gemelo. |
| `dashboard/app.py` | Pantalla Streamlit: conteo OK/RECHAZO, latencia media e historial leyendo `twin.db`. |
| `contracts/` | Formato de los mensajes (`topics.md` y esquemas JSON). Es el acuerdo entre componentes. |
| `simulador2d/` | Animación HTML/CSS/JS **independiente** para entender el proceso visualmente. No usa Python ni MQTT. |
| `agents/` | Registro de prompts y salidas de IA generativa (objetivos 4 y 5 del proyecto). |
| `tests/` | Pruebas con pytest: decisiones correctas, estados y cumplimiento de contratos. |
| `docker-compose.yml`, `mosquitto/` | Broker MQTT local. |
| `docs/` | Contexto, plan de desarrollo y esta guía. |

## 4. Recorrido de una pieza

1. `simulator` crea la pieza `n` y publica en `planta/camara/captura`:
   `{"pieza_id": n, "timestamp": ..., "imagen_png_b64": "..."}`
2. `controller` recibe el mensaje y pasa por los estados:
   - **espera**: no hay pieza en proceso.
   - **captura**: recibe y decodifica la imagen.
   - **inferencia**: llama a `Detector.predict()`.
   - **decisión**: `label == "ok"` → `OK`; cualquier otro → `RECHAZO`. Mide la latencia.
3. Guarda la decisión en `twin.db` y publica en `planta/control/decision`:
   `{"pieza_id", "timestamp", "decision", "label", "score", "latencia_ms"}`
4. `dashboard` lee `twin.db` y refresca los números.

## 5. Cómo ejecutarlo

Requisitos: Python 3.12 o 3.13 (con 3.14 Streamlit/Pillow puede no compilar) y Docker (o Mosquitto instalado).

```bash
cd app
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

docker compose up -d mosquitto
# Sin Docker (macOS): brew install mosquitto && mosquitto -c mosquitto/mosquitto.conf

python -m controller.main         # terminal 1 (arrancar primero)
python -m simulator.main          # terminal 2
streamlit run dashboard/app.py    # terminal 3

pytest                            # pruebas
```

Variables de entorno: `MQTT_HOST`, `INTERVALO_S` (def. 1.0), `P_DEFECTO` (def. 0.2), `N_PIEZAS` (def. 50), `TWIN_DB`.
Ejemplo rápido: `INTERVALO_S=0.2 N_PIEZAS=100 python -m simulator.main`.

## 6. Simulador 2D

Abrir `simulador2d/index.html` con doble clic. Muestra la banda en vista superior, la cámara, el actuador de rechazo y las cajas OK/RECHAZO, con los estados del controlador iluminándose en orden. Controles: pausar, reiniciar, velocidad, probabilidad de defecto, inyectar defecto y **sensibilidad del detector** (si baja del 100 %, algunos defectos pasan sin detectarse). Los tiempos son ilustrativos.

## 7. Cómo extenderlo

- **Detector real:** crear una clase con `predict(image) -> {"label": str, "score": float}` donde `label == "ok"` signifique pieza buena, y pasarla a `InspectionController(detector=...)`. No hay que cambiar nada más.
- **Imágenes mejores:** sustituir `generar_imagen()` en `simulator/main.py` por imágenes de un dataset o de Blender.
- **Nuevo mensaje o campo:** actualizar primero `contracts/*.schema.json`; las pruebas validan el cumplimiento.
- **IA generativa:** guardar en `agents/` un archivo `AAAA-MM-DD_tema.md` por interacción (prompt, modelo, salida, resultado de la auditoría).

## 8. Limitaciones actuales

- El detector es una heurística, no un modelo entrenado.
- Las imágenes son sintéticas y simples (brecha entre simulación y realidad).
- Solo hay una estación de inspección; el resto de la línea no se modela.
- El flujo completo con MQTT y el dashboard aún no se ha validado de punta a punta en todas las máquinas; las pruebas automáticas cubren controlador, detector y contratos.

## 9. Próximos pasos

Ver el cronograma en [plan_desarrollo.md](plan_desarrollo.md): dataset de defectos, entrenamiento del modelo de visión, integración con el gemelo, escenarios de simulación y auditoría de lo generado por IA.
