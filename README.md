# Meeting Summarizer - Саммаризация встреч

Система для автоматической транскрибации и саммаризации встреч с разделением на двух спикеров. Использует Yandex SpeechKit для транскрибации и YandexGPT для разделения спикеров и создания саммари.

## Возможности

- 🎤 Транскрибация аудио и видео через Yandex SpeechKit
- 👥 Автоматическое разделение на двух спикеров через YandexGPT
- 📝 Создание структурированного саммари встречи
- 🐳 Docker-контейнеризация для лёгкого развёртывания
- 🌐 Веб-интерфейс для загрузки файлов и просмотра результатов

## Требования

- Docker 20.10+ и Docker Compose;
- Yandex Cloud API ключ;
- Yandex Cloud Folder ID;
- YandexGPT API-ключ (можно использовать тот же, что и для SpeechKit).

## Установка и запуск

### 1. Клонирование и настройка

```bash
# Клонируйте репозиторий (или используйте текущую директорию)
cd 2025-NOV-Speechkit-Summarizer
```

### 2. Настройка переменных окружения (опционально)

Вы можете указать ключи двумя способами:

#### Первый вариант. Через `.env`

1. Создайте файл `.env` на основе `.env.example`:
   ```bash
   cp .env.example .env
   ```
2. Укажите ваши ключи:
   ```env
   YANDEX_API_KEY=your_yandex_api_key_here
   YANDEX_FOLDER_ID=your_folder_id_here
   YANDEXGPT_API_KEY=your_yandex_api_key_here
   ```

#### Второй вариант. Через UI

После запуска приложения откройте `http://localhost:8000`, найдите блок **«Настройки доступа»** и введите API-ключи и Folder ID прямо в браузере. Ключи:
- сохраняются в вашем `localStorage`;
- не отправляются и не сохраняются на сервере, пока вы не запускаете обработку файла;
- автоматически подставляются в каждый запрос.

В UI также доступно модальное окно «Как получить ключи?» с пошаговой инструкцией по созданию сервисного аккаунта и выдаче ролей.

### 3. Получение API ключей

#### Yandex Cloud API Key и Folder ID:

1. Зайдите в [Yandex Cloud Console](https://console.cloud.yandex.ru/).
2. Создайте сервисный аккаунт.
3. Назначьте роли: `ai.speechkit-stt.user` и `ai.languageModels.user`.
4. Создайте API-ключ для сервисного аккаунта.
5. Скопируйте Folder ID из URL или настроек облака.

#### YandexGPT API:

- Используйте тот же API ключ, что и для SpeechKit.
- Или создайте отдельный ключ с правами на использование YandexGPT.

### 4. Запуск через Docker Compose

```bash
# Сборка образа
docker-compose build

# Запуск контейнера
docker-compose up -d

# Просмотр логов
docker-compose logs -f meeting-summarizer
```

### 5. Использование

Откройте в браузере: `http://localhost:8000`

## Использование API

### Загрузка файла

```bash
curl -X POST "http://localhost:8000/api/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/meeting.mp4"
```

Ответ:
```json
{
  "task_id": "uuid-here",
  "status": "pending",
  "message": "Файл загружен успешно"
}
```

### Проверка статуса

```bash
curl -X GET "http://localhost:8000/api/status/{task_id}"
```

Ответ:
```json
{
  "task_id": "uuid-here",
  "status": "processing",
  "progress": 50,
  "message": "Транскрибация аудио..."
}
```

### Получение результата

```bash
curl -X GET "http://localhost:8000/api/result/{task_id}"
```

Ответ:
```json
{
  "summary": {
    "topic": "Обсуждение проекта",
    "overall_summary": "Краткое резюме встречи...",
    "key_points": ["Пункт 1", "Пункт 2"]
  },
  "speakers": [
    {
      "speaker_id": 1,
      "name": "Спикер 1",
      "segments": [
        {
          "text": "Реплика спикера 1",
          "order": 1
        }
      ],
      "summary": "Резюме высказываний спикера 1"
    },
    {
      "speaker_id": 2,
      "name": "Спикер 2",
      "segments": [...],
      "summary": "Резюме высказываний спикера 2"
    }
  ],
  "transcription": "Полный текст транскрипции...",
  "duration": 3600
}
```

## Структура проекта

```
/
├── Dockerfile                 # Docker-образ
├── docker-compose.yml         # Docker Compose конфигурация
├── requirements.txt           # Python-зависимости
├── .env.example              # Пример переменных окружения
├── .gitignore                # Git ignore файл
├── main.py                   # FastAPI-приложение
├── services/
│   ├── __init__.py
│   ├── audio_processor.py    # Конвертация аудио/видео
│   ├── transcription_service.py  # Yandex SpeechKit-транскрибация
│   └── summarization_service.py # YandexGPT-саммаризация
├── static/
│   ├── index.html            # Веб-интерфейс
│   ├── style.css             # Стили
│   └── app.js                # JavaScript логика
└── README.md                  # Документация
```

## Поддерживаемые форматы

- **Видео**: MP4
- **Аудио**: MP3, WAV, OGG
- **Максимальный размер**: 2GB

## Процесс обработки

1. **Загрузка файла** - файл сохраняется во временную директорию
2. **Конвертация аудио** - извлечение/конвертация в формат для SpeechKit (OGG Opus)
3. **Транскрибация** - преобразование аудио в текст через Yandex SpeechKit
4. **Саммаризация** - анализ транскрипта через YandexGPT:
   - разделение на двух спикеров;
   - определение темы встречи;
   - создание общего резюме;
   - выделение ключевых моментов;
   - резюме для каждого спикера.

## Остановка и очистка

```bash
# Остановка контейнера
docker-compose down

# Остановка с удалением volumes
docker-compose down -v
```

## Устранение неполадок

### Ошибка "YANDEX_API_KEY не установлен"

Убедитесь, что файл `.env` создан и содержит правильные ключи. Проверьте, что переменные окружения передаются в контейнер через `docker-compose.yml`.

### Ошибка транскрибации

- Проверьте права доступа API ключа к SpeechKit
- Убедитесь, что Folder ID указан правильно
- Проверьте формат аудио файла

### Ошибка саммаризации

- Проверьте права доступа API ключа к YandexGPT
- Убедитесь, что модель доступна в вашем облаке
- Проверьте лимиты API

### Проблемы с конвертацией аудио

- Убедитесь, что FFmpeg установлен в контейнере (включен в Dockerfile)
- Проверьте формат исходного файла

## Разработка

### Локальный запуск (без Docker)

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск приложения
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Тестирование

API документация доступна по адресу: `http://localhost:8000/docs`

## Лицензия

MIT

## Автор

2025 Meeting Summarizer Project
