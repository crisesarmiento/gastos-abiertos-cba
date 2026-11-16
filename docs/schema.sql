-- Esquema DuckDB de gastos-abiertos-cba (v1). Montos DECIMAL(18,2); fechas ISO; CUIT 11 dígitos.
CREATE TABLE dim_ejercicio (ejercicio INTEGER PRIMARY KEY, id_vigencia INTEGER);          -- id_vigencia: id de API (cambia por año)
CREATE TABLE dim_jurisdiccion (ejercicio INTEGER, codigo VARCHAR, nombre VARCHAR, tipo VARCHAR, -- tipo: AC | EMAEE
                               id_api INTEGER, PRIMARY KEY (ejercicio, codigo, tipo));
CREATE TABLE dim_unidad (ejercicio INTEGER, jurisdiccion_codigo VARCHAR, codigo VARCHAR, nombre VARCHAR, id_api INTEGER);
CREATE TABLE dim_programa (ejercicio INTEGER, jurisdiccion_codigo VARCHAR, unidad_codigo VARCHAR, codigo VARCHAR, nombre VARCHAR, id_cat_prog INTEGER);
CREATE TABLE dim_partida (ejercicio INTEGER, codigo VARCHAR, nombre VARCHAR, nivel VARCHAR, id_api INTEGER); -- nivel: principal(inciso) | objeto
CREATE TABLE hecho_agregado (
  tipo VARCHAR,                -- AC | EMAEE
  ejercicio INTEGER, mes INTEGER, fecha_corte DATE,
  jurisdiccion_codigo VARCHAR, unidad VARCHAR, programa VARCHAR, partida_principal VARCHAR,
  finalidad VARCHAR, funcion VARCHAR,
  presupuesto_vigente DECIMAL(18,2), compromiso DECIMAL(18,2) /* NULL en EMAEE */,
  devengado DECIMAL(18,2), pagado DECIMAL(18,2),
  corrida_id VARCHAR);         -- acumulados: usar solo el corte más reciente por (tipo, ejercicio)
CREATE TABLE hecho_devengado (
  id_devengado BIGINT, ejercicio INTEGER, jurisdiccion_codigo VARCHAR, id_cat_prog INTEGER, id_objeto_gasto INTEGER,
  nro_comprobante VARCHAR, cuit CHAR(11), descripcion VARCHAR, importe DECIMAL(18,2), fecha DATE, corrida_id VARCHAR);
CREATE TABLE hecho_devengado_item (
  id_devengado BIGINT, n_item INTEGER, cantidad DECIMAL(18,4), importe DECIMAL(18,2), nombre_objeto VARCHAR, nombre VARCHAR);
CREATE TABLE meta_corrida (
  corrida_id VARCHAR PRIMARY KEY, fuente VARCHAR, url VARCHAR, fecha_utc TIMESTAMP, filas BIGINT, sha256 VARCHAR, notas VARCHAR);
