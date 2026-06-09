# Copa Analyst — imagem única (API FastAPI + UI React buildada)
# Estágio 1: build do frontend
FROM node:20-slim AS frontend
WORKDIR /web
COPY web/package*.json ./
# npm install (não 'ci'): tolerante a lockfile dessincronizado — robusto para o deploy
RUN npm install --no-audit --no-fund
COPY web/ ./
RUN npm run build      # gera /web/dist

# Estágio 2: runtime Python
FROM python:3.12-slim
WORKDIR /app

# Dependências Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Código + prompts + banco-semente
COPY src/ ./src/
COPY prompts/ ./prompts/
COPY deploy/ ./deploy/

# UI buildada do estágio anterior
COPY --from=frontend /web/dist ./web/dist

# Banco persistente fica no volume montado em /data (ver COPA_DB_PATH)
ENV COPA_DB_PATH=/data/copa_analyst.db
ENV PORT=8000
EXPOSE 8000

# Usa $PORT (Render/Fly injetam a porta); shell form para expandir a variável
CMD uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
