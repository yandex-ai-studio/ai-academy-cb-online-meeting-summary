"""
FastAPI приложение для саммаризации встреч
"""
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import logging
from pathlib import Path
from typing import Dict, Optional
import asyncio
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

from services.audio_processor import AudioProcessor
from services.transcription_service import TranscriptionService
from services.summarization_service import SummarizationService

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создание приложения
app = FastAPI(title="Meeting Summarizer", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Монтирование статических файлов
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Хранение задач в памяти
tasks: Dict[str, dict] = {}

# Создание необходимых директорий
UPLOAD_DIR = Path("uploads")
RESULTS_DIR = Path("results")
UPLOAD_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

# Инициализация сервисов (ленивая инициализация при первом использовании)
audio_processor = None
transcription_service = None
summarization_service = None


def get_audio_processor():
    """Ленивая инициализация AudioProcessor"""
    global audio_processor
    if audio_processor is None:
        audio_processor = AudioProcessor()
    return audio_processor


def get_transcription_service():
    """Ленивая инициализация TranscriptionService"""
    global transcription_service
    if transcription_service is None:
        transcription_service = TranscriptionService()
    return transcription_service


def get_summarization_service():
    """Ленивая инициализация SummarizationService"""
    global summarization_service
    if summarization_service is None:
        summarization_service = SummarizationService()
    return summarization_service


def update_task_status(task_id: str, status: str, progress: int = 0, message: str = "", result: Optional[dict] = None):
    """Обновление статуса задачи"""
    if task_id not in tasks:
        tasks[task_id] = {
            "task_id": task_id,
            "status": status,
            "progress": progress,
            "message": message,
            "result": result
        }
    else:
        tasks[task_id].update({
            "status": status,
            "progress": progress,
            "message": message
        })
        if result is not None:
            tasks[task_id]["result"] = result


async def process_meeting(task_id: str, file_path: str, credentials: Optional[dict] = None):
    """Асинхронная обработка встречи"""
    credentials = credentials or {}
    try:
        update_task_status(task_id, "processing", 10, "Начало обработки файла...")
        
        # Шаг 1: Конвертация аудио
        logger.info(f"Task {task_id}: Converting audio...")
        update_task_status(task_id, "processing", 20, "Конвертация аудио...")
        audio_path = await get_audio_processor().process_file(file_path)
        
        # Шаг 2: Транскрибация
        logger.info(f"Task {task_id}: Transcribing...")
        update_task_status(task_id, "processing", 50, "Транскрибация аудио...")
        transcription = await get_transcription_service().transcribe(
            audio_path,
            api_key=credentials.get("yandex_api_key"),
            folder_id=credentials.get("yandex_folder_id"),
        )
        
        # Шаг 3: Саммаризация и разделение спикеров
        logger.info(f"Task {task_id}: Summarizing...")
        update_task_status(task_id, "processing", 80, "Создание саммари и разделение спикеров...")
        summary_result = await get_summarization_service().summarize_with_speakers(
            transcription,
            api_key=credentials.get("yandex_api_key"),
            folder_id=credentials.get("yandex_folder_id"),
            gpt_api_key=credentials.get("yandex_gpt_api_key"),
        )
        
        # Шаг 4: Формирование результата
        result = {
            "summary": summary_result.get("summary", {}),
            "speakers": summary_result.get("speakers", []),
            "transcription": transcription,
            "duration": summary_result.get("duration", 0)
        }
        
        # Сохранение результата
        result_file = RESULTS_DIR / f"{task_id}.json"
        import json
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        update_task_status(task_id, "completed", 100, "Обработка завершена", result)
        logger.info(f"Task {task_id}: Completed successfully")
        
    except Exception as e:
        logger.error(f"Task {task_id}: Error - {str(e)}", exc_info=True)
        update_task_status(task_id, "failed", 0, f"Ошибка обработки: {str(e)}")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Главная страница с UI"""
    static_file = static_path / "index.html"
    if static_file.exists():
        with open(static_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Meeting Summarizer API</h1><p>UI not found. Use /docs for API documentation.</p>")


@app.post("/api/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    yandex_api_key: Optional[str] = Form(None),
    yandex_folder_id: Optional[str] = Form(None),
    yandex_gpt_api_key: Optional[str] = Form(None),
):
    """Загрузка файла для обработки"""
    try:
        # Генерация task_id
        task_id = str(uuid.uuid4())
        
        # Валидация файла
        if not file.filename:
            raise HTTPException(status_code=400, detail="Имя файла не указано")
        
        # Проверка расширения
        allowed_extensions = {".mp4", ".mp3", ".wav", ".ogg"}
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Неподдерживаемый формат файла. Разрешены: {', '.join(allowed_extensions)}"
            )
        
        # Сохранение файла
        file_path = UPLOAD_DIR / f"{task_id}{file_ext}"
        with open(file_path, "wb") as f:
            content = await file.read()
            # Проверка размера (2GB максимум)
            max_size = 2 * 1024 * 1024 * 1024  # 2GB
            if len(content) > max_size:
                raise HTTPException(status_code=400, detail="Файл слишком большой (максимум 2GB)")
            f.write(content)
        
        # Инициализация задачи
        update_task_status(task_id, "pending", 0, "Файл загружен, ожидание обработки...")
        
        creds = {
            "yandex_api_key": (yandex_api_key or "").strip() or None,
            "yandex_folder_id": (yandex_folder_id or "").strip() or None,
            "yandex_gpt_api_key": (yandex_gpt_api_key or "").strip() or None,
        }
        
        # Запуск фоновой задачи
        background_tasks.add_task(process_meeting, task_id, str(file_path), creds)
        
        return JSONResponse({
            "task_id": task_id,
            "status": "pending",
            "message": "Файл загружен успешно"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки файла: {str(e)}")


@app.get("/api/status/{task_id}")
async def get_status(task_id: str):
    """Получение статуса задачи"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    task = tasks[task_id]
    return JSONResponse({
        "task_id": task_id,
        "status": task["status"],
        "progress": task["progress"],
        "message": task["message"]
    })


@app.get("/api/result/{task_id}")
async def get_result(task_id: str):
    """Получение результата обработки"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    task = tasks[task_id]
    
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Задача еще не завершена. Статус: {task['status']}")
    
    if task["result"] is None:
        raise HTTPException(status_code=404, detail="Результат не найден")
    
    return JSONResponse(task["result"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

