FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Сначала зависимости — для кеша слоёв
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Код
COPY . .

# обязательно копируем пакет с json-ами
COPY cake_data/ cake_data/

# Каталог для БД (в контейнере)
RUN mkdir -p /data
ENV DB_PATH=/data/exchange_rates.db

#renamed to Dockerfile

CMD ["python", "main.py"]