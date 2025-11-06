FROM python:3.11-slim
WORKDIR /app

# Copy service and shared
COPY services/products-service/ /app/
COPY shared/ /app/shared/

ENV PYTHONPATH=/app

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
