import os
import sys

# --- НАСТРОЙКИ ---
BASE_DATA_DIR = "/data"
RAW_TEXT_BASE_DIR = os.path.join(BASE_DATA_DIR, "3_raw_transcripts")
# Новая папка для итоговых транскрипций
MERGED_OUTPUT_DIR = os.path.join(BASE_DATA_DIR, "4_full_transcripts")
MERGED_FILENAME_TEMPLATE = "{meeting_name}_full_transcript.txt"
CHUNK_DURATION_MINUTES = 10
# --- КОНЕЦ НАСТРОЕК ---

def format_seconds_to_hhmmss(seconds):
    """Конвертирует секунды в строку формата HH:MM:SS."""
    seconds = int(seconds)
    hh = seconds // 3600
    mm = (seconds % 3600) // 60
    ss = seconds % 60
    return f"{hh:02}:{mm:02}:{ss:02}"

def merge_text_files_for_meeting(meeting_name):
    """Собирает все .txt файлы из папки совещания в один итоговый файл."""
    meeting_folder_path = os.path.join(RAW_TEXT_BASE_DIR, meeting_name)
    os.makedirs(MERGED_OUTPUT_DIR, exist_ok=True)
    output_file_path = os.path.join(MERGED_OUTPUT_DIR, MERGED_FILENAME_TEMPLATE.format(meeting_name=meeting_name))

    print(f"\n--- Начинаю сборку транскрипции для: {meeting_name} ---")

    if not os.path.exists(meeting_folder_path):
        print(f"Ошибка: Папка с сырыми транскрипциями не найдена: {meeting_folder_path}", file=sys.stderr)
        sys.exit(1)

    try:
        txt_files = sorted([f for f in os.listdir(meeting_folder_path) if f.endswith('.txt')])
    except FileNotFoundError:
        print(f"Ошибка: Папка {meeting_folder_path} не найдена.", file=sys.stderr)
        return

    if not txt_files:
        print("В папке не найдено .txt файлов для объединения.")
        return

    print(f"Найдено {len(txt_files)} файлов для объединения.")
    
    chunk_duration_seconds = CHUNK_DURATION_MINUTES * 60

    with open(output_file_path, 'w', encoding='utf-8') as outfile:
        # Сначала просто объединяем все содержимое
        full_content = []
        for filename in txt_files:
            file_path = os.path.join(meeting_folder_path, filename)
            with open(file_path, 'r', encoding='utf-8') as infile:
                full_content.append(infile.read())
        
        # Записываем все одним махом, разделяя переносом строки
        outfile.write("\n".join(full_content))

    print(f"Успешно! Все части собраны в один файл: {output_file_path}")

def main():
    if len(sys.argv) != 2:
        print("Использование: python3 4_merge_transcripts.py <имя_совещания>", file=sys.stderr)
        sys.exit(1)
        
    meeting_name = sys.argv[1]
    merge_text_files_for_meeting(meeting_name)

if __name__ == "__main__":
    main()