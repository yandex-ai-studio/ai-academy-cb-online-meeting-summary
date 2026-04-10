# Dockerfile для Meeting Summarizer
FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Создание рабочей директории
WORKDIR /app

# Копирование requirements
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Создание необходимых директорий
RUN mkdir -p /app/uploads /app/results /app/static

# Установка переменных окружения
ENV PYTHONUNBUFFERED=1

# Экспорт порта
EXPOSE 8000

# Команда запуска
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]






