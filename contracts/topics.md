# Contratos de mensajes MQTT

| Tópico | Publica | Suscribe | Esquema |
|---|---|---|---|
| `planta/camara/captura` | simulator | controller | `captura.schema.json` |
| `planta/control/decision` | controller | twin / dashboard | `decision.schema.json` |

Todos los mensajes son JSON UTF-8. La imagen viaja como PNG codificado en base64.
