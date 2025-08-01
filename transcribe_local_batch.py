import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import os
import time
import shutil

# --- НАСТРОЙКИ ---
# Базовые директории для работы
CHUNKS_BASE_DIR = "chunks"
RAW_TEXT_BASE_DIR = "raw_text"
# ID модели Whisper для транскрибации
MODEL_ID = "openai/whisper-large-v3"
# --- КОНЕЦ НАСТРОЕК ---


def get_meeting_folders(directory):
    """Находит папки совещаний в директории с чанками."""
    folders = []
    if not os.path.exists(directory):
        print(f"Внимание: Базовая папка '{directory}' не найдена.")
        return folders
    for item in os.listdir(directory):
        if os.path.isdir(os.path.join(directory, item)):
            folders.append(item)
    return sorted(folders)

def get_transcription_status(meeting_name):
    """Проверяет статус транскрибации для данного совещания."""
    chunks_dir = os.path.join(CHUNKS_BASE_DIR, meeting_name)
    raw_text_dir = os.path.join(RAW_TEXT_BASE_DIR, meeting_name)

    if not os.path.exists(chunks_dir):
        return "Ошибка: папка с чанками не найдена"

    try:
        num_mp3 = len([f for f in os.listdir(chunks_dir) if f.endswith(('.mp3', '.wav', '.flac', '.m4a'))])
    except FileNotFoundError:
        return "Ошибка: папка с чанками не найдена"
    
    if num_mp3 == 0:
        return "Нет аудио-чанков"

    if not os.path.exists(raw_text_dir):
        return "Не начато"

    num_txt = len([f for f in os.listdir(raw_text_dir) if f.endswith('.txt')])

    if num_txt == 0:
        return "Не начато"
    elif num_txt < num_mp3:
        return f"Частично готово ({num_txt}/{num_mp3})"
    elif num_txt == num_mp3:
        return "Готово"
    else:
        return f"Ошибка: текстовых файлов больше, чем аудио ({num_txt}/{num_mp3})"

