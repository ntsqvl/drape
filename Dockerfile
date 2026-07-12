# DRAPE single-service image: FastAPI serves the built React frontend.
# Static assets (drapes, personas, catalog) are generated at build time.

FROM node:20-slim AS frontend
WORKDIR /fe
COPY frontend/package*.json ./
RUN npm ci
COPY frontend .
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend backend
COPY --from=frontend /fe/dist frontend/dist
RUN cd backend \
    && python scripts/make_drapes.py \
    && python scripts/make_personas.py \
    && python scripts/make_catalog.py

ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app:app --app-dir backend --host 0.0.0.0 --port ${PORT}"]
