# -*- coding: utf-8 -*-
"""
@author: jaimesoto
"""
# -*- coding: utf-8 -*-
"""
@Institución : IU Pascual Bravo
@author      : Profesor Jaime E Soto U
@email       : jaime.soto@pascualbravo.edu.co
@Departamento: Facultad de Ingeniería - Departamento de Sistemas Digitales
@asignatura  : ET01555 - Fundamentos de Bigdata 
@Tarea       : Tarea UNIDAD 1 - Procesamiento ETL (Extraction-Transformation-Load)

Data de Colombia
https://www.datos.gov.co/Mapas-Nacionales/Departamentos-y-municipios-de-Colombia/xdk5-pm3f/data
"""
#-------------------------------------------------------------------------
# UTILIZAR ESTE ALGORTIMO PARA VARIOS PROPÓSTIOS:
# 1.- Realizar el procedimiento de carga de los departamentos y municipios
# 2.- Incluir la modificación para agregar el campo "id_region" en la tabla "operaciones".
# 3.- Valorizar el código "id_region"
# NOTA: Previo a eso, se debe crear una tabla regiones y modificar
# la tabla "operaciones" para agregar el campo "id_region".  
# REQUERIMIENTO: Debe modificar el nombre del archivo y colocar el equipo (X)
#-------------------------------------------------------------------------


#-------------------------------------------------------------------------
# Paquetes y librerías
#-------------------------------------------------------------------------
import time
import sys
import re
import random
import pandas as pd
import psycopg2
from   psycopg2 import Error
import csv

# -------------------------------------------------------------------------
# Variables globales
# -------------------------------------------------------------------------
error_con = False
id_pais   = 57

#--------------------------------------------------------------------------
# Parámetros de conexión de la Base de datos local
# Estos son los parámteros que permiten la conexión con el PostgreSQL Local
#--------------------------------------------------------------------------
v_host	   = "localhost"
v_port	   = "5432"
v_database = "bigdata"
v_user	   = "postgres"
v_password = "berrio123"

#-----------------------------------------------------------------------------
# Función: Obtener número de código de Región
#-----------------------------------------------------------------------------
def getCodigoRegion(region):
    codigo_region = 0
    if region == "Region Eje Cafetero - Antioquia":
        codigo_region = 1
    elif region == "Region Centro Oriente":
         codigo_region = 2
    elif region == "Region Centro Sur":
         codigo_region = 3
    elif region == "Region Caribe":
         codigo_region = 4
    elif region == "Region Llano":
         codigo_region = 5
    elif region == "Region Pacifico":
         codigo_region = 6
    else:
         codigo_region = 0
    return codigo_region    

#-----------------------------------------------------------------------------
# Función:  Carga Tabla Temporal (Con Rollback defensivo para evitar transacciones abortadas)
#-----------------------------------------------------------------------------
def cargarTablaTemporal(conn, cursor, contador, 
                        nombre_region, codigo_region, 
                        codigo_dep, departamento, 
                        codigo_mun, municipio):
    
    print("Cargando temporal ... -> ", len(str(codigo_mun)), contador, 
          codigo_dep, codigo_mun, codigo_region, 
          departamento, municipio, nombre_region)

    if (len(str(codigo_mun)) > 10):
        print("Problemas con el código de departamento ... fila -> ", contador + 1)
        return

    try:
        comando_sql = '''INSERT INTO temporal(codigo_region, codigo_dep, codigo_mun, departamento, municipio, region) 
                         VALUES (%s,%s,%s,%s,%s,%s);'''
        cursor.execute(comando_sql, 
                       (codigo_region, codigo_dep, codigo_mun, departamento, municipio, nombre_region))
        conn.commit()
    except (Exception, Error) as error:
        print("Error en Carga Temporal: ", error)
        conn.rollback() # Limpia la transacción abortada para permitir continuar
    finally:
        pass

#----------------------------------------------------------------------------------
# Clase:  Cargar Departamentos
#----------------------------------------------------------------------------------
def cargarDepartamento(conn, cursor, 
                       codigo_departamento, nombre_departamento, 
                       codigo_region,
                       cantidad):
    try:
        id_pais         = 57
        sufijo          = str(codigo_departamento).zfill(2)
        id_departamento = int(str(id_pais) + sufijo)    
        nombre_dep      = nombre_departamento[0:50]
        print(sufijo, id_departamento, nombre_dep, codigo_departamento, codigo_region, cantidad)
        
        comando_sql = '''INSERT INTO departamentos (id_departamento, codigo_dane, nombre, codigo_region) 
                         VALUES (%s,%s,%s,%s);'''
        cursor.execute(comando_sql, 
                       (id_departamento, codigo_departamento, nombre_dep, codigo_region))
        conn.commit()
    except (Exception, Error) as error:
        print("Error en carga de Departamentos: ", error)
        conn.rollback()
    finally:
        pass

