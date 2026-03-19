# 🚀 BACKEND API - CONSOLIDADOR REM

## 📦 Backend FastAPI Completo - Listo para Producción

Este es el backend completo que cumple el 100% de la especificación del frontend React.

---

## ⚡ INSTALACIÓN RÁPIDA (3 PASOS)

### 1️⃣ Instalar Requisitos Previos

**Python 3.8+**
- Descargar: https://www.python.org/downloads/
- ✅ Marcar "Add Python to PATH" durante instalación

**SQL Server**
- SQL Server Express (gratis): https://www.microsoft.com/sql-server
- O usar instancia existente

**ODBC Driver 17 para SQL Server**
- Descargar: https://docs.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server

---

### 2️⃣ Configurar Base de Datos

**Ejecutar en SQL Server Management Studio:**
```sql
-- Abrir y ejecutar: database_setup.sql
-- Esto crea todas las tablas + usuario admin inicial
```

**Usuario creado:**
- Email: admin@maipu.cl
- Password: admin (con bcrypt)

---

### 3️⃣ Configurar y Ejecutar

**Windows:**
```cmd
1. Doble clic en start.bat
2. Editar .env con credenciales SQL Server
3. Reiniciar start.bat
```

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
# Editar .env con credenciales
./start.sh
```

**Manual:**
```bash
pip install -r requirements.txt
copy .env.example .env  # Windows
cp .env.example .env    # Linux/Mac
# Editar .env
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## ✅ Verificar Instalación

1. **API funcionando:**
   http://localhost:8000

2. **Documentación interactiva:**
   http://localhost:8000/docs

3. **Probar login:**
   ```bash
   POST http://localhost:8000/auth/login
   {
     "email": "admin@maipu.cl",
     "password": "admin"
   }
   ```

---

## 📁 Estructura del Proyecto

```
backend-fastapi/
├── main.py                          ⭐ API FastAPI completa
├── requirements.txt                 📦 Dependencias Python
├── .env.example                     🔧 Plantilla configuración
├── start.bat                        ▶️  Inicio Windows
├── start.sh                         ▶️  Inicio Linux/Mac
├── database_setup.sql               💾 Script SQL Server
├── ESPECIFICACION_CUMPLIDA.md      📋 Documentación cambios
├── README.md                        📖 Este archivo
├── uploads/                         📁 Archivos subidos (auto)
└── logs/                           📁 Logs (auto)
```

---

## 🔌 ENDPOINTS DISPONIBLES

### 🔐 Autenticación
- `POST /auth/register` - Registrar usuario
- `POST /auth/login` - Login (retorna JWT + programa_nombre)
- `GET /auth/me` - Usuario actual (incluye programa_nombre)
- `GET /usuarios` - Listar encargados (admin, con programa_nombre)

### 📁 Archivos
- `POST /archivos/upload` - Subir archivo .xlsm
- `GET /archivos` - Listar archivos (con JOINs: usuario_nombre, programa_nombre, validado_por_nombre)
- `POST /archivos/validar` - Validar/rechazar archivo (admin)

### 🔄 Consolidación
- `POST /consolidar` - Consolidar archivos (genera .xlsm real)
- `GET /consolidaciones` - Listar consolidaciones (con JOIN: creado_por_nombre)

### 🏥 Programas
- `GET /programas` - Listar programas
- `POST /programas` - Crear programa (admin)

### 📊 Logs
- `GET /logs` - Ver log de actividad (admin)

---

## ✨ CARACTERÍSTICAS IMPLEMENTADAS

✅ **Passwords con bcrypt** (seguridad mejorada)
✅ **Consolidación REAL** con openpyxl (genera .xlsm)
✅ **JOINs en todas consultas** (nombres legibles)
✅ **programa_nombre** en login y usuario actual
✅ **Endpoint GET /usuarios** para frontend
✅ **Archivos guardados físicamente** en disco
✅ **Macros VBA preservadas** en consolidación
✅ **Control de acceso por roles** (admin/encargado)
✅ **JWT en todos endpoints** protegidos
✅ **Log de auditoría** completo

---

## 🔐 SEGURIDAD

### Passwords
- **bcrypt** con salt automático
- No se almacenan passwords en texto plano
- Verificación segura en cada login

### JWT Tokens
- Expiración: 8 horas
- Algoritmo: HS256
- Incluye: user_id, email, rol

