# Proyecto 2 de Big Data — Taxis y apps de transporte en Nueva York (TLC, 2024–2025)

SI3007 / ST0263 Tópicos Especiales en Telemática, Universidad EAFIT, 2026-2.

**Integrantes:** Jean Carlo Ardila · Andres Felipe Prieto · David Cossio Salazar

Caso de estudio de Big Data sobre los registros de viajes de la NYC Taxi and Limousine Commission (TLC): taxis amarillos, taxis verdes y Uber/Lyft en 2024 y 2025. El pipeline corre en AWS Academy: fuentes en RDS MariaDB, archivos en EC2 y URL de la TLC; datalake en S3; preparación con Glue y Spark; catálogo con Glue y EMR/Hive; analítica con Athena, Hive, SparkSQL y PySpark; y una app en Streamlit detrás de API Gateway.

## Estructura

Un directorio por punto de la rúbrica. Cada uno tiene su README con qué hace, cómo reproducirlo y las evidencias.

| Punto | Directorio | Contenido |
|---|---|---|
| 1 | [`punto1-caso-de-estudio/`](punto1-caso-de-estudio/) | Caso de estudio, datos y las 6 preguntas de negocio |
| 2 | [`punto2-fuentes/`](punto2-fuentes/) | Fuentes simuladas: RDS MariaDB, archivos en EC2 y URL |
| 3 | [`punto3-ingesta/`](punto3-ingesta/) | Ingesta automática al datalake en S3 |
| 4 | [`punto4-preparacion/`](punto4-preparacion/) | Preparación raw → trusted con Glue y Spark |
| 5 | [`punto5-catalogo/`](punto5-catalogo/) | Catálogo con Glue Data Catalog y EMR/Hive |
| 6 | [`punto6-analitica-sql/`](punto6-analitica-sql/) | Analítica con Athena, Hive y SparkSQL |
| 7 | [`punto7-analitica-pyspark/`](punto7-analitica-pyspark/) | Analítica con PySpark |
| 8 | [`punto8-visualizacion-app/`](punto8-visualizacion-app/) | Visualización y app en Streamlit detrás de API Gateway |

Código compartido: [`comun/config.py`](comun/config.py) (configuración y nombres de los recursos de AWS).

## Requisitos

- Una sesión activa de AWS Academy Learner Lab (región `us-east-1`).
- Python 3.10 o superior y la AWS CLI v2.

## Cómo reproducir

1. **Credenciales.** En el Learner Lab: *Start Lab* → *AWS Details* → *AWS CLI: Show*. Copia el bloque en `~/.aws/credentials` cambiando `[default]` por `[academy]`. Las credenciales cambian en cada sesión del laboratorio.
2. **Entorno de Python:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Configuración local:** `cp config.example.env config.env`. `config.env` está en `.gitignore` porque guarda la contraseña de la base de datos.
4. **Seguir los puntos en orden**, empezando por [`punto2-fuentes/`](punto2-fuentes/).

Para no gastar presupuesto del laboratorio al terminar: `python punto2-fuentes/infra/destruir_infra.py --confirmar`.
