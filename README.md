# Identificación de Materiales por Ultrasonido

Sistema que estima el tipo de material frente a un sensor ultrasónico, comparando la reflectancia calculada contra valores de referencia almacenados en base de datos, con visualización en tiempo real.

## ¿Qué hace?

- Recibe lecturas periódicas de uno o varios sensores ultrasónicos conectados a dispositivos remotos.
- Calcula la reflectividad estimada a partir del valor leído y la distancia real configurada.
- Compara esa reflectividad contra una tabla de materiales de referencia para identificar el material más probable.
- Grafica las lecturas en tiempo real (últimos 20s / 1min / 5min) con Chart.js.
- Permite guardar calibraciones (reflectancia + distancia real + material identificado) y consultarlas paginadas.

## Arquitectura

```
[Sensor ultrasónico / dispositivo] → [API FastAPI] → [PostgreSQL]
                                            ↓
                                  [Frontend HTML/JS + Chart.js]
```

- **Backend:** FastAPI + psycopg2, con endpoints para dispositivos, sensores, lecturas, materiales y reflectancias.
- **Base de datos:** PostgreSQL, tablas para dispositivos, sensores, lecturas, materiales y reflectancias calculadas.
- **Frontend:** HTML/CSS/JS con Chart.js para graficar series de tiempo y una tabla paginada de calibraciones.

## Requisitos

- Python 3.10+
- PostgreSQL
- Un navegador moderno para el frontend

## Instalación

```bash
git clone https://github.com/TU_USUARIO/ultrasound-material-id.git
cd ultrasound-material-id
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install fastapi uvicorn psycopg2-binary python-dotenv pydantic
```

## Configuración

Este proyecto usa variables de entorno para las credenciales de la base de datos. Crea un archivo `.env` en la raíz (nunca lo subas al repositorio):

```
DB_HOST=localhost
DB_NAME=ultrasonido
DB_USER=ultrasonido
DB_PASSWORD=tu_password_aqui
```

Y en `main.py`, reemplaza los valores fijos por lectura desde entorno, igual que en la configuración de base de datos estándar con `python-dotenv`.

Además, revisa la lista `IPs_permitidas` y `allowed_origins` en `main.py`: están configuradas para una red local específica (equipos de laboratorio). Ajusta o elimina esas restricciones según tu entorno.

## Ejecutar el backend

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Ejecutar el frontend

```bash
cd html
python -m http.server 8080
```

Ajusta la constante `API_BASE` dentro del `<script>` de `index.html` para que apunte a la IP donde corre tu backend.

## Endpoints principales

| Método | Ruta                          | Descripción                                   |
|--------|-------------------------------|------------------------------------------------|
| GET    | `/dispositivos`               | Lista de dispositivos registrados               |
| GET    | `/sensores/{id}/lecturas`     | Lecturas históricas de un sensor                |
| GET    | `/materiales`                 | Lista de materiales de referencia               |
| POST   | `/reflectancia`               | Registra una nueva calibración de reflectancia  |
| GET    | `/reflectancias`              | Lista paginada de calibraciones guardadas       |

## Hardware utilizado

- Sensor ultrasónico
- Dispositivo/microcontrolador con conexión a red local
- Materiales de referencia con reflectancia conocida para calibración

> Nota: las IPs y orígenes CORS definidos en `main.py` corresponden a la red del laboratorio donde se desarrolló el proyecto. Para reproducirlo en otro entorno, ajusta esos valores.

## Estado del proyecto

Proyecto académico. Pendiente: mover credenciales a variables de entorno, eliminar definiciones y rutas duplicadas en `main.py`, limpiar bloques de código comentado.