-- Script de creacion de base de datos SQL Server
-- Sistema Consolidador REM

USE master;
GO

CREATE DATABASE consolidador_rem;
GO

USE consolidador_rem;
GO

CREATE TABLE programas (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    activo BIT NOT NULL DEFAULT 1
);

CREATE TABLE usuarios (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    rol VARCHAR(20) NOT NULL CHECK (rol IN ('admin', 'encargado')),
    programa_id INT NULL REFERENCES programas(id),
    activo BIT NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT GETDATE()
);

CREATE TABLE archivos (
    id INT IDENTITY(1,1) PRIMARY KEY,
    usuario_id INT NOT NULL REFERENCES usuarios(id),
    programa_id INT NOT NULL REFERENCES programas(id),
    nombre_archivo VARCHAR(255) NOT NULL,
    ruta_archivo VARCHAR(500) NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente'
        CHECK (estado IN ('pendiente', 'validado', 'rechazado', 'consolidado')),
    observaciones TEXT NULL,
    validado_por INT NULL REFERENCES usuarios(id),
    fecha_subida DATETIME NOT NULL DEFAULT GETDATE(),
    fecha_validacion DATETIME NULL,
    activo BIT NOT NULL DEFAULT 1
);

CREATE TABLE consolidaciones (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nombre_archivo VARCHAR(255) NOT NULL,
    ruta_archivo VARCHAR(500) NOT NULL,
    archivos_count INT NOT NULL,
    creado_por INT NOT NULL REFERENCES usuarios(id),
    fecha DATETIME NOT NULL DEFAULT GETDATE()
);

CREATE TABLE consolidacion_archivos (
    id INT IDENTITY(1,1) PRIMARY KEY,
    consolidacion_id INT NOT NULL REFERENCES consolidaciones(id),
    archivo_id INT NOT NULL REFERENCES archivos(id)
);

CREATE TABLE log_actividad (
    id INT IDENTITY(1,1) PRIMARY KEY,
    usuario_id INT NOT NULL REFERENCES usuarios(id),
    accion VARCHAR(50) NOT NULL,
    detalle VARCHAR(500) NULL,
    archivo_id INT NULL REFERENCES archivos(id),
    consolidacion_id INT NULL REFERENCES consolidaciones(id),
    fecha DATETIME NOT NULL DEFAULT GETDATE()
);

-- Indices
CREATE INDEX IX_usuarios_email ON usuarios(email);
CREATE INDEX IX_archivos_programa ON archivos(programa_id);
CREATE INDEX IX_archivos_estado ON archivos(estado);
CREATE INDEX IX_log_fecha ON log_actividad(fecha DESC);

-- Usuario admin inicial (password: admin)
INSERT INTO usuarios (nombre, email, password_hash, rol, activo)
VALUES ('Administrador', 'admin@maipu.cl', 
        '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 
        'admin', 1);

-- Programas de ejemplo
INSERT INTO programas (nombre) VALUES 
('CESFAM Norte'), ('CESFAM Sur'), ('CESFAM Este');

GO
