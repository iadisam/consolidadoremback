"""
API REST para Sistema de Consolidación REM
FastAPI + SQL Server + pyodbc
Versión: 2.2.0
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, timedelta
import pyodbc
import bcrypt
import jwt
import os
from pathlib import Path
import shutil
from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell
from io import BytesIO

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv()

# ==================== CONFIGURACIÓN ====================
app = FastAPI(
    title="API Consolidador REM",
    description="API para gestión de archivos REM y consolidación",
    version="2.2.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración JWT
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("❌ ERROR: SECRET_KEY no configurada en .env")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

# Configuración SQL Server
DB_CONFIG = {
    "DRIVER": os.getenv("DB_DRIVER", "{ODBC Driver 17 for SQL Server}"),
    "SERVER": os.getenv("DB_SERVER"),
    "DATABASE": os.getenv("DB_NAME"),
    "UID": os.getenv("DB_USER"),
    "PWD": os.getenv("DB_PASSWORD"),
}

# Validar variables requeridas
required_vars = ["DB_SERVER", "DB_NAME", "DB_USER", "DB_PASSWORD"]
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"❌ ERROR: Variables faltantes en .env: {', '.join(missing_vars)}")

# Mostrar configuración (sin password)
print("="*60)
print("📊 CONFIGURACIÓN DE BASE DE DATOS:")
print(f"   SERVER: {DB_CONFIG['SERVER']}")
print(f"   DATABASE: {DB_CONFIG['DATABASE']}")
print(f"   USER: {DB_CONFIG['UID']}")
print(f"   PASSWORD: {'*' * len(DB_CONFIG['PWD']) if DB_CONFIG['PWD'] else 'NO CONFIGURADA'}")
print("="*60)

# Directorio de archivos
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Security
security = HTTPBearer()

# ====================MODELOS PYDANTIC ====================

class ProgramaBase(BaseModel):
    nombre: str

class ProgramaCreate(ProgramaBase):
    pass

class Programa(ProgramaBase):
    id: int
    activo: bool
    
    class Config:
        from_attributes = True

class UsuarioCreate(BaseModel):
    nombre: str
    email: EmailStr
    password: str
    rol: str
    programa_id: Optional[int] = None

class UsuarioLogin(BaseModel):
    email: EmailStr
    password: str

class Usuario(BaseModel):
    id: int
    nombre: str
    email: str
    rol: str
    programa_id: Optional[int]
    activo: bool
    created_at: datetime
    programa_nombre: Optional[str]
    
    class Config:
        from_attributes = True

class ArchivoUpload(BaseModel):
    programa_id: int

class ArchivoInfo(BaseModel):
    id: int
    usuario_id: int
    programa_id: int
    nombre_archivo: str
    estado: str
    observaciones: Optional[str]
    fecha_subida: datetime
    fecha_validacion: Optional[datetime]
    activo: bool
    usuario_nombre: str
    programa_nombre: str
    validado_por_nombre: Optional[str]
    
    class Config:
        from_attributes = True

class ValidacionArchivo(BaseModel):
    archivo_id: int
    estado: str
    observaciones: Optional[str] = None

class ConsolidacionCreate(BaseModel):
    archivos_ids: List[int]

class ConsolidacionInfo(BaseModel):
    id: int
    nombre_archivo: str
    archivos_count: int
    creado_por: int
    fecha: datetime
    creado_por_nombre: str
    
    class Config:
        from_attributes = True

# ==================== UTILIDADES ====================

def get_db_connection():
    """Crea conexión a SQL Server"""
    try:
        conn_str = ";".join([f"{k}={v}" for k, v in DB_CONFIG.items()])
        conn = pyodbc.connect(conn_str)
        return conn
    except Exception as e:
        print(f"❌ Error conectando a base de datos: {e}")
        raise HTTPException(status_code=500, detail=f"Error de conexión a base de datos: {str(e)}")

def hash_password(password: str) -> str:
    """Hashea password con bcrypt"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica password con bcrypt"""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

