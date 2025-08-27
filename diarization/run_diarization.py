import os
import torch
from pyannote.audio import Pipeline
from dotenv import load_dotenv
import time

# --- НАСТРОЙКИ ---
# Директория с аудиофайлами для обработки
SOURCE_AUDIO_DIR = "audio_for_diarization"
# Директория для сохранения результатов в формате RTTM
RESULTS_DIR = "diarization_results"
# ID модели на Hugging Face
MODEL_ID = "pyannote/speaker-diarization-3.1"
# --- КОНЕЦ НАСТРОЕК ---


def diarize_audio_files():
    """
    Основная функция для запуска процесса диаризации спикеров
    на всех аудиофайлах в указанной директории.
    """
    # --- 1. ЗАГРУЗКА ТОКЕНА И ИНИЦИАЛИЗАЦИЯ МОДЕЛИ ---

    # Загружаем переменные окружения из файла .env
    # Это безопасный способ хранить ваш токен
    load_dotenv()
    hf_token = os.getenv("HUGGINGFACE_TOKEN")

    if not hf_token:
        print("Ошибка: Токен Hugging Face не найден.")
        print("Пожалуйста, создайте файл .env в той же папке, что и скрипт,")
        print("и добавьте в него строку: HUGGINGFACE_TOKEN='ваш_токен_доступа'")
        return

    print("Инициализация... Загрузка модели диаризации. Это может занять некоторое время.")
    try:
        # Загружаем предобученный конвейер (pipeline) с использованием токена
        pipeline = Pipeline.from_pretrained(
            MODEL_ID,
            use_auth_token=hf_token
        )

        # Перемещаем модель на GPU, если он доступен, для ускорения обработки
        if torch.cuda.is_available():
            device = torch.device("cuda")
            pipeline.to(device)
            print(f"Модель {MODEL_ID} успешно загружена на GPU.")
        else:
            device = torch.device("cpu")
            print(f"Модель {MODEL_ID} успешно загружена на CPU. Обработка будет медленнее.")

    except Exception as e:
        print(f"Не удалось загрузить модель: {e}")
        print("Убедитесь, что вы приняли условия использования моделей на Hugging Face и ваш токен действителен.")
        return


    # --- 2. ПОИСК И ОБРАБОТКА АУДИОФАЙЛОВ ---

    # Создаем папку для результатов, если она не существует
    os.makedirs(RESULTS_DIR, exist_ok=True)

    # Ищем все поддерживаемые аудиофайлы в исходной директории
    supported_formats = ('.wav', '.mp3', '.flac', '.m4a')
    audio_files = [f for f in os.listdir(SOURCE_AUDIO_DIR) if f.endswith(supported_formats)]

    if not audio_files:
        print(f"В папке '{SOURCE_AUDIO_DIR}' не найдено аудиофайлов для обработки.")
        return

    print(f"\nНайдено {len(audio_files)} аудиофайлов. Начинаю обработку...")

    for i, filename in enumerate(audio_files):
        print(f"\n--- ({i+1}/{len(audio_files)}) Обрабатываю файл: {filename} ---")
        file_path = os.path.join(SOURCE_AUDIO_DIR, filename)
        
        try:
            start_time = time.time()
            
            # Запускаем конвейер диаризации на аудиофайле
            # Модель автоматически обработает аудио: сконвертирует в моно, 16кГц
            diarization = pipeline(file_path)
            
            end_time = time.time()
            print(f"Диаризация файла завершена за {end_time - start_time:.2f} секунд.")

            # --- 3. СОХРАНЕНИЕ РЕЗУЛЬТАТОВ ---

            # Формируем путь для сохранения RTTM файла
            output_rttm_path = os.path.join(RESULTS_DIR, os.path.splitext(filename)[0] + '.rttm')
            
            # Записываем результат в файл формата RTTM
            with open(output_rttm_path, "w") as rttm_file:
                diarization.write_rttm(rttm_file)
            
            print(f"Результат сохранен в: {output_rttm_path}")

            # Опционально: выводим результат в консоль для наглядности
            print("Разметка спикеров:")
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                print(f"[{turn.start:04.1f}s -> {turn.end:04.1f}s] SPEAKER_{speaker}")


        except Exception as e:
            print(f"!!! Произошла ошибка при обработке файла {filename}: {e}")
            print("!!! Пропускаю этот файл и перехожу к следующему.")
            continue
            
    print(f"\n--- Обработка всех файлов завершена! ---")


if __name__ == "__main__":
    # Для безопасного хранения токена рекомендуется установить python-dotenv
    try:
        import dotenv
    except ImportError:
        print("Внимание: библиотека python-dotenv не установлена.")
        print("Рекомендуется установить ее ('pip install python-dotenv') для безопасного хранения токена.")

    dotenv.load_dotenv()
    diarize_audio_files()