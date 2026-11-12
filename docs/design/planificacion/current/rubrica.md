# Rúbrica — Proyecto 2 de Big Data (SI3007, 2026-2)

Fuente: `SI3007-262-proyecto2.docx`, en la raíz del repo; es también el documento de entrega que se va diligenciando. El documento dice "proyecto 3" en dos lugares; es un error del profesor y no cambia nada (Jean, 2026-11-10).

- **Peso:** 15% · **Entrega y sustentación presencial:** 2026-11-19
- **Profesor:** Edwin Montoya

## Requerimientos

Crear un caso de estudio que procese datos almacenados en **bases de datos, archivos y URLs**. Conseguir un dataset (típicamente público) y guardar una parte en bases de datos como fuente. Plantear **al menos 5 preguntas / hipótesis de negocio** que se contestan con esos datos; se refinan a medida que avanza el proyecto.

| # | Punto | Herramientas que pide la rúbrica |
|---|---|---|
| 1 | Caso de estudio y ≥5 preguntas de negocio | — |
| 2 | Fuentes de datos simuladas | RDS MariaDB, archivos en una instancia EC2, URLs en Internet |
| 3 | Ingesta **automática** al datalake, en las zonas correctas | AWS S3 |
| 4 | Preparación de datos: raw → trusted (o bronze → silver) | AWS Glue y Apache Spark |
| 5 | Catalogación de tablas SQL | AWS Glue y EMR/Hive |
| 6 | Analítica descriptiva con SQL | AWS Athena, EMR/Hive y SparkSQL |
| 7 | Analítica descriptiva con Spark en Python | PySpark |
| 8 | Visualización + aplicación expuesta por API Gateway | matplotlib, Dash, Power BI, Grafana, etc. + Streamlit detrás de API Gateway |

## Entregables

- **Documento:** el mismo Docx del enunciado, diligenciado con integrantes, link del repo y, por cada punto, descripciones, pantallazos, evidencias y extractos de código importante.
- **Compartirlo** con el profesor en una de dos nubes: OneDrive EAFIT (`emontoya@eafit.edu.co`) o Google Drive (`edwin.montoya@gmail.com`).
- **Correo inicial** por EAFIT Interactiva: integrantes, que el documento ya está compartido, la URL del documento y en qué nube.
- **Repo en GitHub** con un directorio explícito por cada uno de los 8 puntos: evidencias, código fuente y, lo más importante, todas las instrucciones y archivos para que el profesor u otra persona reproduzca el proyecto.
