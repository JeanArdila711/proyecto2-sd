# Propuesta para el Punto 8: Streamlit y API Gateway

Andres Felipe Prieto, 2026-11-17. Decisión abierta del encargo (fase D): la propone el compañero y la decide Jean.

## La pregunta

¿Puede API Gateway ser el proxy directo de una app de Streamlit en una EC2, o hace falta otro diseño?

## Lo que dice la documentación

- **Streamlit necesita un WebSocket persistente** entre el navegador y el servidor: "It uses WebSockets to maintain a persistent, two-way communication channel between the client and server" y "Each browser tab or window creates its own WebSocket connection" (https://docs.streamlit.io/develop/concepts/architecture/architecture).
- **Las HTTP API y REST API de API Gateway no tienen soporte de WebSocket.** La tabla comparativa (https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-vs-rest.html) no lo lista para ninguna de las dos, y la integración HTTP proxy describe un paso de request/response: "API Gateway passes the entire request and response between the frontend and the backend" (https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-http.html). Ninguna página menciona el `Upgrade` de WebSocket.
- **Las WebSocket API de API Gateway no pasan el socket crudo al backend:** "The WebSocket API invokes your backend based on the content of the messages it receives from client apps", con rutas `$connect`, `$disconnect` y `$default` (https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api-overview.html). Streamlit habla su propio protocolo sobre un WebSocket y no encaja en ese modelo de rutas.

Conclusión: **un proxy directo de API Gateway a Streamlit no está soportado por lo documentado**. *Sin probar* en Academy; no se gastó tiempo en intentarlo.

## Propuesta

```
Navegador ──HTTP:8501──> Streamlit en una EC2 (t3.small)
                             │ requests.get(URL de API Gateway)
                             ▼
               API Gateway (HTTP API)  GET /resultados/{pregunta}
                             │ integración Lambda
                             ▼
               Lambda tlc-resultados (LabRole) ──> s3://<bucket>/resultados/punto6/athena/{pN}/resultado.csv
```

- **API Gateway expone los resultados** de P1–P6 como JSON, a través de una Lambda que lee los CSV que deja el Punto 6. Es la "aplicación expuesta mediante API Gateway".
- **Streamlit consume esa API** y dibuja las gráficas. Corre en una EC2 con Python 3.11 en un venv (`findings.md`, AL2023), con el puerto 8501 abierto solo a la IP de quien presenta.
- Las gráficas salen de resultados guardados, no de consultas en vivo (Athena cobra por dato escaneado), como pide el encargo.
- Gráficas estáticas en matplotlib (PNG en `punto8-visualizacion-app/evidencias/`) para el Docx.

Descartado:
- **API Gateway como proxy directo a Streamlit:** no soporta el WebSocket (arriba).
- **Un ALB delante de Streamlit:** soporta WebSocket, pero no es API Gateway, que es lo que pide la rúbrica.

## Qué necesita Jean decidir

1. ¿Aprueba el diseño API Gateway → Lambda → resultados, con Streamlit como cliente?
2. ¿Streamlit en la misma EC2 de las fuentes (`tlc-fuente-archivos`) o en una EC2 aparte? La propuesta es una aparte (`tlc-streamlit`, t3.small) para no mezclar la fuente de datos con la app, creada por un script idempotente en `punto8-visualizacion-app/`.
