"""
Сервис для обработки и конвертации аудио/видео файлов
"""
import os
import logging
from pathlib import Path
from typing import Optional
import asyncio
from moviepy.editor import VideoFileClip
from pydub import AudioSegment

logger = logging.getLogger(__name__)


class AudioProcessor:
    """Обработчик аудио файлов для конвертации в формат для SpeechKit"""
    
    def __init__(self):
        self.temp_dir = Path("uploads")
        self.temp_dir.mkdir(exist_ok=True)
    
    async def process_file(self, file_path: str) -> str:
        """
        Конвертирует файл в формат, поддерживаемый Yandex SpeechKit
        SpeechKit поддерживает: LPCM, OggOpus, MP3
        
        Args:
            file_path: Путь к исходному файлу
            
        Returns:
            Путь к конвертированному аудио файлу
        """
        file_path_obj = Path(file_path)
        file_ext = file_path_obj.suffix.lower()
        
        # Если файл уже в поддерживаемом формате (MP3, WAV), можно использовать как есть
        # Но лучше конвертировать в OggOpus для оптимального качества/размера
        output_path = self.temp_dir / f"{file_path_obj.stem}_processed.ogg"
        
        try:
            # Запускаем конвертацию в отдельном потоке
            await asyncio.to_thread(self._convert_file, file_path, str(output_path), file_ext)
            
            logger.info(f"File converted: {file_path} -> {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error converting file {file_path}: {str(e)}", exc_info=True)
            raise Exception(f"Ошибка конвертации файла: {str(e)}")
    
    def _convert_file(self, input_path: str, output_path: str, input_ext: str):
        """Синхронная конвертация файла"""
        if input_ext in ['.mp3', '.wav', '.ogg']:
            # Аудио файл - используем pydub
            audio = AudioSegment.from_file(input_path)
            # Конвертируем в OggOpus (поддерживается SpeechKit)
            audio.export(output_path, format="ogg", codec="libopus", parameters=["-b:a", "64k"])
        elif input_ext == '.mp4':
            # Видео файл - извлекаем аудио через moviepy
            video = VideoFileClip(input_path)
            # Конвертируем в OggOpus
            video.audio.write_audiofile(
                output_path,
                codec='libopus',
                bitrate='64k',
                verbose=False,
                logger=None
            )
            video.close()
        else:
            raise ValueError(f"Неподдерживаемый формат файла: {input_ext}")
    
    def cleanup(self, file_path: str):
        """Удаление временного файла"""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.info(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.warning(f"Error cleaning up file {file_path}: {str(e)}")






