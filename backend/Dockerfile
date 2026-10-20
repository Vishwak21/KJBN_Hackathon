FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend backend
RUN useradd --create-home appuser && mkdir -p /app/data && chown -R appuser /app
USER appuser
ENV DATABASE_PATH=/app/data/procurement.db
EXPOSE 8000
CMD ["sh", "-c", "python -m backend.seed && python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000"]
