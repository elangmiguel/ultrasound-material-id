from fastapi import FastAPI, Form, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Generator, Tuple, List
from datetime import datetime
from pydantic import BaseModel, Field,  condecimal, validator, PositiveFloat

import psycopg2
from psycopg2.extras import RealDictCursor
import psycopg2.extensions

# Parámetros de conexión a la base de datos
DB_HOST = "192.168.56.1"
DB_NAME = "ultrasonido"
DB_USER = "ultrasonido"
DB_PASWD = "123456"

# Definición del tipo para la conexión y cursor
DBConnection = Generator[Tuple[psycopg2.extensions.connection, RealDictCursor], None, None]

app = FastAPI()

from fastapi import FastAPI, Request, HTTPException
from starlette.responses import JSONResponse

app = FastAPI()

# Lista blanca de IPs permitidas
IPs_permitidas = {
    "127.0.0.1",    	# localhost
    
	#ObligamePrro1
    "200.100.10.100",	# IP local
    "200.100.10.101", 	# IP externa del dispositivo
    "200.100.10.102", 	# IP externa de 
    
	#Anfitrion-VM
	"192.168.56.1",		# IP de la VM
    "192.168.56.2", 	# IP local
	
	#ELANG 5324
	"192.168.137.1",	# IP local
    "192.168.137.2", 	# IP externa del dispositivo
}

@app.middleware("http")
async def limitar_por_ip(request: Request, call_next):
    ip_cliente = request.client.host
    if ip_cliente not in IPs_permitidas:
        return JSONResponse(status_code=403, content={"detail": "Acceso denegado desde esta IP"})
    return await call_next(request)

@app.get("/protegido")
def ruta_protegida():
    return {"mensaje": "Acceso concedido"}