def process_meeting_folder(meeting_name, pipe, force_rerun=False):
    """
    Основная функция обработки папки с чанками одного совещания
    с использованием локальной модели Whisper.
    """
    print(f"\n--- Начинаю обработку совещания: {meeting_name} ---")
    chunks_folder_path = os.path.join(CHUNKS_BASE_DIR, meeting_name)
    output_meeting_folder = os.path.join(RAW_TEXT_BASE_DIR, meeting_name)

    if force_rerun and os.path.exists(output_meeting_folder):
        print(f"Удаляю предыдущие результаты из: {output_meeting_folder}")
        shutil.rmtree(output_meeting_folder)
    
    os.makedirs(output_meeting_folder, exist_ok=True)
    print(f"Результаты будут сохранены в: {output_meeting_folder}")

    # Ищем аудиофайлы с разными расширениями
    audio_files = sorted([f for f in os.listdir(chunks_folder_path) if f.endswith(('.mp3', '.wav', '.flac', '.m4a'))])
    
    total_files = len(audio_files)
    if total_files == 0:
        print("В папке не найдено аудиофайлов для обработки.")
        return

    for i, filename in enumerate(audio_files):
        print(f"\nОбрабатываю чанк {i+1}/{total_files}: {filename}")
        file_path = os.path.join(chunks_folder_path, filename)
        
        # Проверка существования файла перед обработкой
        if not os.path.exists(file_path):
            print(f"Ошибка: Файл не найден по пути: {file_path}")
            continue

        try:
            start_time = time.time()
            
            # --- ТРАНСКРИБАЦИЯ ФАЙЛА ---
            # Используем пайплайн, переданный в функцию
            result = pipe(
                file_path, 
                generate_kwargs={"language": "russian"}, 
                return_timestamps=True
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            print(f"Транскрибация чанка завершена за {processing_time:.2f} секунд.")

            # --- ФОРМАТИРОВАНИЕ И СОХРАНЕНИЕ РЕЗУЛЬТАТА С ВРЕМЕННЫМИ МЕТКАМИ ---
            output_filepath = os.path.join(output_meeting_folder, os.path.splitext(filename)[0] + '.txt')
            
            with open(output_filepath, 'w', encoding='utf-8') as f:
                if result and "chunks" in result:
                    for chunk in result["chunks"]:
                        start_ts = chunk.get('timestamp', [None, None])[0]
                        end_ts = chunk.get('timestamp', [None, None])[1]
                        text = chunk.get('text', '').strip()
                        
                        # Записываем только если есть текст
                        if text and start_ts is not None and end_ts is not None:
                            f.write(f"[{start_ts:.2f} -> {end_ts:.2f}] {text}\n")
                else:
                    # На случай, если результат пустой или в неожиданном формате
                    f.write(result.get("text", "Не удалось извлечь текст."))

            print(f"Результат с временными метками сохранен в: {output_filepath}")

        except Exception as e:
            print(f"!!! Произошла критическая ошибка при обработке файла {filename}: {e}")
            print("!!! Пропускаю этот чанк и перехожу к следующему.")
            continue
            
    print(f"\n--- Обработка совещания {meeting_name} завершена! ---")


def main():
    """
    Главная функция: загружает модель и запускает интерактивное меню
    для выбора папок и управления процессом транскрибации.
    """
    # --- ЗАГРУЗКА МОДЕЛИ И ПАЙПЛАЙНА (выполняется один раз) ---
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
            batch_size=16, # Ускоряет обработку, если передавать несколько файлов сразу, но мы обрабатываем по одному
        )
        print(f"Модель {MODEL_ID} успешно загружена на устройство: {device}")
    except Exception as e:
        print(f"Не удалось загрузить модель или создать пайплайн: {e}")
        print("Проверьте интернет-соединение, имя модели и установленные библиотеки.")
        return

    # --- ГЛАВНЫЙ ЦИКЛ РАБОТЫ С ПОЛЬЗОВАТЕЛЕМ ---
    os.makedirs(RAW_TEXT_BASE_DIR, exist_ok=True)
    
    while True:
        meeting_folders = get_meeting_folders(CHUNKS_BASE_DIR)

        if not meeting_folders:
            print(f"\nВ папке '{CHUNKS_BASE_DIR}' не найдено папок с аудио-чанками.")
            print("Создайте подпапку в 'chunks' и поместите туда аудиофайлы для начала работы.")
            break

        print("\nДоступные совещания для локальной транскрибации:")
        meetings_to_process = []
        for i, folder_name in enumerate(meeting_folders):
            status = get_transcription_status(folder_name)
            print(f"{i + 1}. {folder_name} - Статус: {status}")
            meetings_to_process.append((folder_name, status))
        
        try:
            choice = input("\nВыберите номер совещания для транскрибации (или 'q' для выхода): ")
            if choice.lower() == 'q':
                print("Выход из программы.")
                break
            
            choice_index = int(choice) - 1
            if 0 <= choice_index < len(meetings_to_process):
                selected_meeting, status = meetings_to_process[choice_index]
                
                force_rerun = False
                if status not in ["Не начато", "Нет аудио-чанков", "Ошибка: папка с чанками не найдена"]:
                    confirm = input(f"Транскрипция для '{selected_meeting}' уже существует или начата. Хотите запустить заново и перезаписать все файлы? (y/n): ")
                    if confirm.lower() != 'y':
                        print("Операция отменена. Выберите другое совещание.")
                        continue
                    force_rerun = True
                
                # Запуск обработки выбранной папки
                process_meeting_folder(selected_meeting, pipe, force_rerun=force_rerun)

            else:
                print("Неверный выбор. Пожалуйста, введите действительный номер из списка.")
        except ValueError:
            print("Неверный ввод. Пожалуйста, введите номер или 'q'.")
        except Exception as e:
            print(f"Произошла непредвиденная ошибка в главном цикле: {e}")

if __name__ == "__main__":
    main()