### Roles
- **Admin**: Validar, consolidar, ver logs, gestionar usuarios
- **Encargado**: Subir archivos de su programa

---

## 🌐 CONSUMIR DESDE FRONTEND

### Ejemplo Login:
```javascript
const response = await fetch('http://localhost:8000/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'admin@maipu.cl',
    password: 'admin'
  })
});

const { access_token, user } = await response.json();
// user incluye: programa_nombre
```

### Ejemplo Endpoint Protegido:
```javascript
const response = await fetch('http://localhost:8000/archivos', {
  headers: { 
    'Authorization': `Bearer ${access_token}` 
  }
});

const archivos = await response.json();
// Cada archivo incluye: usuario_nombre, programa_nombre, validado_por_nombre
```

### Ejemplo Subir Archivo:
```javascript
const formData = new FormData();
formData.append('file', file);
formData.append('programa_id', programaId);

const response = await fetch('http://localhost:8000/archivos/upload', {
  method: 'POST',
  headers: { 
    'Authorization': `Bearer ${access_token}` 
  },
  body: formData
});
```

---

## 🐛 SOLUCIÓN DE PROBLEMAS

### Error: "Python no reconocido"
→ Reinstalar Python marcando "Add to PATH"

### Error: "pyodbc.Error: Data source name not found"
→ Instalar ODBC Driver 18 para SQL Server

### Error: "Login failed for user"
→ Verificar credenciales en .env

### Error: "ModuleNotFoundError: No module named 'fastapi'"
→ `pip install -r requirements.txt`

### Error: "Port 8000 already in use"
→ Cambiar puerto en start.bat: `--port 8001`

### Error al consolidar archivos
→ Verificar que archivos existen en uploads/
→ Verificar permisos de escritura

---

## 📊 MIGRACION DE PASSWORDS EXISTENTES

Si ya tienes usuarios en tu BD con SHA256, tienes dos opciones:

**Opción 1: Reset de passwords** (Recomendado)
```sql
-- Los usuarios deberán crear nueva password
-- La nueva password se guardará con bcrypt automáticamente
```

**Opción 2: Script de conversión**
```python
# Crear script que regenere passwords con bcrypt
# (Requiere conocer passwords originales)
```

---

## 🚀 DESPLIEGUE EN PRODUCCIÓN

1. **Cambiar SECRET_KEY:**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   # Copiar resultado a .env
   ```

2. **Configurar CORS:**
   Editar `main.py` línea 29:
   ```python
   allow_origins=["https://tu-frontend.com"]
   ```

3. **Usar servidor WSGI:**
   ```bash
   gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

4. **Configurar HTTPS:**
   - Usar nginx como reverse proxy
   - Certificado SSL (Let's Encrypt)

---

## 📞 DOCUMENTACIÓN COMPLETA

- **Cambios implementados:** ESPECIFICACION_CUMPLIDA.md
- **Swagger UI:** http://localhost:8000/docs (después de iniciar)
- **ReDoc:** http://localhost:8000/redoc

---

## 📝 NOTAS IMPORTANTES

1. **Primer archivo es plantilla:** La consolidación usa el primer archivo validado como base
2. **Solo celdas editables:** Solo suma celdas numéricas no bloqueadas
3. **Macros preservadas:** Archivos .xlsm mantienen macros VBA
4. **Un archivo activo por programa:** Al subir nuevo, el anterior se desactiva
5. **Logs inmutables:** Toda acción queda registrada permanentemente

---

## ✅ CHECKLIST DE INSTALACIÓN

- [ ] Python 3.8+ instalado
- [ ] SQL Server instalado y corriendo
- [ ] ODBC Driver 18 instalado
- [ ] Base de datos creada (database_setup.sql ejecutado)
- [ ] Archivo .env configurado con credenciales
- [ ] Dependencias instaladas (pip install -r requirements.txt)
- [ ] API iniciada (start.bat o start.sh)
- [ ] API accesible en http://localhost:8000
- [ ] Login funciona con admin@maipu.cl / admin
- [ ] Frontend puede consumir endpoints

---

**Versión:** 2.0.0  
**Estado:** ✅ PRODUCCIÓN READY  
**Cumplimiento Especificación:** 100%

---

Municipalidad de Maipú - Dirección de Salud  
Backend API FastAPI + SQL Server  
Febrero 2026
