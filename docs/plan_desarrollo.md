# Plan de Desarrollo: Gemelo Digital SIL + Visión Artificial (Calzado)

Prototipo 100 % software, sin hardware físico, siguiendo las fases de CRISP-DM. Fecha de elaboración: 22 de octubre de 2026 (Mes 2 del cronograma; quedan ~5 semanas).

## 1. Alcance recomendado

- **Línea simulada:** corte, costura, montaje, pegado de suela y control de calidad final. Para el prototipo, simular **solo la estación de inspección visual**. Las demás etapas se modelan como flujo y tiempos.
- **Defectos a detectar (3 o 4):** costura irregular o rota, mancha o suciedad, pegado defectuoso (burbujas o desalineación de suela) y deformación o corte incompleto.
- **SIL en este proyecto:** el "controlador" (lógica de inspección y decisión aprobar/rechazar) corre como software y se conecta a una planta virtual. La planta virtual es la banda, las cámaras y los zapatos sintéticos. No hace falta PLC ni cámara reales.

## 2. Arquitectura propuesta

```
[Planta virtual]            [Capa de comunicación]        [Controlador SIL]          [Gemelo / UI]
 Simulador de banda  --->   MQTT / OPC UA simulado  --->  Lógica de control    --->  Dashboard
 Cámara virtual (imagen)    (Mosquitto / asyncua)         + Módulo de visión          (estado, KPIs,
 Generador de defectos                                    (modelo CNN/YOLO)           defectos, histórico)
                                                          Decisión: OK / Rechazo
                                   └──────── Base de datos (SQLite/PostgreSQL + FS de imágenes)
```

Capas:
1. **Física simulada:** banda, piezas, temporización y cámara virtual.
2. **Visión artificial:** preprocesamiento, inferencia y clasificación de defectos.
3. **Control SIL:** máquina de estados (espera, captura, inferencia, decisión, actuador de rechazo).
4. **Gemelo digital:** réplica del estado en tiempo real, con métricas y registro histórico.
5. **Agentes de IA generativa:** generan y configuran el modelo, y su salida se audita (objetivos 4 y 5).

## 3. Stack tecnológico

| Capa | Tecnología sugerida | Alternativa |
|---|---|---|
| Lenguaje base | Python 3.11 | — |
| Simulación de planta | **SimPy** (eventos discretos) + generador 2D propio | Unity/Blender, o Gazebo (más pesado) |
| Imágenes sintéticas | Blender (Python API) o Stable Diffusion/inpainting + augmentations con **Albumentations** | Datasets públicos de defectos textiles/cuero (MVTec AD, Kaggle) |
| Visión artificial | **OpenCV** + **PyTorch** + **Ultralytics YOLOv8/11** (detección) o **Anomalib** (anomalías, útil con pocos defectos) | TensorFlow/Keras |
| Etiquetado | Roboflow, CVAT o Label Studio | — |
| Comunicación SIL | **MQTT (Mosquitto)** u **OPC UA (asyncua)**, que emulan el protocolo industrial real | Redis pub/sub |
| Control | Máquina de estados en Python (`transitions`) y opcionalmente IEC 61131-3 con OpenPLC como PLC virtual | — |
| Backend | **FastAPI** + WebSockets | Flask |
| Dashboard | **Streamlit** o React + Grafana | Dash |
| Datos | SQLite o PostgreSQL, imágenes en disco | — |
| Agentes IA generativa | Claude / API de LLM para generar código, configuración y escenarios, con trazabilidad de prompts | LangChain |
| Contenedores | Docker Compose | — |
| Seguimiento de experimentos | MLflow o Weights & Biases | — |

## 4. Fases (CRISP-DM) y cronograma restante

### Semana 1 (22–31 oct): Comprensión del negocio y de los datos + requerimientos
- Definir KPIs: precisión, recall por defecto, falsos rechazos, latencia por pieza (< 200 ms), throughput.
- Levantar requerimientos de la planta (actividad "Análisis de requerimientos").
- Documentar el catálogo de defectos y las condiciones de captura (iluminación, ángulo, resolución).
- Buscar y evaluar datasets públicos. Decidir cuánto va a ser sintético y cuánto real.

### Semana 2 (1–7 nov): Arquitectura y preparación de datos
- Diagramas de arquitectura (C4 o UML) y contratos de mensajes (tópicos MQTT, esquemas JSON).
- Construir el dataset: imágenes sintéticas y reales, etiquetado, split train/val/test y augmentations.
- Montar el repositorio, Docker Compose y la estructura de carpetas (`simulator/`, `vision/`, `controller/`, `twin/`, `dashboard/`, `agents/`).

### Semana 3 (8–17 nov): Modelado, visión y simulación
- Entrenar el modelo de visión (primero un baseline, luego YOLO o Anomalib) y evaluar con matriz de confusión, mAP y curvas PR.
- Implementar el simulador de planta (SimPy) con cámara virtual que emite imágenes.
- Implementar el controlador SIL y conectarlo por MQTT al simulador y al módulo de visión.
- Configurar los agentes de IA generativa: qué generan (escenarios, código de módulos, variaciones de defectos), con prompts versionados y registro de salidas.

### Semana 4 (18–24 nov): Integración, simulación y auditoría
- Integrar el gemelo digital con el dashboard (estado en tiempo real, conteo OK/NOK, historial).
- Ejecutar escenarios: operación normal, ráfaga de defectos, cámara degradada (ruido, baja luz), latencia o pérdida de mensajes.
- **Auditoría de la simulación generada por IA** (objetivo 5):
  - Revisión de código y reproducibilidad (mismas semillas, mismos resultados).
  - Verificación contra casos esperados (pruebas unitarias y de integración).
  - Detección de alucinaciones y sesgos, con una checklist y una bitácora de hallazgos.

### Semana 5 (25–30 nov): Evaluación y entregables
- Análisis de resultados, discusión y conclusiones.
- Artículo corto, póster y anexos.

## 5. Mapeo a los objetivos específicos

| Objetivo | Entregable |
|---|---|
| 1. Herramientas y metodologías de gemelos digitales | Marco teórico comparativo (ISO 23247, SIL/HIL/MIL, plataformas) |
| 2. Modelar el prototipo | Simulador + controlador SIL + módulo de visión funcionando |
| 3. Esquematizar la arquitectura | Diagramas C4/UML y contratos de mensajes |
| 4. Proponer con agentes de IA generativa | Registro de prompts, agentes configurados y código generado |
| 5. Auditoría | Informe de auditoría con checklist, métricas y hallazgos |

## 6. Riesgos y mitigaciones

- **Pocos datos de defectos reales:** usar datos sintéticos, augmentations y un enfoque de detección de anomalías (Anomalib), que se entrena solo con piezas buenas.
- **Alcance excesivo en 5 semanas:** limitar a 3 o 4 defectos y una sola estación de inspección. Dejar el resto como trabajo futuro.
- **Brecha entre simulación y realidad (domain gap):** declararla como limitación y validar con algunas imágenes reales.
- **Código generado por IA no confiable:** pruebas automáticas y revisión humana obligatoria. Esto alimenta directamente el objetivo 5.

## 7. Reparto sugerido (3 integrantes)

- **Persona A:** simulador de planta, controlador SIL y comunicación (MQTT/OPC UA).
- **Persona B:** datos y modelo de visión (dataset, entrenamiento, evaluación).
- **Persona C:** dashboard, agentes de IA, auditoría y documentación (artículo y póster).
