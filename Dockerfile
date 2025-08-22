FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Сначала зависимости — кеш слоёв
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Копируем json-ы отдельно — на всякий
COPY cake_data/ cake_data/

# Cloud Run передаёт порт через переменную окружения $PORT
# Обязательно слушать на этом порту внутри контейнера
EXPOSE 8080

# Запускаем бота
CMD ["python", "main.py"]