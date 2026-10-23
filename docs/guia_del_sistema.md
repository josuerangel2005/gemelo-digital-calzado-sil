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
                              │
                              └── MQTT por WebSocket (puerto 9001) --> web/ (interfaz del gemelo, modo "MQTT en vivo")
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
| `web/` | Interfaz web del gemelo (React + Vite + Tailwind): banda en 2D, KPIs, última captura, controles y registro. Tiene dos modos: simulación local en el navegador o "MQTT en vivo", que muestra lo que publican `simulator/` y `controller/`. |
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
cd web && pnpm dev                # terminal 4 (opcional): interfaz web, botón "MQTT en vivo"

pytest                            # pruebas
```

Variables de entorno: `MQTT_HOST`, `INTERVALO_S` (def. 1.0), `P_DEFECTO` (def. 0.2), `N_PIEZAS` (def. 50), `TWIN_DB`.
Ejemplo rápido: `INTERVALO_S=0.2 N_PIEZAS=100 python -m simulator.main`.

## 6. Interfaz web (simulador 2D)

Requisitos: Node.js 22 y pnpm.

```bash
cd web
pnpm install
pnpm dev          # abre la interfaz en http://localhost:5173
pnpm test         # pruebas de la lógica de simulación (vitest)
pnpm build        # chequeo de tipos + build de producción en web/dist
```

Muestra la banda en vista superior, la cámara, el actuador de rechazo y las cajas OK/RECHAZO, con los estados del controlador (espera → captura → inferencia → decisión) iluminándose en orden. Diseño generado con Figma Make y adaptado al proyecto.

- **Controles:** pausar, reiniciar, velocidad, probabilidad de defecto, **sensibilidad del detector** (si baja del 100 %, algunos defectos pasan sin detectarse) e inyección de un defecto concreto (mancha, costura o pegado).
- **Escenarios:** operación normal, ráfaga de defectos, cámara degradada (baja la sensibilidad y sube la latencia) y pérdida de mensajes (el 15 % de las decisiones no llega al gemelo).
- **Planta vs. gemelo:** las cajas OK/RECHAZO cuentan lo que pasó físicamente; los KPIs cuentan solo los mensajes de decisión que recibió el gemelo. En el escenario de pérdida de mensajes ambos números divergen a propósito.
- **Defectos no detectados:** el controlador los aprueba, así que cuentan como OK y caen en la caja OK. El KPI "Defectos no detectados" usa la verdad de la simulación para medirlos.
- **Mensaje de decisión:** el JSON de "Última captura" sigue `contracts/decision.schema.json` (`decision` es siempre `OK` o `RECHAZO`).

**Modo "MQTT en vivo"** (selector arriba a la derecha): la interfaz se conecta al broker por WebSocket (`ws://localhost:9001`, configurable con la variable `VITE_MQTT_URL`) y se suscribe a `planta/camara/captura` y `planta/control/decision`.

- Cada captura coloca la pieza en la cámara y muestra la **imagen real** que generó `simulator/`; cada decisión la clasifica y actualiza KPIs, cajas y registro.
- Los mensajes que no cumplen `contracts/` se descartan y se cuentan como "inválidos".
- Una captura sin decisión durante 5 s se descarta y se cuenta como "sin decisión" (controlador caído o mensaje perdido).
- Los controles de la simulación se desactivan: la línea la mueve `simulator/` con sus variables de entorno.
- "Defectos no detectados" muestra "—": sin la verdad de la simulación no se puede medir en vivo.

Para probarlo: `docker compose up -d mosquitto`, luego `python -m controller.main`, abrir la interfaz con `pnpm dev`, elegir "MQTT en vivo" y ejecutar `python -m simulator.main`.

Código: la lógica está en `web/src/sim/` (sin React, con pruebas), la conexión MQTT y la validación de mensajes en `web/src/live/`, y la interfaz en `web/src/components/`. Los tiempos de la simulación local son ilustrativos.

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