def create_access_token(data: dict):
    """Crea JWT token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    """Decodifica JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Obtiene usuario actual desde token"""
    token = credentials.credentials
    payload = decode_token(token)
    user_id = payload.get("user_id")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT u.id, u.nombre, u.email, u.rol, u.programa_id, u.activo,
               p.nombre as programa_nombre
        FROM usuarios u
        LEFT JOIN programas p ON u.programa_id = p.id
        WHERE u.id = ? AND u.activo = 1
    """, user_id)
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=401, detail="Usuario no válido")
    
    return {
        "id": row[0],
        "nombre": row[1],
        "email": row[2],
        "rol": row[3],
        "programa_id": row[4],
        "programa_nombre": row[6]
    }

def registrar_log(usuario_id: int, accion: str, detalle: str = None, 
                  archivo_id: int = None, consolidacion_id: int = None):
    """Registra actividad en log"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO log_actividad (usuario_id, accion, detalle, archivo_id, consolidacion_id)
            VALUES (?, ?, ?, ?, ?)
        """, usuario_id, accion, detalle, archivo_id, consolidacion_id)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️  Error registrando log: {e}")

# ==================== ENDPOINTS ====================

@app.get("/")
def root():
    """Health check"""
    return {
        "status": "ok",
        "service": "API Consolidador REM",
        "version": "2.2.0",
        "docs": "/docs"
    }

@app.get("/health")
def health_check():
    """Verificar estado de la API"""
    try:
        conn = get_db_connection()
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except:
        return {"status": "unhealthy", "database": "disconnected"}

# ==================== PLANTILLA ====================

@app.get("/plantilla/download")
def descargar_plantilla():
    """Descargar plantilla base SA_26_V1.2.xlsm"""
    plantilla_path = Path("SA_26_V1.2.xlsm")
    
    if not plantilla_path.exists():
        raise HTTPException(status_code=404, detail="Plantilla no encontrada. Coloque SA_26_V1.2.xlsm en la raíz del proyecto")
    
    return FileResponse(
        path=str(plantilla_path),
        filename="SA_26_V1.2.xlsm",
        media_type="application/vnd.ms-excel.sheet.macroEnabled.12"
    )

# ==================== AUTENTICACIÓN ====================

@app.post("/auth/register")
def register(usuario: UsuarioCreate):
    """Registrar nuevo usuario"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM usuarios WHERE email = ?", usuario.email)
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Email ya registrado")
    
    if usuario.rol not in ['admin', 'encargado']:
        conn.close()
        raise HTTPException(status_code=400, detail="Rol inválido")
    
    password_hash = hash_password(usuario.password)
    
    cursor.execute("""
        INSERT INTO usuarios (nombre, email, password_hash, rol, programa_id)
        VALUES (?, ?, ?, ?, ?)
    """, usuario.nombre, usuario.email, password_hash, usuario.rol, usuario.programa_id)
    
    conn.commit()
    user_id = cursor.execute("SELECT @@IDENTITY").fetchone()[0]
    conn.close()
    
    return {"message": "Usuario creado exitosamente", "user_id": user_id}

@app.post("/auth/login")
def login(credentials: UsuarioLogin):
    """Login y generar token"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT u.id, u.nombre, u.email, u.password_hash, u.rol, u.programa_id, u.activo,
               p.nombre as programa_nombre
        FROM usuarios u
        LEFT JOIN programas p ON u.programa_id = p.id
        WHERE u.email = ?
    """, credentials.email)
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    
    if not verify_password(credentials.password, row[3]):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    
    if not row[6]:
        raise HTTPException(status_code=401, detail="Usuario inactivo")
    
    token = create_access_token({
        "user_id": row[0],
        "email": row[2],
        "rol": row[4]
    })
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": row[0],
            "nombre": row[1],
            "email": row[2],
            "rol": row[4],
            "programa_id": row[5],
            "programa_nombre": row[7]
        }
    }

@app.get("/auth/me")
def get_me(current_user: dict = Depends(get_current_user)):
    """Obtener info del usuario actual"""
    return current_user

@app.get("/usuarios", response_model=List[Usuario])
def listar_usuarios(current_user: dict = Depends(get_current_user)):
    """Listar usuarios encargados con nombre de programa (solo admin)"""
    if current_user["rol"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.id, u.nombre, u.email, u.rol, u.programa_id, u.activo, u.created_at,
               p.nombre as programa_nombre
        FROM usuarios u
        LEFT JOIN programas p ON u.programa_id = p.id
        WHERE u.rol = 'encargado'
        ORDER BY u.nombre
    """)
    
    usuarios = []
    for row in cursor.fetchall():
        usuarios.append({
            "id": row[0],
            "nombre": row[1],
            "email": row[2],
            "rol": row[3],
            "programa_id": row[4],
            "activo": row[5],
            "created_at": row[6],
            "programa_nombre": row[7]
        })
    
    conn.close()
    return usuarios

