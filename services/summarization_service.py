"""
Сервис саммаризации и разделения спикеров через YandexGPT
"""
import os
import logging
from typing import Dict, Optional
import httpx
import json

logger = logging.getLogger(__name__)


class SummarizationService:
    """Сервис для саммаризации и разделения спикеров через YandexGPT API"""
    
    def __init__(
        self,
        default_api_key: Optional[str] = None,
        default_folder_id: Optional[str] = None,
        default_gpt_api_key: Optional[str] = None,
    ):
        # Ключ по умолчанию для SpeechKit/Yandex API (может совпадать с GPT)
        env_api_key = os.getenv("YANDEX_API_KEY")
        self.default_api_key = default_api_key or env_api_key
        self.default_folder_id = default_folder_id or os.getenv("YANDEX_FOLDER_ID")
        self.default_gpt_api_key = default_gpt_api_key or os.getenv("YANDEXGPT_API_KEY") or env_api_key
        
        # Endpoint для YandexGPT
        self.base_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        self.model = "yandexgpt/latest"  # Используем последнюю версию модели
    
    async def summarize_with_speakers(
        self,
        transcription: str,
        api_key: Optional[str] = None,
        folder_id: Optional[str] = None,
        gpt_api_key: Optional[str] = None,
    ) -> Dict:
        """
        Создает саммари и разделяет транскрипт на двух спикеров
        
        Args:
            transcription: Полный текст транскрипции
            api_key: Основной API ключ (используется как fallback для GPT)
            folder_id: Folder ID Yandex Cloud
            gpt_api_key: Ключ для YandexGPT (если отличается от основного)
            
        Returns:
            Словарь с саммари, спикерами и их сегментами
        """
        effective_folder_id = folder_id or self.default_folder_id
        effective_api_key = api_key or self.default_api_key
        effective_gpt_key = gpt_api_key or self.default_gpt_api_key or effective_api_key
        
        if not effective_folder_id:
            raise ValueError("Yandex Cloud Folder ID не передан и не найден в окружении")
        if not effective_gpt_key:
            raise ValueError("YandexGPT API key не передан и не найден в окружении")
        
        try:
            # Промпт для анализа и разделения спикеров
            prompt = self._create_analysis_prompt(transcription)
            
            # Вызов YandexGPT API
            response_text = await self._call_yandexgpt(prompt, effective_folder_id, effective_gpt_key)
            
            # Парсинг ответа
            result = self._parse_response(response_text, transcription)
            
            logger.info("Summarization and speaker separation completed")
            return result
            
        except Exception as e:
            logger.error(f"Error in summarization: {str(e)}", exc_info=True)
            # В случае ошибки возвращаем базовую структуру
            return self._create_fallback_result(transcription)
    
    def _create_analysis_prompt(self, transcription: str) -> str:
        """Создает промпт для анализа транскрипта"""
        return f"""Проанализируй транскрипт встречи двух участников и выполни следующие задачи:

1. Раздели транскрипт на реплики двух спикеров (Спикер 1 и Спикер 2)
2. Определи основную тему встречи
3. Создай краткое общее резюме встречи
4. Выдели ключевые моменты обсуждения
5. Создай краткое резюме для каждого спикера

Транскрипт:
{transcription}

Верни ответ строго в формате JSON со следующей структурой:
{{
    "topic": "основная тема встречи",
    "overall_summary": "краткое общее резюме встречи (2-3 предложения)",
    "key_points": ["ключевой момент 1", "ключевой момент 2", ...],
    "speakers": [
        {{
            "speaker_id": 1,
            "name": "Спикер 1",
            "segments": [
                {{
                    "text": "текст реплики",
                    "order": 1
                }},
                ...
            ],
            "summary": "краткое резюме высказываний спикера 1"
        }},
        {{
            "speaker_id": 2,
            "name": "Спикер 2",
            "segments": [
                {{
                    "text": "текст реплики",
                    "order": 1
                }},
                ...
            ],
            "summary": "краткое резюме высказываний спикера 2"
        }}
    ]
}}

Важно: верни только валидный JSON, без дополнительных комментариев или текста до/после JSON."""
    
    async def _call_yandexgpt(self, prompt: str, folder_id: str, api_key: str) -> str:
        """Вызывает YandexGPT API"""
        headers = {
            "Authorization": f"Api-Key {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "modelUri": f"gpt://{folder_id}/{self.model}",
            "completionOptions": {
                "stream": False,
                "temperature": 0.3,
                "maxTokens": 4000
            },
            "messages": [
                {
                    "role": "user",
                    "text": prompt
                }
            ]
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                self.base_url,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            
            # Извлекаем текст ответа
            if "result" in data and "alternatives" in data["result"]:
                return data["result"]["alternatives"][0]["message"]["text"]
            else:
                raise ValueError(f"Неожиданный формат ответа API: {data}")
    
    def _parse_response(self, response_text: str, original_transcription: str) -> Dict:
        """Парсит ответ от YandexGPT и извлекает JSON"""
        try:
            # Пытаемся найти JSON в ответе
            # Убираем markdown code blocks если есть
            text = response_text.strip()
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            # Парсим JSON
            result = json.loads(text)
            
            # Добавляем длительность (приблизительно, на основе количества символов)
            # Средняя скорость речи ~150 слов/мин, ~10 символов/слово
            estimated_duration = len(original_transcription) / 25  # секунды
            
            return {
                "summary": {
                    "topic": result.get("topic", "Встреча"),
                    "overall_summary": result.get("overall_summary", ""),
                    "key_points": result.get("key_points", [])
                },
                "speakers": result.get("speakers", []),
                "duration": estimated_duration
            }
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}. Response: {response_text[:200]}")
            # Если не удалось распарсить, создаем fallback результат
            return self._create_fallback_result(original_transcription)
    
    def _create_fallback_result(self, transcription: str) -> Dict:
        """Создает базовый результат при ошибке парсинга"""
        # Разделяем транскрипт пополам как простую эвристику
        words = transcription.split()
        mid_point = len(words) // 2
        
        speaker1_text = " ".join(words[:mid_point])
        speaker2_text = " ".join(words[mid_point:])
        
        return {
            "summary": {
                "topic": "Встреча",
                "overall_summary": transcription[:200] + "..." if len(transcription) > 200 else transcription,
                "key_points": []
            },
            "speakers": [
                {
                    "speaker_id": 1,
                    "name": "Спикер 1",
                    "segments": [{"text": speaker1_text, "order": 1}],
                    "summary": speaker1_text[:150] + "..." if len(speaker1_text) > 150 else speaker1_text
                },
                {
                    "speaker_id": 2,
                    "name": "Спикер 2",
                    "segments": [{"text": speaker2_text, "order": 1}],
                    "summary": speaker2_text[:150] + "..." if len(speaker2_text) > 150 else speaker2_text
                }
            ],
            "duration": len(transcription) / 25
        }

