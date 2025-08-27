import os
import re

# --- НАСТРОЙКИ ---
# Папка с результатами диаризации (.rttm файлы)
DIARIZATION_DIR = "../diarization/diarization_results"
# Папка с объединенными транскриптами
RAW_TEXT_DIR = "raw_text"
# Имя объединенного файла транскрипта
MERGED_FILENAME = "_full_transcript.txt"
# Имя файла с применной диаризацией
DIARIZED_FILENAME = "_diarized_transcript.txt"
# Длительность каждого аудио-чанка в минутах
CHUNK_DURATION_MINUTES = 10
# --- КОНЕЦ НАСТРОЕК ---


def parse_rttm_file(rttm_path):
    """
    Парсит RTTM файл и возвращает список сегментов с информацией о спикерах.
    Формат RTTM: SPEAKER file_id channel start_time duration conf1 conf2 speaker_id conf3 conf4
    """
    segments = []
    try:
        with open(rttm_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('SPEAKER'):
                    parts = line.split()
                    if len(parts) >= 8:
                        start_time = float(parts[3])
                        duration = float(parts[4])
                        end_time = start_time + duration
                        speaker_id = parts[7]
                        
                        segments.append({
                            'start': start_time,
                            'end': end_time,
                            'speaker': speaker_id
                        })
        
        # Сортируем сегменты по времени начала
        segments.sort(key=lambda x: x['start'])
        return segments
    
    except FileNotFoundError:
        print(f"Файл диаризации не найден: {rttm_path}")
        return []
    except Exception as e:
        print(f"Ошибка при чтении RTTM файла {rttm_path}: {e}")
        return []


def get_speaker_at_time(segments, time_seconds):
    """
    Определяет, какой спикер говорит в указанное время.
    """
    for segment in segments:
        if segment['start'] <= time_seconds <= segment['end']:
            return segment['speaker']
    return "UNKNOWN_SPEAKER"


def format_seconds_to_hhmmss(seconds):
    """Конвертирует секунды в строку формата HH:MM:SS."""
    hh = seconds // 3600
    mm = (seconds % 3600) // 60
    ss = seconds % 60
    return f"{hh:02}:{mm:02}:{ss:02}"


def apply_diarization_to_transcript(meeting_name):
    """
    Применяет результаты диаризации к объединенному транскрипту.
    """
    print(f"\n--- Применяю диаризацию для: {meeting_name} ---")
    
    # Пути к файлам
    rttm_path = os.path.join(DIARIZATION_DIR, f"{meeting_name}.rttm")
    transcript_path = os.path.join(RAW_TEXT_DIR, meeting_name, MERGED_FILENAME)
    output_path = os.path.join(RAW_TEXT_DIR, meeting_name, DIARIZED_FILENAME)
    
    # Проверяем существование файлов
    if not os.path.exists(rttm_path):
        print(f"Файл диаризации не найден: {rttm_path}")
        return False
    
    if not os.path.exists(transcript_path):
        print(f"Объединенный транскрипт не найден: {transcript_path}")
        print("Сначала выполните скрипт 4-merge_transcripts.py")
        return False
    
    # Парсим результаты диаризации
    segments = parse_rttm_file(rttm_path)
    if not segments:
        print("Не удалось загрузить данные диаризации")
        return False
    
    print(f"Загружено {len(segments)} сегментов диаризации")
    
    # Читаем объединенный транскрипт
    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Ошибка при чтении транскрипта: {e}")
        return False
    
    # Разбиваем транскрипт на части по метаданным
    parts = re.split(r'\n\n--- Конец Части-(\d+), Время: ([\d:]+) - ([\d:]+) ---', content)
    
    # Создаем итоговый текст с информацией о спикерах
    diarized_content = []
    chunk_duration_seconds = CHUNK_DURATION_MINUTES * 60
    
    current_speaker = None
    
    for i in range(0, len(parts), 4):
        if i < len(parts):
            part_text = parts[i].strip()
            if not part_text:
                continue
                
            # Определяем номер части
            if i + 1 < len(parts):
                part_num = int(parts[i + 1]) if parts[i + 1].isdigit() else (i // 4) + 1
            else:
                part_num = (i // 4) + 1
            
            # Вычисляем время начала этой части
            part_start_seconds = (part_num - 1) * chunk_duration_seconds
            part_end_seconds = part_num * chunk_duration_seconds
            
            # Разбиваем текст части на предложения для более точной привязки спикеров
            sentences = re.split(r'[.!?]+', part_text)
            
            part_content = []
            part_content.append(f"\n=== ЧАСТЬ {part_num} ({format_seconds_to_hhmmss(part_start_seconds)} - {format_seconds_to_hhmmss(part_end_seconds)}) ===\n")
            
            for j, sentence in enumerate(sentences):
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                # Примерно определяем время этого предложения внутри части
                sentence_time = part_start_seconds + (j / len(sentences)) * chunk_duration_seconds
                
                # Определяем спикера для этого времени
                speaker = get_speaker_at_time(segments, sentence_time)
                
                # Если спикер изменился, добавляем заголовок
                if speaker != current_speaker:
                    current_speaker = speaker
                    part_content.append(f"\n[{speaker}]: ")
                
                part_content.append(sentence + ". ")
            
            diarized_content.extend(part_content)
            diarized_content.append(f"\n\n--- Конец Части-{part_num} ---\n")
    
    # Сохраняем результат
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(''.join(diarized_content))
        
        print(f"Успешно! Транскрипт с диаризацией сохранен: {output_path}")
        return True
        
    except Exception as e:
        print(f"Ошибка при сохранении файла: {e}")
        return False


def get_available_meetings():
    """
    Находит совещания, для которых есть и объединенный транскрипт, и результаты диаризации.
    """
    meetings = []
    
    # Получаем список папок с транскриптами
    if not os.path.exists(RAW_TEXT_DIR):
        return meetings
    
    for folder_name in os.listdir(RAW_TEXT_DIR):
        folder_path = os.path.join(RAW_TEXT_DIR, folder_name)
        if not os.path.isdir(folder_path):
            continue
        
        # Проверяем наличие объединенного транскрипта
        transcript_path = os.path.join(folder_path, MERGED_FILENAME)
        if not os.path.exists(transcript_path):
            continue
        
        # Проверяем наличие файла диаризации
        rttm_path = os.path.join(DIARIZATION_DIR, f"{folder_name}.rttm")
        if not os.path.exists(rttm_path):
            continue
        
        # Проверяем, есть ли уже файл с диаризацией
        diarized_path = os.path.join(folder_path, DIARIZED_FILENAME)
        already_processed = os.path.exists(diarized_path)
        
        meetings.append((folder_name, already_processed))
    
    return meetings


def main():
    """
    Основная функция для интерактивного выбора совещания и применения диаризации.
    """
    print("=== Применение диаризации к транскриптам ===")
    
    while True:
        meetings = get_available_meetings()
        
        if not meetings:
            print("\nНе найдено совещаний с одновременно доступными транскриптами и результатами диаризации.")
            print("Убедитесь, что:")
            print("1. Выполнен скрипт 4-merge_transcripts.py")
            print("2. Выполнена диаризация (run_diarization.py)")
            break
        
        print(f"\nДоступные совещания для применения диаризации:")
        for i, (meeting_name, already_processed) in enumerate(meetings):
            status = "(уже обработан)" if already_processed else ""
            print(f"{i + 1}. {meeting_name} {status}")
        
        try:
            choice = input("\nВыберите номер совещания (или 'q' для выхода): ")
            if choice.lower() == 'q':
                break
            
            choice_index = int(choice) - 1
            if 0 <= choice_index < len(meetings):
                selected_meeting, already_processed = meetings[choice_index]
                
                if already_processed:
                    confirm = input(f"Файл с диаризацией для '{selected_meeting}' уже существует. Перезаписать? (y/n): ")
                    if confirm.lower() != 'y':
                        continue
                
                success = apply_diarization_to_transcript(selected_meeting)
                if success:
                    print("Диаризация успешно применена!")
                else:
                    print("Произошла ошибка при применении диаризации.")
            else:
                print("Неверный выбор. Пожалуйста, введите действительный номер.")
                
        except ValueError:
            print("Неверный ввод. Пожалуйста, введите номер или 'q'.")


if __name__ == "__main__":
    main()
