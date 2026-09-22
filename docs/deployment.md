# Deployment

The entire stack is packaged into a standard `docker-compose.yml` for reproducibility.

## Containers
- `flood_db`: `postgis/postgis:15-3.3`. Ephemeral data is bound to the `postgis_data` volume.
- `flood_backend`: Python 3.11. Contains `libpq-dev` and `gdal-bin` directly in the image to satisfy GeoPandas `C_INCLUDE_PATH` requirements. Exposes 8000.
- `flood_frontend`: Multi-stage build. Uses Node 20 to compile Vite, then serves static assets via an Alpine NGINX layer on port 3000.

## Environment Variables
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `DATABASE_URL`

These are piped natively from a root `.env` file through docker-compose. Secrets are explicitly excluded via `.gitignore`.
