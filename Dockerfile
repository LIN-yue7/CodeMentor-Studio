FROM node:22-bookworm-slim AS frontend
WORKDIR /build/workbench-web
COPY workbench-web/package.json workbench-web/package-lock.json ./
RUN npm ci
COPY workbench-web/ ./
RUN npm run build

FROM python:3.11-slim-bookworm
WORKDIR /srv/codementor
ENV CODEMENTOR_AI_MODE=local \
    DATABASE__SQLITE_PATH=/srv/data/studio.db \
    PYTHONUNBUFFERED=1
COPY requirements-lock.txt ./
RUN pip install --no-cache-dir -r requirements-lock.txt \
    && useradd --create-home --uid 10001 codementor \
    && mkdir -p /srv/data /srv/codementor/data/library \
    && chown -R codementor:codementor /srv/data /srv/codementor/data
COPY app/ ./app/
COPY examples/studio-r9/ ./examples/studio-r9/
COPY --from=frontend /build/workbench-web/dist ./workbench-web/dist
USER codementor
EXPOSE 10000
CMD ["sh", "-c", "exec uvicorn app.workbench:app --host 0.0.0.0 --port ${PORT:-10000} --proxy-headers --forwarded-allow-ips '*' --limit-concurrency 24"]
