FROM python:3.11-slim
WORKDIR /app

# Копируем сервис и shared
COPY services/auth-service/ /app/
COPY shared/ /app/shared/

ENV PYTHONPATH=/app

# Установим минимальные системные пакеты, чтобы psycopg2 и зависимости компилировались корректно
RUN apt-get update && \
	apt-get install -y --no-install-recommends gcc build-essential libpq-dev && \
	rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
