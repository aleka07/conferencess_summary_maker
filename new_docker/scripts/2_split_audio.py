import os
import sys
import subprocess
import math

# --- НАСТРОЙКИ ---
BASE_DATA_DIR = "/data"
CHUNKS_OUTPUT_DIR = os.path.join(BASE_DATA_DIR, "2_audio_chunks")
CHUNK_DURATION_MINUTES = 10
OVERLAP_SECONDS = 10 
# --- КОНЕЦ НАСТРОЕК ---

def get_file_duration(file_path):
    """Получает длительность медиафайла в секундах с помощью ffprobe."""
    try:
        command = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", file_path
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return float(result.stdout)
    except (subprocess.CalledProcessError, ValueError) as e:
        print(f"Ошибка при получении длительности файла {file_path}: {e}", file=sys.stderr)
        return None
    except FileNotFoundError:
        print("Ошибка: ffprobe не найден. Он должен быть установлен в Docker-контейнере.", file=sys.stderr)
        return None

def split_audio_into_chunks(input_audio_path, meeting_name):
    """Разделяет аудиофайл на чанки."""
    print(f"\nРазделение '{input_audio_path}' на фрагменты для совещания '{meeting_name}'...")
    duration = get_file_duration(input_audio_path)
    if duration is None:
        sys.exit(1)

    output_chunk_dir = os.path.join(CHUNKS_OUTPUT_DIR, meeting_name)
    os.makedirs(output_chunk_dir, exist_ok=True)

    chunk_duration_seconds = CHUNK_DURATION_MINUTES * 60
    effective_chunk_duration = chunk_duration_seconds - OVERLAP_SECONDS
    
    if effective_chunk_duration <= 0:
        print("Ошибка: Длительность чанка должна быть больше длительности перекрытия.", file=sys.stderr)
        sys.exit(1)
        
    num_chunks = math.ceil(duration / effective_chunk_duration) if duration > 0 else 0
    if num_chunks == 0 and duration > 0:
        num_chunks = 1

    print(f"Длительность аудио: {duration:.2f}s. Будет создано {num_chunks} фрагментов.")

    for i in range(num_chunks):
        start_time = i * effective_chunk_duration
        current_chunk_duration = chunk_duration_seconds
        
        if start_time + current_chunk_duration > duration:
            current_chunk_duration = duration - start_time
        
        if current_chunk_duration <= 0:
            continue

        output_chunk_path = os.path.join(output_chunk_dir, f"{meeting_name}_part{i+1:03d}.mp3")
        
        print(f"  Создание фрагмента {i+1}/{num_chunks}: {output_chunk_path} (начало: {start_time:.2f}s)")
        try:
            cmd = [
                "ffmpeg", "-y", "-i", input_audio_path,
                "-ss", str(start_time), "-t", str(current_chunk_duration),
                "-c:a", "libmp3lame", "-b:a", "192k", # Всегда перекодируем для унификации
                output_chunk_path
            ]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"Ошибка при создании фрагмента {i+1}: {e}", file=sys.stderr)
            print(f"Вывод FFmpeg (stderr):\n{e.stderr}", file=sys.stderr)
            sys.exit(1)
            
    print(f"Разделение '{meeting_name}' завершено.")

def main():
    if len(sys.argv) != 3:
        print("Использование: python3 2_split_audio.py <путь_к_входному_аудио> <имя_совещания>", file=sys.stderr)
        sys.exit(1)
        
    input_audio_path = sys.argv[1]
    meeting_name = sys.argv[2]
    
    if not os.path.exists(input_audio_path):
        print(f"Ошибка: Входной аудиофайл не найден: {input_audio_path}", file=sys.stderr)
        sys.exit(1)
        
    split_audio_into_chunks(input_audio_path, meeting_name)

if __name__ == "__main__":
    main()