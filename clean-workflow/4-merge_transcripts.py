import os

# --- НАСТРОЙКИ ---
# Папка, где лежат папки с текстовыми файлами транскрипций
RAW_TEXT_BASE_DIR = "raw_text"

# Имя, которое будет дано итоговому объединенному файлу
MERGED_FILENAME = "_full_transcript.txt"

# Длительность каждого аудио-чанка в минутах.
CHUNK_DURATION_MINUTES = 10
# --- КОНЕЦ НАСТРОЕК ---


def get_meeting_folders(directory):
    """Находит папки совещаний в директории с результатами транскрибации."""
    folders = []
    if not os.path.exists(directory):
        print(f"Ошибка: Базовая папка '{directory}' не найдена.")
        return folders
    for item in os.listdir(directory):
        if os.path.isdir(os.path.join(directory, item)):
            folders.append(item)
    return sorted(folders)

def has_merged_file(meeting_folder_path):
    """Проверяет, существует ли уже объединенный файл."""
    return os.path.exists(os.path.join(meeting_folder_path, MERGED_FILENAME))

def format_seconds_to_hhmmss(seconds):
    """Конвертирует секунды в строку формата HH:MM:SS."""
    hh = seconds // 3600
    mm = (seconds % 3600) // 60
    ss = seconds % 60
    return f"{hh:02}:{mm:02}:{ss:02}"

def merge_text_files_for_meeting(meeting_name):
    """
    Собирает все .txt файлы из папки совещания в один итоговый файл,
    добавляя метаданные после каждого фрагмента.
    """
    meeting_folder_path = os.path.join(RAW_TEXT_BASE_DIR, meeting_name)
    output_file_path = os.path.join(meeting_folder_path, MERGED_FILENAME)

    print(f"\n--- Начинаю сборку транскрипции для: {meeting_name} ---")

    try:
        txt_files = [f for f in os.listdir(meeting_folder_path) if f.endswith('.txt') and f != MERGED_FILENAME]
        txt_files.sort()
    except FileNotFoundError:
        print(f"Ошибка: Папка {meeting_folder_path} не найдена.")
        return

    if not txt_files:
        print("В папке не найдено .txt файлов для объединения.")
        return

    print(f"Найдено {len(txt_files)} файлов для объединения.")
    
    chunk_duration_seconds = CHUNK_DURATION_MINUTES * 60

    try:
        with open(output_file_path, 'w', encoding='utf-8') as outfile:
            for i, filename in enumerate(txt_files):
                file_path = os.path.join(meeting_folder_path, filename)
                
                with open(file_path, 'r', encoding='utf-8') as infile:
                    content = infile.read().strip() # .strip() убирает лишние пустые строки в конце
                    outfile.write(content)
                
                # Вычисляем и добавляем метаданные
                part_num = i + 1
                start_seconds = i * chunk_duration_seconds
                end_seconds = part_num * chunk_duration_seconds
                
                start_time_str = format_seconds_to_hhmmss(start_seconds)
                end_time_str = format_seconds_to_hhmmss(end_seconds)

                metadata_line = f"\n\n--- Конец Части-{part_num}, Время: {start_time_str} - {end_time_str} ---"
                outfile.write(metadata_line)
                
                # Добавляем пустые строки для разделения перед следующей частью
                if i < len(txt_files) - 1:
                    outfile.write("\n\n")
        
        print(f"Успешно! Все части собраны в один файл: {output_file_path}")

    except Exception as e:
        print(f"Произошла ошибка во время сборки файлов: {e}")


def main():
    while True:
        meeting_folders = get_meeting_folders(RAW_TEXT_BASE_DIR)

        if not meeting_folders:
            break

        print("\nДоступные транскрипции для сборки в один файл:")
        meetings_to_process = []
        for i, folder_name in enumerate(meeting_folders):
            meeting_path = os.path.join(RAW_TEXT_BASE_DIR, folder_name)
            status = "(уже собран)" if has_merged_file(meeting_path) else ""
            print(f"{i + 1}. {folder_name} {status}")
            meetings_to_process.append((folder_name, has_merged_file(meeting_path)))
        
        try:
            choice = input("\nВыберите номер совещания для сборки (или 'q' для выхода): ")
            if choice.lower() == 'q':
                break
            
            choice_index = int(choice) - 1
            if 0 <= choice_index < len(meetings_to_process):
                selected_meeting, already_merged = meetings_to_process[choice_index]
                
                if already_merged:
                    confirm = input(f"Итоговый файл для '{selected_meeting}' уже существует. Хотите создать его заново? (y/n): ")
                    if confirm.lower() != 'y':
                        continue
                
                merge_text_files_for_meeting(selected_meeting)

            else:
                print("Неверный выбор. Пожалуйста, введите действительный номер.")
        except ValueError:
            print("Неверный ввод. Пожалуйста, введите номер или 'q'.")

if __name__ == "__main__":
    main()