# ==================== PROGRAMAS ====================

@app.get("/programas", response_model=List[Programa])
def listar_programas(current_user: dict = Depends(get_current_user)):
    """Listar todos los programas activos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, activo FROM programas WHERE activo = 1")
    
    programas = []
    for row in cursor.fetchall():
        programas.append({
            "id": row[0],
            "nombre": row[1],
            "activo": row[2]
        })
    
    conn.close()
    return programas

@app.post("/programas")
def crear_programa(programa: ProgramaCreate, current_user: dict = Depends(get_current_user)):
    """Crear nuevo programa (solo admin)"""
    if current_user["rol"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("INSERT INTO programas (nombre) VALUES (?)", programa.nombre)
        conn.commit()
        programa_id = cursor.execute("SELECT @@IDENTITY").fetchone()[0]
        conn.close()
        
        registrar_log(current_user["id"], "crear_programa", f"Programa: {programa.nombre}")
        
        return {"message": "Programa creado", "id": programa_id}
    except pyodbc.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Programa ya existe")

# ==================== ARCHIVOS ====================

@app.post("/archivos/upload")
async def subir_archivo(
    file: UploadFile = File(...),
    programa_id: int = None,
    current_user: dict = Depends(get_current_user)
):
    """Subir archivo REM"""
    
    if not file.filename.endswith('.xlsm'):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos .xlsm")
    
    if current_user["rol"] == "encargado":
        programa_id = current_user["programa_id"]
        if not programa_id:
            raise HTTPException(status_code=400, detail="Usuario sin programa asignado")
    
    if not programa_id:
        raise HTTPException(status_code=400, detail="programa_id requerido")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE archivos 
        SET activo = 0 
        WHERE programa_id = ? AND usuario_id = ? AND activo = 1
    """, programa_id, current_user["id"])
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{programa_id}_{timestamp}_{file.filename}"
    filepath = UPLOAD_DIR / filename
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    cursor.execute("""
        INSERT INTO archivos (usuario_id, programa_id, nombre_archivo, ruta_archivo, estado)
        VALUES (?, ?, ?, ?, 'pendiente')
    """, current_user["id"], programa_id, file.filename, str(filepath))
    
    conn.commit()
    archivo_id = cursor.execute("SELECT @@IDENTITY").fetchone()[0]
    conn.close()
    
    registrar_log(current_user["id"], "subir", f"Archivo: {file.filename}", archivo_id)
    
    return {
        "message": "Archivo subido exitosamente",
        "archivo_id": archivo_id,
        "filename": filename
    }