#-----------------------------------------------------------------------------
# Clase:  Cargar Municipios
#-----------------------------------------------------------------------------
def cargarMunicipio(conn, cursor, contador, codigo_dep, codigo_mun, municipio):
    try:
        sufijo          = str(codigo_dep).zfill(2)
        id_departamento = int(str(57) + sufijo)    
        sufijo          = str(contador).zfill(3)
        id_municipio    = int(str(id_departamento) + sufijo)    
        nombre_mun      = municipio[0:50]
        
        print("Carga de municipios: contador, sufijo, id_dep, id_mun, nom_mun, cod_mun: ", 
              contador, sufijo, id_departamento, id_municipio, nombre_mun, codigo_mun) 
    
        comando_sql = '''INSERT INTO municipios (id_departamento, id_municipio, nombre, codigo_dane) 
                         VALUES (%s,%s,%s,%s);'''
        cursor.execute(comando_sql, 
                       (id_departamento, id_municipio, nombre_mun, codigo_mun))
        conn.commit()
    except (Exception, Error) as error:
        print("Error en carga de Municipios: ", error)
        conn.rollback()
    finally:
        pass    

# --------------------------------------------------------------------------
# INICIO DEL PROGRAMA
# --------------------------------------------------------------------------
try:
    connection = psycopg2.connect(user=v_user, password=v_password, host=v_host,
                                  port=v_port, database=v_database)
    cursor = connection.cursor()
    cursor.execute("SELECT version();")
    record = cursor.fetchone()
    print("PostgreSQL Información del Servidor")
    print(connection.get_dsn_parameters(), "\n")    
    print("Python version: ", sys.version)    
    print("Estás conectado a - ", record, "\n")
    print("Base de datos:", v_database, "\n")
    
    # -------------------------------------------------------------------------
    # REQUERIMIENTO: Creación de tabla Regiones y modificación de operaciones
    # -------------------------------------------------------------------------
    print("Configurando esquema de Regiones y Operaciones...")
    
    # 1. Crear la tabla regiones si no existe (con sus columnas base comunes)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS regiones (
            id_region INT PRIMARY KEY,
            nombre_region VARCHAR(100)
        );
    ''')
    
    # 2. Asegurar columnas adicionales si existen restricciones (ej: descripcion)
    cursor.execute('''
        DO $$ 
        BEGIN 
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='regiones' and column_name='nombre_region') THEN
                ALTER TABLE regiones ADD COLUMN nombre_region VARCHAR(100);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='regiones' and column_name='descripcion') THEN
                ALTER TABLE regiones ADD COLUMN descripcion VARCHAR(255);
            END IF;
        END $$;
    ''')
    
    # 3. Insertar regiones base valorizando también la descripción para evitar el NOT NULL
    regiones_data = [
        (1, "Region Eje Cafetero - Antioquia", "Region Eje Cafetero - Antioquia"),
        (2, "Region Centro Oriente", "Region Centro Oriente"),
        (3, "Region Centro Sur", "Region Centro Sur"),
        (4, "Region Caribe", "Region Caribe"),
        (5, "Region Llano", "Region Llano"),
        (6, "Region Pacifico", "Region Pacifico")
    ]
    for reg_id, reg_nom, reg_desc in regiones_data:
        cursor.execute('''
            INSERT INTO regiones (id_region, nombre_region, descripcion) 
            VALUES (%s, %s, %s) 
            ON CONFLICT (id_region) DO UPDATE 
            SET nombre_region = EXCLUDED.nombre_region,
                descripcion = EXCLUDED.descripcion;
        ''', (reg_id, reg_nom, reg_desc))
        
    # 4. Modificar tabla "operaciones" para agregar el campo id_region si no existe
    cursor.execute('''
        DO $$ 
        BEGIN 
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='operaciones' and column_name='id_region') THEN
                ALTER TABLE operaciones ADD COLUMN id_region INT;
            END IF;
        END $$;
    ''')
    connection.commit()
    # -------------------------------------------------------------------------
    # LIMPIEZA DE TABLAS PRINCIPALES
    # -------------------------------------------------------------------------
    cursor.execute('''TRUNCATE temporal CASCADE;''')    
    cursor.execute('''TRUNCATE departamentos CASCADE;''')
    cursor.execute('''TRUNCATE municipios CASCADE;''')
    connection.commit()    
except (Exception, Error) as error:
    print("Error en conexión o configuración inicial: ", error)
    error_con = True
finally:
    if (error_con):            
        sys.exit("Error de conexión con servidor PostgreSQL")

# ------------------------------------------------------------------------- 
# Extracción de Datos - Hoja de Cálculo (CSV)
# ------------------------------------------------------------------------- 
try:
    archivo_fisico = 'colombia-dane-departamentos.csv'

    with open(archivo_fisico, encoding='utf-8') as File:
        hoja_calculo = csv.reader(File, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)   
        
        col_nom_reg = 0 
        col_cod_dep = 1 
        col_nom_dep = 2 
        col_cod_mun = 3 
        col_nom_mun = 4 
        
        contador_registros = 0        
        for fila in hoja_calculo:
            if (contador_registros > 0):
                if len(fila) >= 5:
                    nombre_region = fila[col_nom_reg]
                    codigo_region = getCodigoRegion(nombre_region)  
                    cargarTablaTemporal(connection, cursor, contador_registros, 
                                        nombre_region, 
                                        codigo_region,
                                        fila[col_cod_dep], 
                                        fila[col_nom_dep], 
                                        fila[col_cod_mun],
                                        fila[col_nom_mun])
            contador_registros = contador_registros + 1
except (Exception, Error) as error:
    print("Error (excepción): ", error)
    sys.exit("Error -> Fase Excel - Extracción hoja de cálculo -> carga tabla temporal")
finally:
    print("Tabla Temporal cargada ....")

# --------------------------------------------------------------------------
# CUERPO PRINCIPAL DEL PROGRAMA - PROCESAMIENTO DE DEPARTAMENTOS
# --------------------------------------------------------------------------
try:
    print("Inicia la carga de información en tablas definitivas...")

    # DEPARTAMENTOS 
    print("DEPARTAMENTOS")    
    comando_sql = '''SELECT distinct codigo_dep, departamento, codigo_region, count(*) as veces from temporal 
                     group by codigo_dep, departamento, codigo_region order by departamento'''
    cursor.execute(comando_sql)
    tuplas_tabla_temporal = cursor.fetchall()

    campo_cod_dep = 0   
    campo_nom_dep = 1   
    campo_cod_reg = 2   
    campo_can_mun = 3   
   
    for tupla in tuplas_tabla_temporal:
        codigo_dep     = tupla[campo_cod_dep] 
        departamento   = tupla[campo_nom_dep]
        codigo_region  = tupla[campo_cod_reg]
        cantidad_mun   = tupla[campo_can_mun]
        cargarDepartamento(connection, cursor,
                           codigo_dep, departamento, codigo_region,
                           cantidad_mun) 

    # MUNICIPIOS
    print("MUNICIPIOS")    
    comando_sql = '''SELECT codigo_dep, codigo_mun, municipio from temporal order by departamento, municipio'''
    cursor.execute(comando_sql)    
    tuplas_tabla_temporal = cursor.fetchall()
    
    campo_1  = 0 
    campo_2  = 1 
    campo_3  = 2 
    contador = 0 
    codigo_old = ''
    
    for tupla in tuplas_tabla_temporal:
        codigo_dep  = tupla[campo_1] 
        codigo_mun  = tupla[campo_2] 
        municipio   = tupla[campo_3] 
        if (codigo_dep == codigo_old):
            contador   = contador + 1
        else:
            contador   = 1
        codigo_old = codigo_dep
        cargarMunicipio(connection, cursor, contador, codigo_dep, codigo_mun, municipio) 
# -------------------------------------------------------------------------
    # REQUERIMIENTO: Valorizar el campo id_region en la tabla operaciones
    # -------------------------------------------------------------------------
    print("Actualizando/Valorizando 'id_region' en la tabla operaciones...")
    
    # Hacemos el UPDATE relacionando 'operaciones' con 'municipios' y 'departamentos'
    # utilizando las columnas reales de tu base de datos normalizada:
    comando_sql = '''
        UPDATE operaciones AS op
        SET id_region = d.codigo_region
        FROM municipios AS m
        JOIN departamentos AS d ON m.id_departamento = d.id_departamento
        WHERE op.id_municipio = m.id_municipio;
    '''
    
    cursor.execute(comando_sql)
    connection.commit()
    print("¡El campo 'id_region' se ha valorizado correctamente en la tabla operaciones!")

    connection.close()    
    
except (Exception, Error) as error:
    print("Error de procesamiento de la tabla!", error)
    if connection:
        connection.rollback()
finally:
    if (connection):
        connection.close()
        print("Conexión PostgreSQL cerrada")    
        
print("Fin del proceso ETL")