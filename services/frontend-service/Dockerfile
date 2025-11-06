FROM python:3.11-slim
WORKDIR /app

# Copy whole project so frontend can serve templates from monolith app
COPY . /app

ENV PYTHONPATH=/app

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
