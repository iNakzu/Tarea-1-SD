# Tarea 1 - Sistema de consultas con cache y generación de tráfico

Este proyecto implementa una arquitectura de microservicios para evaluar el comportamiento de una capa de caché frente a distintas cargas de consultas sobre un dataset de edificios por zona.

## Objetivo

Medir el efecto del cacheado sobre la latencia y la tasa de aciertos en consultas sobre el archivo `data/buildings.csv`, usando tres componentes principales:

- `response_generator`: resuelve consultas sobre el dataset en memoria.
- `cache_service`: consulta Redis primero y, si no encuentra la respuesta, delega en `response_generator` y registra métricas.
- `traffic_generator`: genera carga sintética con distribuciones uniforme o Zipf.

Además, el archivo `analizar_metricas.py` permite resumir los resultados almacenados en CSV.

## Arquitectura

El flujo es el siguiente:

1. `traffic_generator` envía solicitudes a `cache_service`.
2. `cache_service` busca la respuesta en Redis.
3. Si hay caché, devuelve la respuesta y registra un evento `hit`.
4. Si no hay caché, llama a `response_generator`, guarda la respuesta en Redis y registra un evento `miss`.
5. `response_generator` carga el dataset en memoria al iniciar y resuelve la consulta.

## Requisitos

- Docker Desktop instalado y ejecutándose.
- Docker Compose disponible.

## Estructura del proyecto

- `docker-compose.yml`: orquesta los servicios.
- `cache_service/`: API FastAPI con Redis y registro de métricas.
- `response_generator/`: API FastAPI que responde consultas sobre el dataset.
- `traffic_generator/`: API FastAPI que genera carga de trabajo.
- `data/`: datos de entrada.
- `metrics/`: archivo CSV generado por el servicio de caché.
- `resultados/`: resultados de ejecuciones anteriores.
- `analizar_metricas.py`: script para analizar un CSV de métricas.

## Cómo ejecutar

Desde la raíz del proyecto, ejecuta:

```bash
docker compose up --build
```

Si tu instalación usa la sintaxis antigua, también puedes probar:

```bash
docker-compose up --build
```

Los servicios quedarán disponibles en:

- Redis: `localhost:6379`
- `cache_service`: `http://localhost:8000`
- `response_generator`: `http://localhost:8001`
- `traffic_generator`: `http://localhost:8002`

Para detener todo:

```bash
docker compose down
```

## Endpoints principales

### `cache_service`

- `GET /health`: verifica que el servicio está activo.
- `POST /query`: recibe una consulta, revisa Redis y, si no existe, la resuelve con `response_generator`.

Ejemplo de cuerpo:

```json
{
	"type": "Q1",
	"params": {
		"zone_id": "Z1",
		"confidence_min": 0.5
	}
}
```

### `response_generator`

- `GET /health`: verifica que el servicio está activo.
- `POST /query`: resuelve la consulta directamente sobre el dataset.

Tipos de consulta:

- `Q1`: cuenta registros por zona y umbral de confianza.
- `Q2`: calcula promedio, total y cantidad de área por zona.
- `Q3`: calcula densidad como registros por km2.
- `Q4`: compara densidad entre dos zonas y devuelve la ganadora.
- `Q5`: construye la distribución de confianza en bins.

Ejemplos de parámetros:

```json
{
	"type": "Q4",
	"params": {
		"zone_a": "Z1",
		"zone_b": "Z2",
		"confidence_min": 0.7
	}
}
```

```json
{
	"type": "Q5",
	"params": {
		"zone_id": "Z3",
		"bins": 10
	}
}
```

### `traffic_generator`

- `GET /health`: verifica que el servicio está activo.
- `POST /run`: genera y ejecuta solicitudes contra `cache_service`.

Ejemplo de cuerpo:

```json
{
	"distribution": "zipf",
	"n_requests": 100
}
```

Valores posibles de `distribution`:

- `uniform`: selecciona zonas y consultas de forma uniforme.
- `zipf`: favorece unas zonas más que otras siguiendo una distribución Zipf.

## Variables de entorno

`docker-compose.yml` configura estas variables:

- `REDIS_HOST`: host de Redis usado por `cache_service`.
- `REDIS_PORT`: puerto de Redis.
- `RESPONSE_GENERATOR_URL`: URL interna del servicio de consultas.
- `CACHE_TTL`: tiempo de vida de las entradas en caché, en segundos.
- `CACHE_URL`: URL interna de `cache_service` usada por `traffic_generator`.

## Métricas

Cada solicitud atendida por `cache_service` agrega una fila en `metrics/metrics.csv` con:

- tipo de evento (`hit` o `miss`)
- tipo de consulta
- latencia en milisegundos
- clave de caché
- timestamp

Para analizar un archivo CSV:

```bash
python analizar_metricas.py metrics/metrics.csv
```

El script reporta:

- total de consultas
- hits y misses
- hit rate y miss rate
- latencia promedio
- latencia p50
- latencia p95

## Notas de implementación

- `response_generator` carga `data/buildings.csv` en memoria al iniciar.
- `cache_service` usa Redis con política `allkeys-lru` según el archivo de composición.
- Los resultados históricos de experimentos se guardan en `resultados/`.

## Flujo recomendado de prueba

1. Levantar los servicios con Docker Compose.
2. Ejecutar una prueba de tráfico, por ejemplo con `distribution = zipf` y `n_requests = 100`.
3. Revisar el archivo `metrics/metrics.csv`.
4. Analizar el CSV con `analizar_metricas.py`.

