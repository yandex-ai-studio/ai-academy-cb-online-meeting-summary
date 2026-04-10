"""
Сервис транскрибации через Yandex SpeechKit REST API
"""
import os
import logging
from typing import Optional
from pathlib import Path
import httpx

logger = logging.getLogger(__name__)


class TranscriptionService:
    """Сервис для транскрибации аудио через Yandex SpeechKit REST API"""
    
    def __init__(self, default_api_key: Optional[str] = None, default_folder_id: Optional[str] = None):
        self.default_api_key = default_api_key or os.getenv("YANDEX_API_KEY")
        self.default_folder_id = default_folder_id or os.getenv("YANDEX_FOLDER_ID")
        self.endpoint = os.getenv(
            "YANDEX_STT_ENDPOINT",
            "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
        )
    
    async def transcribe(self, audio_path: str, api_key: Optional[str] = None, folder_id: Optional[str] = None) -> str:
        """
        Транскрибирует аудио файл в текст
        
        Args:
            audio_path: Путь к аудио файлу
            api_key: Ключ Yandex SpeechKit (опционально, иначе используется значение по умолчанию)
            folder_id: Folder ID Yandex Cloud (опционально)
            
        Returns:
            Полный текст транскрипции
        """
        effective_api_key = api_key or self.default_api_key
        effective_folder_id = folder_id or self.default_folder_id
        
        if not effective_api_key:
            raise ValueError("Yandex SpeechKit API key не передан и не найден в окружении")
        if not effective_folder_id:
            raise ValueError("Yandex Cloud Folder ID не передан и не найден в окружении")
        
        try:
            audio_bytes = Path(audio_path).read_bytes()
            params = {
                "lang": "ru-RU",
                "folderId": effective_folder_id
            }
            headers = {
                "Authorization": f"Api-Key {effective_api_key}",
                "Content-Type": "application/octet-stream"
            }
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self.endpoint,
                    params=params,
                    headers=headers,
                    content=audio_bytes
                )
                response.raise_for_status()
                data = response.json()
            
            if data.get("error_code"):
                raise Exception(f"SpeechKit error {data['error_code']}: {data.get('error_message')}")
            
            result_text = data.get("result", "").strip()
            logger.info(f"Transcription completed for {audio_path}")
            return result_text
            
        except httpx.HTTPStatusError as http_err:
            logger.error(
                "HTTP error during transcription (%s): %s",
                http_err.response.status_code,
                http_err.response.text
            )
            raise Exception(f"HTTP ошибка транскрибации: {http_err.response.text}") from http_err
        except Exception as e:
            logger.error(f"Error transcribing {audio_path}: {str(e)}", exc_info=True)
            raise Exception(f"Ошибка транскрибации: {str(e)}")