@app.get("/archivos", response_model=List[ArchivoInfo])
def listar_archivos(
    estado: Optional[str] = None,
    programa_id: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    """Listar archivos con información completa"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT a.id, a.usuario_id, a.programa_id, a.nombre_archivo, a.ruta_archivo,
               a.estado, a.observaciones, a.validado_por, a.fecha_subida, a.fecha_validacion, a.activo,
               u.nombre as usuario_nombre,
               p.nombre as programa_nombre,
               u2.nombre as validado_por_nombre
        FROM archivos a
        JOIN usuarios u ON a.usuario_id = u.id
        JOIN programas p ON a.programa_id = p.id
        LEFT JOIN usuarios u2 ON a.validado_por = u2.id
        WHERE a.activo = 1
    """
    params = []
    
    if current_user["rol"] == "encargado":
        query += " AND a.usuario_id = ?"
        params.append(current_user["id"])
    
    if estado:
        query += " AND a.estado = ?"
        params.append(estado)
    
    if programa_id:
        query += " AND a.programa_id = ?"
        params.append(programa_id)
    
    query += " ORDER BY a.fecha_subida DESC"
    
    cursor.execute(query, *params)
    
    archivos = []
    for row in cursor.fetchall():
        archivos.append({
            "id": row[0],
            "usuario_id": row[1],
            "programa_id": row[2],
            "nombre_archivo": row[3],
            "estado": row[5],
            "observaciones": row[6],
            "fecha_subida": row[8],
            "fecha_validacion": row[9],
            "activo": row[10],
            "usuario_nombre": row[11],
            "programa_nombre": row[12],
            "validado_por_nombre": row[13]
        })
    
    conn.close()
    return archivos

@app.get("/archivos/{archivo_id}/download")
def descargar_archivo(
    archivo_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Descargar archivo por ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, usuario_id, nombre_archivo, ruta_archivo, estado, activo
        FROM archivos
        WHERE id = ?
    """, archivo_id)
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    if current_user["rol"] == "encargado" and row[1] != current_user["id"]:
        raise HTTPException(status_code=403, detail="No tiene permiso para descargar este archivo")
    
    ruta_archivo = Path(row[3])
    if not ruta_archivo.exists():
        raise HTTPException(status_code=404, detail="Archivo físico no encontrado")
    
    return FileResponse(
        path=str(ruta_archivo),
        filename=row[2],
        media_type="application/vnd.ms-excel.sheet.macroEnabled.12"
    )

@app.post("/archivos/{archivo_id}/resubir")
async def resubir_archivo(
    archivo_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Re-subir archivo reparado por admin (solo admin)"""
    if current_user["rol"] != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores pueden re-subir archivos")
    
    if not file.filename.endswith('.xlsm'):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos .xlsm")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obtener archivo original
    cursor.execute("""
        SELECT id, usuario_id, programa_id, nombre_archivo, ruta_archivo
        FROM archivos
        WHERE id = ?
    """, archivo_id)
    
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    # Eliminar archivo físico anterior si existe
    ruta_anterior = Path(row[4])
    if ruta_anterior.exists():
        ruta_anterior.unlink()
    
    # Guardar nuevo archivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{row[2]}_{timestamp}_{file.filename}"
    filepath = UPLOAD_DIR / filename
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Actualizar registro: nuevo archivo, estado pendiente
    cursor.execute("""
        UPDATE archivos 
        SET nombre_archivo = ?, 
            ruta_archivo = ?,
            estado = 'pendiente', 
            observaciones = 'Documento reparado por administrador',
            validado_por = NULL,
            fecha_validacion = NULL,
            fecha_subida = GETDATE()
        WHERE id = ?
    """, file.filename, str(filepath), archivo_id)
    
    conn.commit()
    conn.close()
    
    registrar_log(current_user["id"], "resubir", f"Archivo reparado: {file.filename}", archivo_id)
    
    return {
        "message": "Archivo re-subido exitosamente",
        "archivo_id": archivo_id,
        "filename": filename
    }

@app.post("/archivos/validar")
def validar_archivo(
    validacion: ValidacionArchivo,
    current_user: dict = Depends(get_current_user)
):
    """Validar o rechazar archivo (solo admin)"""
    if current_user["rol"] != "admin":
        raise HTTPException(status_code=403, detail="Solo admin puede validar")
    
    if validacion.estado not in ['validado', 'rechazado']:
        raise HTTPException(status_code=400, detail="Estado inválido")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE archivos 
        SET estado = ?, observaciones = ?, validado_por = ?, fecha_validacion = GETDATE()
        WHERE id = ?
    """, validacion.estado, validacion.observaciones, current_user["id"], validacion.archivo_id)
    
    conn.commit()
    conn.close()
    
    accion = "validar" if validacion.estado == "validado" else "rechazar"
    registrar_log(current_user["id"], accion, validacion.observaciones, validacion.archivo_id)
    
    return {"message": f"Archivo {validacion.estado} exitosamente"}

# ==================== CONSOLIDACIÓN ====================

@app.post("/consolidar")
def consolidar_archivos_api(
    consolidacion: ConsolidacionCreate,
    current_user: dict = Depends(get_current_user)
):
    """Consolidar múltiples archivos validados (solo admin)"""
    if current_user["rol"] != "admin":
        raise HTTPException(status_code=403, detail="Solo admin puede consolidar")
    
    if len(consolidacion.archivos_ids) < 2:
        raise HTTPException(status_code=400, detail="Se requieren al menos 2 archivos")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    placeholders = ",".join(["?"] * len(consolidacion.archivos_ids))
    cursor.execute(f"""
        SELECT id, ruta_archivo FROM archivos 
        WHERE id IN ({placeholders}) AND estado = 'validado' AND activo = 1
    """, *consolidacion.archivos_ids)
    
    archivos = cursor.fetchall()
    
    if len(archivos) != len(consolidacion.archivos_ids):
        conn.close()
        raise HTTPException(status_code=400, detail="Algunos archivos no están validados")
    
    try:
        plantilla_path = archivos[0][1]
        wb_consolidado = load_workbook(plantilla_path, keep_vba=True)
        
        hojas_datos = [sheet for sheet in wb_consolidado.sheetnames 
                      if sheet not in ['NOMBRE', 'Control', 'MACROS']]
        
        for sheet_name in hojas_datos:
            ws_consolidado = wb_consolidado[sheet_name]
            celdas_editables = []
            
            for row in ws_consolidado.iter_rows():
                for cell in row:
                    if isinstance(cell, MergedCell):
                        continue
                    
                    if (cell.data_type == 'n' and not cell.protection.locked):
                        cell.value = 0
                        celdas_editables.append((cell.row, cell.column))
            
            for archivo_id, ruta_archivo in archivos:
                wb_fuente = load_workbook(ruta_archivo, data_only=True)
                
                if sheet_name in wb_fuente.sheetnames:
                    ws_fuente = wb_fuente[sheet_name]
                    
                    for row_idx, col_idx in celdas_editables:
                        cell_fuente = ws_fuente.cell(row=row_idx, column=col_idx)
                        cell_consolidado = ws_consolidado.cell(row=row_idx, column=col_idx)
                        
                        if isinstance(cell_fuente.value, (int, float)):
                            valor_actual = cell_consolidado.value
                            if isinstance(valor_actual, (int, float)):
                                cell_consolidado.value = valor_actual + cell_fuente.value
                            else:
                                cell_consolidado.value = cell_fuente.value
                
                wb_fuente.close()
        
        ws_nombre = wb_consolidado["NOMBRE"]
        ws_nombre["B2"].value = f"CONSOLIDADO DE {len(archivos)} ESTABLECIMIENTOS"
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_consolidado = f"REM_Consolidado_{timestamp}.xlsm"
        ruta_consolidado = UPLOAD_DIR / nombre_consolidado
        
        wb_consolidado.save(ruta_consolidado)
        wb_consolidado.close()
        
        cursor.execute("""
            INSERT INTO consolidaciones (nombre_archivo, ruta_archivo, archivos_count, creado_por)
            VALUES (?, ?, ?, ?)
        """, nombre_consolidado, str(ruta_consolidado), len(consolidacion.archivos_ids), current_user["id"])
        
        conn.commit()
        consolidacion_id = cursor.execute("SELECT @@IDENTITY").fetchone()[0]
        
        for archivo_id in consolidacion.archivos_ids:
            cursor.execute("""
                INSERT INTO consolidacion_archivos (consolidacion_id, archivo_id)
                VALUES (?, ?)
            """, consolidacion_id, archivo_id)
            
            cursor.execute("""
                UPDATE archivos SET estado = 'consolidado' WHERE id = ?
            """, archivo_id)
        
        conn.commit()
        conn.close()
        
        registrar_log(current_user["id"], "consolidar", 
                     f"{len(consolidacion.archivos_ids)} archivos", None, consolidacion_id)
        
        return {
            "message": "Consolidación exitosa",
            "consolidacion_id": consolidacion_id,
            "archivo": nombre_consolidado
        }
        
    except Exception as e:
        import traceback
        error_detallado = traceback.format_exc()
        print(f"❌ Error durante la consolidación: {error_detallado}")
        conn.close()
        raise HTTPException(status_code=500, detail=f"Error en consolidación: {str(e)}")

@app.get("/consolidaciones", response_model=List[ConsolidacionInfo])
def listar_consolidaciones(current_user: dict = Depends(get_current_user)):
    """Listar consolidaciones realizadas con nombre del creador"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT c.id, c.nombre_archivo, c.archivos_count, c.creado_por, c.fecha,
               u.nombre as creado_por_nombre
        FROM consolidaciones c
        JOIN usuarios u ON c.creado_por = u.id
        ORDER BY c.fecha DESC
    """)
    
    consolidaciones = []
    for row in cursor.fetchall():
        consolidaciones.append({
            "id": row[0],
            "nombre_archivo": row[1],
            "archivos_count": row[2],
            "creado_por": row[3],
            "fecha": row[4],
            "creado_por_nombre": row[5]
        })
    
    conn.close()
    return consolidaciones

@app.get("/consolidaciones/{consolidacion_id}/download")
def descargar_consolidacion(
    consolidacion_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Descargar archivo consolidado por ID (solo admin)"""
    if current_user["rol"] != "admin":
        raise HTTPException(status_code=403, detail="Solo admin puede descargar consolidaciones")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, nombre_archivo, ruta_archivo
        FROM consolidaciones
        WHERE id = ?
    """, consolidacion_id)
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Consolidación no encontrada")
    
    ruta_archivo = Path(row[2])
    if not ruta_archivo.exists():
        raise HTTPException(status_code=404, detail="Archivo consolidado no encontrado")
    
    return FileResponse(
        path=str(ruta_archivo),
        filename=row[1],
        media_type="application/vnd.ms-excel.sheet.macroEnabled.12"
    )

# ==================== LOGS ====================

@app.get("/logs")
def obtener_logs(
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
):
    """Obtener log de actividad (solo admin)"""
    if current_user["rol"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT l.*, u.nombre as usuario_nombre
        FROM log_actividad l
        JOIN usuarios u ON l.usuario_id = u.id
        ORDER BY l.fecha DESC
        OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY
    """, limit)
    
    logs = []
    for row in cursor.fetchall():
        logs.append({
            "id": row[0],
            "usuario_id": row[1],
            "usuario_nombre": row[7],
            "accion": row[2],
            "detalle": row[3],
            "archivo_id": row[4],
            "consolidacion_id": row[5],
            "fecha": row[6]
        })
    
    conn.close()
    return logs

# ==================== INICIO ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
