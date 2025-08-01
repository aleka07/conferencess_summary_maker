import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import os
import time

# --- НАСТРОЙКА ---
# 1. Укажите путь к вашему 50-минутному аудиофайлу
audio_file_path = "chunks/23-07/23-07_part001.mp3" # <-- ЗАМЕНИТЕ ЭТОТ ПУТЬ

# --- Проверка существования файла ---
if not os.path.exists(audio_file_path):
    print(f"Ошибка: Файл не найден по пути: {audio_file_path}")
    print("Пожалуйста, убедитесь, что вы указали правильный путь к вашему аудиофайлу.")
else:
    # --- ЗАГРУЗКА МОДЕЛИ ---
    print("Загрузка модели Whisper... Это может занять несколько минут.")
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    model_id = "openai/whisper-large-v3"

    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True
    )
    model.to(device)

    processor = AutoProcessor.from_pretrained(model_id)

    # --- СОЗДАНИЕ КОНВЕЙЕРА С ПОСЛЕДОВАТЕЛЬНЫМ МЕТОДОМ ---
    # Мы убрали 'chunk_length_s', чтобы активировать метод "Sequential" (по умолчанию)
    pipe = pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        torch_dtype=torch_dtype,
        device=device,
        # batch_size здесь будет применяться, только если вы передадите НЕСКОЛЬКО ФАЙЛОВ
        # Для одного длинного файла он не ускорит процесс
        batch_size=16,
        return_timestamps=True,
    )

    print(f"Транскрибирую файл (метод Sequential): {audio_file_path}")
    print("!!! Этот метод ставит точность выше скорости. ПРОЦЕСС ЗАЙМЕТ ЗНАЧИТЕЛЬНОЕ ВРЕМЯ !!!")
    start_time = time.time()

    # --- ТРАНСКРИБАЦИЯ ВАШЕГО ФАЙЛА ---
    result = pipe(audio_file_path, generate_kwargs={"language": "russian"}, 
                  return_timestamps=True)

    end_time = time.time()
    processing_time = end_time - start_time
    print(f"Транскрибация завершена за {processing_time:.2f} секунд.")

    # --- ВЫВОД РЕЗУЛЬТАТА С ВРЕМЕННЫМИ МЕТКАМИ ---
    print("\n--- Результат транскрибации ---\n")
    if result and "chunks" in result:
        for chunk in result["chunks"]:
            start_ts = chunk.get('timestamp', [None, None])[0]
            end_ts = chunk.get('timestamp', [None, None])[1]
            text = chunk.get('text', '')
            # Добавим проверку, чтобы не выводить пустые значения
            if start_ts is not None and end_ts is not None:
                print(f"[{start_ts:.2f} -> {end_ts:.2f}] {text}")
            else:
                print(text)

    # Опционально: сохранить весь текст в файл
    full_text = result["text"]
    with open("transcription_output_sequential.txt", "w", encoding="utf-8") as f:
        f.write(full_text)
    print("\nПолный текст также сохранен в файл 'transcription_output_sequential.txt'")