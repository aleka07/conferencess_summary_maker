import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import os
import sys
import time

# --- НАСТРОЙКИ ---
BASE_DATA_DIR = "/data"
CHUNKS_BASE_DIR = os.path.join(BASE_DATA_DIR, "2_audio_chunks")
RAW_TEXT_BASE_DIR = os.path.join(BASE_DATA_DIR, "3_raw_transcripts")
MODEL_ID = "openai/whisper-large-v3"
# --- КОНЕЦ НАСТРОЕК ---

def initialize_pipeline():
    """Инициализирует и возвращает пайплайн для распознавания речи."""
    print("Инициализация... Загрузка модели Whisper. Это может занять несколько минут.")
    try:
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            MODEL_ID, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True
        )
        model.to(device)
        processor = AutoProcessor.from_pretrained(MODEL_ID)
        
        pipe = pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            torch_dtype=torch_dtype,
            device=device,
            batch_size=16,
        )
        print(f"Модель {MODEL_ID} успешно загружена на устройство: {device}")
        return pipe
    except Exception as e:
        print(f"Не удалось загрузить модель или создать пайплайн: {e}", file=sys.stderr)
        sys.exit(1)

def process_meeting_folder(meeting_name, pipe):
    """Транскрибирует все аудио-чанки для указанного совещания."""
    print(f"\n--- Начинаю транскрибацию совещания: {meeting_name} ---")
    chunks_folder_path = os.path.join(CHUNKS_BASE_DIR, meeting_name)
    output_meeting_folder = os.path.join(RAW_TEXT_BASE_DIR, meeting_name)
    
    os.makedirs(output_meeting_folder, exist_ok=True)
    
    if not os.path.exists(chunks_folder_path):
        print(f"Ошибка: Папка с аудио-чанками не найдена: {chunks_folder_path}", file=sys.stderr)
        return

    audio_files = sorted([f for f in os.listdir(chunks_folder_path) if f.lower().endswith(('.mp3', '.wav'))])
    
    total_files = len(audio_files)
    if total_files == 0:
        print("В папке не найдено аудиофайлов для обработки.")
        return

    for i, filename in enumerate(audio_files):
        print(f"\nОбрабатываю чанк {i+1}/{total_files}: {filename}")
        file_path = os.path.join(chunks_folder_path, filename)
        
        try:
            start_time = time.time()
            result = pipe(
                file_path, 
                generate_kwargs={"language": "russian"}, 
                return_timestamps=True
            )
            processing_time = time.time() - start_time
            print(f"Транскрибация чанка завершена за {processing_time:.2f} секунд.")

            output_filepath = os.path.join(output_meeting_folder, os.path.splitext(filename)[0] + '.txt')
            with open(output_filepath, 'w', encoding='utf-8') as f:
                if result and "chunks" in result:
                    for chunk in result["chunks"]:
                        start_ts = chunk.get('timestamp', [None, None])[0]
                        text = chunk.get('text', '').strip()
                        if text and start_ts is not None:
                            f.write(f"[{start_ts:07.2f}] {text}\n") # Форматирование с ведущими нулями
                else:
                    f.write(result.get("text", "Не удалось извлечь текст."))
            print(f"Результат сохранен в: {output_filepath}")
        except Exception as e:
            print(f"!!! Критическая ошибка при обработке файла {filename}: {e}", file=sys.stderr)
            continue
            
    print(f"\n--- Обработка совещания {meeting_name} завершена! ---")

def main():
    if len(sys.argv) != 2:
        print("Использование: python3 3_transcribe_local_batch.py <имя_совещания>", file=sys.stderr)
        sys.exit(1)
    
    meeting_name = sys.argv[1]
    
    # Инициализация модели происходит один раз
    transcription_pipeline = initialize_pipeline()
    
    process_meeting_folder(meeting_name, transcription_pipeline)

if __name__ == "__main__":
    main()