# Middleware CORS
allowed_origins = [
    "http://localhost:8000",	 	# Origen local
    "http://192.168.56.1:8000",	 	# Origen VM Anfitrion-VM
    "http://192.168.56.2:8000",	 	# Origen local Anfitrion-VM
    "http://200.100.10.100:8000",	# Origen local de ObligamePrro1
    "http://200.100.10.102:8000",	# Origen externo de  
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

def get_db() -> DBConnection:
    conn = psycopg2.connect(database=DB_NAME, user=DB_USER, password=DB_PASWD, host=DB_HOST, port=5432)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        yield conn, cursor
    finally:
        cursor.close()
        conn.close()

def construir_insert(tabla: str, campos: dict):
    columnas = []
    valores = []
    placeholders = []

    for key, value in campos.items():
        if value is not None:
            columnas.append(key)
            valores.append(value)
            placeholders.append("%s")

    query = f"INSERT INTO {tabla} ({', '.join(columnas)}) VALUES ({', '.join(placeholders)})"
    return query, tuple(valores)

@app.get("/")
async def root():
    return {"message": "API funcionando correctamente"}

@app.get("/select/{table}", tags=["Base de datos"])
async def read_table(table: str, db: DBConnection = Depends(get_db)):
    tablas_permitidas = ["dispositivo", "sensor", "lectura", "tipo", "sensor_tipo", "configuracion"]
    if table not in tablas_permitidas:
        raise HTTPException(status_code=400, detail=f"Tabla '{table}' no permitida")

    conn, cursor = db
    cursor.execute(f"SELECT * FROM {table} ORDER BY id")
    rows = cursor.fetchall()
    return rows

@app.get("/lecturas", tags=["lectura", "web"])
async def get_lecturas(db: DBConnection = Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT fecha, valor FROM lectura ORDER BY fecha")
    rows = cursor.fetchall()
    return [{"fecha": str(row["fecha"]), "valor": row["valor"]} for row in rows]

@app.get("/sensor/select/lectura", tags=["web"])
async def get_lecturas_por_sensor(sensor_id: int, db: DBConnection = Depends(get_db)):
    conn, cursor = db
    try:
        cursor.execute("""
            SELECT id, sensor_id, valor, fecha 
            FROM lectura 
            WHERE sensor_id = %s 
            ORDER BY fecha DESC
            """.strip(), (sensor_id,))
        rows = cursor.fetchall()
        return [
            {"id": row["id"], "sensor_id": row["sensor_id"], "valor": row["valor"], "fecha": str(row["fecha"])}
            for row in rows
        ]
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al consultar lecturas: {str(e)}")

@app.get("/materiales", tags=["material", "web"])
async def get_materiales(db: DBConnection = Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT id, nombre, descripcion, reflectancia_referencia FROM material ORDER BY reflectancia_referencia")
    rows = cursor.fetchall()
    return [
        {
            "id": row["id"],
            "nombre": row["nombre"],
            "descripcion": row["descripcion"],
            "reflectancia_referencia": float(row["reflectancia_referencia"]) if row["reflectancia_referencia"] is not None else None
        }
        for row in rows
    ]

class ReflectanciaIn(BaseModel):
    dispositivo_id: int = Field(..., gt=0, description="ID válido del dispositivo")
    lectura_id: int = Field(..., gt=0, description="ID válido de la lectura")
    distancia_real: PositiveFloat = Field(..., description="Distancia real mayor que cero")
    valor: Optional[float] = Field(None, description="Valor de reflectancia del sensor")
    material_id: Optional[int] = Field(None, description="ID del material identificado")

@app.post("/reflectancia", tags=["web"])
async def crear_reflectancia(
    reflectancia: ReflectanciaIn,
    db: Tuple = Depends(get_db)
):
    if reflectancia.valor is not None and reflectancia.valor < 0:
        raise HTTPException(status_code=400, detail="El valor no puede ser negativo")

    conn, cursor = db
    try:
        query, valores = construir_insert("reflectancia", reflectancia.dict())
        cursor.execute(query, valores)
        conn.commit()

        return {"message": "Reflectancia insertada"}

    except Exception as e:
        conn.rollback()
        print(f"Error al insertar reflectancia: {e}")  # Log en consola backend
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()



# Modelo Pydantic para la reflectancia
class ReflectanciaOut(BaseModel):
    id: int
    fecha: datetime
    dispositivo_id: int
    lectura_id: int
    distancia_real: float
    valor: Optional[float] = None
    material_id: Optional[int] = None


@app.get("/reflectancias", response_model=List[ReflectanciaOut], tags=["web"])
async def listar_reflectancias(
    page: int = Query(1, ge=1, description="Número de página (mínimo 1)"),
    page_size: int = Query(10, ge=1, le=100, description="Cantidad de ítems por página (1-100)"),
    db: DBConnection = Depends(get_db)
):
    offset = (page - 1) * page_size
    conn, cursor = db

    query = """
        SELECT id, fecha, dispositivo_id, lectura_id, distancia_real, valor, material_id
        FROM public.reflectancia
        ORDER BY fecha DESC
        LIMIT %s OFFSET %s
    """
    cursor.execute(query, (page_size, offset))
    rows = cursor.fetchall()

    resultados = [ReflectanciaOut(**row) for row in rows]
    return resultados













class Dispositivo(BaseModel):
    id: int
    nombre: str

class Sensor(BaseModel):
    id: int
    referencia: str
    descripcion: str
    dispositivo_id: int

class Lectura(BaseModel):
    id: int
    sensor_id: int
    valor: float
    fecha: datetime


@app.get("/dispositivos", response_model=List[Dispositivo], tags=["web"])
async def get_dispositivos(db: DBConnection = Depends(get_db)):
    conn, cursor = db
    try:
        cursor.execute("SELECT id, nombre FROM dispositivo")
        return cursor.fetchall()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al consultar dispositivos: {str(e)}")


@app.get("/dispositivos/{dispositivo_id}/sensores", response_model=List[Sensor], tags=["web"])
async def get_sensores_por_dispositivo(dispositivo_id: int, db: DBConnection = Depends(get_db)):
    conn, cursor = db
    try:
        cursor.execute("""
            SELECT id, referencia, descripcion, dispositivo_id
            FROM sensor
            WHERE dispositivo_id = %s
        """, (dispositivo_id,))
        return cursor.fetchall()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al consultar sensores: {str(e)}")


@app.get("/sensores/{sensor_id}/lecturas", response_model=List[Lectura], tags=["web"])
async def get_lecturas_por_sensor(sensor_id: int, db: DBConnection = Depends(get_db)):
    conn, cursor = db
    try:
        cursor.execute("""
            SELECT id, sensor_id, valor, fecha
            FROM lectura
            WHERE sensor_id = %s
            ORDER BY fecha DESC
            LIMIT 500
        """, (sensor_id,))
        return cursor.fetchall()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al consultar lecturas: {str(e)}")












@app.post("/insert/dispositivo", tags=["dispositivo"])
async def insert_dispositivo(
    nombre: str,
    ip: Optional[str] = None,
    w: Optional[float] = None,
    n: Optional[float] = None,
    db: DBConnection = Depends(get_db)
):
    conn, cursor = db
    query, valores = construir_insert("dispositivo", {
        "nombre": nombre,
        "ip": ip,
        "w": w,
        "n": n
    })
    cursor.execute(query, valores)
    conn.commit()
    return {
        "message": "Dispositivo insertado correctamente",
        "datos_insertados": dict(zip(["nombre", "ip", "w", "n"], valores))
    }

@app.get("/select/dispositivo/", tags=["dispositivo"])
async def get_dispositivo(
    id: Optional[int] = None,
    nombre: Optional[str] = None,
    ip: Optional[str] = None,
    w: Optional[float] = None,
    n: Optional[float] = None,
    db: DBConnection = Depends(get_db)
):
    conn, cursor = db
    query = "SELECT * FROM dispositivo WHERE TRUE"
    params = []
    if id is not None:
        query += " AND id = %s"
        params.append(id)
    if nombre is not None:
        query += " AND nombre = %s"
        params.append(nombre)
    if ip is not None:
        query += " AND ip = %s"
        params.append(ip)
    if w is not None:
        query += " AND w = %s"
        params.append(w)
    if n is not None:
        query += " AND n = %s"
        params.append(n)
    query += " ORDER BY id"
    cursor.execute(query, params)
    return cursor.fetchall()

@app.put("/update/dispositivo", tags=["dispositivo"])
async def update_dispositivo(
    id: int,
    nombre: str,
    ip: Optional[str] = None,
    w: Optional[float] = None,
    n: Optional[float] = None,
    db: DBConnection = Depends(get_db)
):
    conn, cursor = db
    cursor.execute(
        "UPDATE dispositivo SET nombre = %s, ip = %s, w = %s, n = %s WHERE id = %s",
        (nombre, ip, w, n, id)
    )
    conn.commit()
    return {"message": "Dispositivo actualizado correctamente"}

@app.delete("/delete/dispositivo", tags=["dispositivo"])
async def delete_dispositivo(id: int, db: DBConnection = Depends(get_db)):
    conn, cursor = db
    cursor.execute("DELETE FROM dispositivo WHERE id = %s", (id,))
    conn.commit()
    return {"message": "Dispositivo eliminado correctamente"}




@app.post("/insert/sensor", tags=["sensor"])
async def insert_sensor(
    dispositivo_id: int,
    referencia: str,
    descripcion: Optional[str] = None,
    db: DBConnection = Depends(get_db)
):
    conn, cursor = db
    query, valores = construir_insert("sensor", {
        "dispositivo_id": dispositivo_id,
        "referencia": referencia,
        "descripcion": descripcion
    })
    cursor.execute(query, valores)
    conn.commit()
    return {
        "message": "Sensor insertado correctamente",
        "datos_insertados": dict(zip(["dispositivo_id", "referencia", "descripcion"], valores))
    }

@app.get("/select/sensor/", tags=["sensor"])
async def get_sensor(
    id: Optional[int] = None,
    dispositivo_id: Optional[int] = None,
    referencia: Optional[str] = None,
    descripcion: Optional[str] = None,
    include_dispositivo: bool = False,
    db: DBConnection = Depends(get_db)
):
    conn, cursor = db
    if include_dispositivo:
        query = """
            SELECT s.id, s.dispositivo_id, s.referencia, s.descripcion,
                   d.nombre, d.ip, d.w, d.n
            FROM sensor s
            JOIN dispositivo d ON s.dispositivo_id = d.id
            WHERE TRUE
        """
    else:
        query = "SELECT * FROM sensor WHERE TRUE"
    params = []
    if id is not None:
        query += " AND s.id = %s" if include_dispositivo else " AND id = %s"
        params.append(id)
    if dispositivo_id is not None:
        query += " AND s.dispositivo_id = %s" if include_dispositivo else " AND dispositivo_id = %s"
        params.append(dispositivo_id)
    if referencia is not None:
        query += " AND s.referencia = %s" if include_dispositivo else " AND referencia = %s"
        params.append(referencia)
    if descripcion is not None:
        query += " AND s.descripcion = %s" if include_dispositivo else " AND descripcion = %s"
        params.append(descripcion)
    query += " ORDER BY s.id" if include_dispositivo else " ORDER BY id"
    cursor.execute(query, params)
    return cursor.fetchall()

@app.put("/update/sensor", tags=["sensor"])
async def update_sensor(
    id: int,
    dispositivo_id: int,
    referencia: str,
    descripcion: Optional[str] = None,
    db: DBConnection = Depends(get_db)
):
    conn, cursor = db
    cursor.execute(
        "UPDATE sensor SET dispositivo_id = %s, referencia = %s, descripcion = %s WHERE id = %s",
        (dispositivo_id, referencia, descripcion, id)
    )
    conn.commit()
    return {"message": "Sensor actualizado correctamente"}

@app.delete("/delete/sensor", tags=["sensor"])
async def delete_sensor(id: int, db: DBConnection = Depends(get_db)):
    conn, cursor = db
    cursor.execute("DELETE FROM sensor WHERE id = %s", (id,))
    conn.commit()
    return {"message": "Sensor eliminado correctamente"}




@app.post("/insert/lectura", tags=["lectura"])
async def insert_lectura(
    fecha: datetime,
    valor: float,
    sensor_id: int,
    db: DBConnection = Depends(get_db)
):
    conn, cursor = db
    query, valores = construir_insert("lectura", {
        "fecha": fecha,
        "valor": valor,
        "sensor_id": sensor_id
    })
    cursor.execute(query, valores)
    conn.commit()
    return {
        "message": "Lectura insertada correctamente",
        "datos_insertados": dict(zip(["fecha", "valor", "sensor_id"], valores))
    }

@app.get("/select/lectura/", tags=["lectura"])
async def get_lectura(
    id: Optional[int] = None,
    fecha: Optional[datetime] = None,
    valor: Optional[float] = None,
    sensor_id: Optional[int] = None,
    include_sensor: bool = False,
    db: DBConnection = Depends(get_db)
):
    conn, cursor = db
    if include_sensor:
        query = """
            SELECT l.id, l.fecha, l.valor, l.sensor_id,
                   s.referencia, s.descripcion, s.dispositivo_id
            FROM lectura l
            JOIN sensor s ON l.sensor_id = s.id
            WHERE TRUE
        """
    else:
        query = "SELECT * FROM lectura WHERE TRUE"
    params = []
    if id is not None:
        query += " AND l.id = %s" if include_sensor else " AND id = %s"
        params.append(id)
    if fecha is not None:
        query += " AND l.fecha = %s" if include_sensor else " AND fecha = %s"
        params.append(fecha)
    if valor is not None:
        query += " AND l.valor = %s" if include_sensor else " AND valor = %s"
        params.append(valor)
    if sensor_id is not None:
        query += " AND l.sensor_id = %s" if include_sensor else " AND sensor_id = %s"
        params.append(sensor_id)
    query += " ORDER BY l.id" if include_sensor else " ORDER BY id"
    cursor.execute(query, params)
    return cursor.fetchall()

@app.put("/update/lectura", tags=["lectura"])
async def update_lectura(
    id: int,
    fecha: datetime,
    valor: float,
    sensor_id: int,
    db: DBConnection = Depends(get_db)
):
    conn, cursor = db
    cursor.execute(
        "UPDATE lectura SET fecha = %s, valor = %s, sensor_id = %s WHERE id = %s",
        (fecha, valor, sensor_id, id)
    )
    conn.commit()
    return {"message": "Lectura actualizada correctamente"}

@app.delete("/delete/lectura", tags=["lectura"])
async def delete_lectura(id: int, db: DBConnection = Depends(get_db)):
    conn, cursor = db
    cursor.execute("DELETE FROM lectura WHERE id = %s", (id,))
    conn.commit()
    return {"message": "Lectura eliminada correctamente"}




@app.post("/insert/material", tags=["material"])
async def insert_material(
    nombre: str,
    descripcion: Optional[str] = None,
    reflectancia_referencia: Optional[float] = None,
    db: DBConnection = Depends(get_db)
):
    conn, cursor = db
    query, valores = construir_insert("material", {
        "nombre": nombre,
        "descripcion": descripcion,
        "reflectancia_referencia": reflectancia_referencia
    })
    cursor.execute(query, valores)
    conn.commit()
    return {
        "message": "Material insertado correctamente",
        "datos_insertados": dict(zip(["nombre", "descripcion", "reflectancia_referencia"], valores))
    }

@app.get("/select/material/", tags=["material"])
async def get_material(
    id: Optional[int] = None,
    nombre: Optional[str] = None,
    descripcion: Optional[str] = None,
    reflectancia_referencia: Optional[float] = None,
    db: DBConnection = Depends(get_db)
):
    conn, cursor = db
    query = "SELECT * FROM material WHERE TRUE"
    params = []
    if id is not None:
        query += " AND id = %s"
        params.append(id)
    if nombre is not None:
        query += " AND nombre = %s"
        params.append(nombre)
    if descripcion is not None:
        query += " AND descripcion = %s"
        params.append(descripcion)
    if reflectancia_referencia is not None:
        query += " AND reflectancia_referencia = %s"
        params.append(reflectancia_referencia)
    query += " ORDER BY id"
    cursor.execute(query, params)
    return cursor.fetchall()

@app.put("/update/material", tags=["material"])
async def update_material(
    id: int,
    nombre: str,
    descripcion: Optional[str] = None,
    reflectancia_referencia: Optional[float] = None,
    db: DBConnection = Depends(get_db)
):
    conn, cursor = db
    cursor.execute(
        "UPDATE material SET nombre = %s, descripcion = %s, reflectancia_referencia = %s WHERE id = %s",
        (nombre, descripcion, reflectancia_referencia, id)
    )
    conn.commit()
    return {"message": "Material actualizado correctamente"}

@app.delete("/delete/material", tags=["material"])
async def delete_material(id: int, db: DBConnection = Depends(get_db)):
    conn, cursor = db
    cursor.execute("DELETE FROM material WHERE id = %s", (id,))
    conn.commit()
    return {"message": "Material eliminado correctamente"}


@app.post("/insert/reflectancia", tags=["reflectancia"])
async def insert_reflectancia(
    dispositivo_id: int,
    lectura_id: int,
    distancia_real: float,
    fecha: Optional[datetime] = None,
    valor: Optional[float] = None,
    material_id: Optional[int] = None,

    db: DBConnection = Depends(get_db)
):
    conn, cursor = db
    data = {
        "fecha": fecha,
        "dispositivo_id": dispositivo_id,
        "lectura_id": lectura_id,
        "distancia_real": distancia_real,
        "valor": valor,
        "material_id": material_id
    }
    query, valores = construir_insert("reflectancia", data)
    cursor.execute(query, valores)
    conn.commit()
    return {
        "message": "Reflectancia insertada correctamente",
        "datos_insertados": dict(zip(
            ["fecha", "dispositivo_id", "lectura_id", "distancia_real", "valor", "material_id"],
            valores
        ))
    }

@app.get("/select/reflectancia/", tags=["reflectancia"])
async def get_reflectancia(
    id: Optional[int] = None,
    fecha: Optional[datetime] = None,
    dispositivo_id: Optional[int] = None,
    lectura_id: Optional[int] = None,
    distancia_real: Optional[float] = None,
    valor: Optional[float] = None,
    material_id: Optional[int] = None,
    db: DBConnection = Depends(get_db)
):
    conn, cursor = db
    query = "SELECT * FROM reflectancia WHERE TRUE"
    params = []
    if id is not None:
        query += " AND id = %s"
        params.append(id)
    if fecha is not None:
        query += " AND fecha = %s"
        params.append(fecha)
    if dispositivo_id is not None:
        query += " AND dispositivo_id = %s"
        params.append(dispositivo_id)
    if lectura_id is not None:
        query += " AND lectura_id = %s"
        params.append(lectura_id)
    if distancia_real is not None:
        query += " AND distancia_real = %s"
        params.append(distancia_real)
    if valor is not None:
        query += " AND valor = %s"
        params.append(valor)
    if material_id is not None:
        query += " AND material_id = %s"
        params.append(material_id)
    query += " ORDER BY id"
    cursor.execute(query, params)
    return cursor.fetchall()

@app.put("/update/reflectancia", tags=["reflectancia"])
async def update_reflectancia(
    id: int,
    fecha: Optional[datetime] = None,
    dispositivo_id: int = None,
    lectura_id: int = None,
    distancia_real: float = None,
    valor: Optional[float] = None,
    material_id: Optional[int] = None,
    db: DBConnection = Depends(get_db)
):
    conn, cursor = db
    cursor.execute(
        """
        UPDATE reflectancia
        SET fecha = %s,
            dispositivo_id = %s,
            lectura_id = %s,
            distancia_real = %s,
            valor = %s,
            material_id = %s
        WHERE id = %s
        """,
        (fecha, dispositivo_id, lectura_id, distancia_real, valor, material_id, id)
    )
    conn.commit()
    return {"message": "Reflectancia actualizada correctamente"}

@app.delete("/delete/reflectancia", tags=["reflectancia"])
async def delete_reflectancia(id: int, db: DBConnection = Depends(get_db)):
    conn, cursor = db
    cursor.execute("DELETE FROM reflectancia WHERE id = %s", (id,))
    conn.commit()
    return {"message": "Reflectancia eliminada correctamente"}












'''

# region formulario
@app.post("/insert/lectura", tags=["lectura"])

async def insert_lectura(
    sensor_id: int,
    valor: float | None = None,
    fecha: str | None = str(datetime.now())
):
    query, valores = construir_insert("lectura", {
        "sensor_id": sensor_id,
        "valor": valor,
        "fecha": fecha
    })
    cursor_obj.execute(query, valores)
    cc.commit()
    return {
        "message": "Lectura insertada correctamente",
        "datos_insertados": dict(zip(["sensor_id", "valor", "fecha"], valores))
    }
# endregion

# region x-www-form-urlencoded
@app.post("/x/insert/lectura", tags=["x-www-form-urlencoded"])
async def xinsert_lectura(
    sensor_id: int = Form(...),
    valor: float = Form(...),
    fecha: Optional[str] = Form(None)
):
    fecha_final = fecha or datetime.now().isoformat()
    
    query, valores = construir_insert("lectura", {
        "sensor_id": sensor_id,
        "valor": valor,
        "fecha": fecha_final
    })
    cursor_obj.execute(query, valores)
    cc.commit()
    return {
        "message": "Lectura insertada correctamente",
        "datos_insertados": {
            "sensor_id": sensor_id,
            "valor": valor,
            "fecha": fecha_final
        }
    }
# endregion
'''

# region json
# --- 
DBConnection = Tuple[psycopg2.extensions.connection, RealDictCursor]

class LecturaInput(BaseModel):
    sensor_id: int = Field(..., description="ID del sensor que envía la lectura")
    valor: float = Field(..., description="Valor leído por el sensor")
    fecha: Optional[str] = Field(None, format="date-time", description="Fecha y hora en formato ISO 8601 (opcional)")

@app.post("/sensor/insert/lectura", tags=["application/json", "sensor"])
async def insert_lectura(
    lectura: LecturaInput,
    db: DBConnection = Depends(get_db)
):
    conn, cursor = db

    try:
        fecha_final = fecha_final = datetime.fromisoformat(lectura.fecha).strftime("%Y-%m-%d %H:%M:%S") if lectura.fecha else datetime.now().isoformat()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use ISO 8601.")

    try:
        cursor.execute("""
            INSERT INTO lectura (sensor_id, valor, fecha)
            VALUES (%s, %s, %s)
        """, (lectura.sensor_id, lectura.valor, fecha_final))
        conn.commit()
        return {
            "message": "Lectura insertada correctamente",
            "datos_insertados": {
                "sensor_id": lectura.sensor_id,
                "valor": lectura.valor,
                "fecha": fecha_final
            }
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
# endregion
