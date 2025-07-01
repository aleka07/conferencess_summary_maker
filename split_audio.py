import os
import subprocess
import math

AUDIO_INPUT_DIR = "audio-from-input"
CHUNKS_OUTPUT_DIR = "chunks"
CHUNK_DURATION_MINUTES = 10
OVERLAP_SECONDS = 2 # Небольшое перекрытие для плавного перехода

def check_ffmpeg_and_ffprobe():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        subprocess.run(["ffprobe", "-version"], capture_output=True, check=True)
        print("ffmpeg и ffprobe установлены.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Ошибка: ffmpeg или ffprobe не найдены. Пожалуйста, установите их для продолжения.")
        return False

def get_audio_files(directory):
    audio_files = []
    if not os.path.exists(directory):
        return audio_files
    for filename in os.listdir(directory):
        if filename.endswith(".mp3"):
            audio_files.append(filename)
    return sorted(audio_files)

def get_file_duration(file_path):
    try:
        result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path], capture_output=True, text=True, check=True)
        return float(result.stdout)
    except (subprocess.CalledProcessError, ValueError) as e:
        print(f"Ошибка при получении длительности файла {file_path}: {e}")
        return None

def has_chunks_been_created(audio_filename):
    base_name = os.path.splitext(audio_filename)[0]
    chunk_dir = os.path.join(CHUNKS_OUTPUT_DIR, base_name)
    if os.path.exists(chunk_dir) and os.listdir(chunk_dir):
        return True
    return False

def split_audio_into_chunks(input_file_path, output_base_dir, audio_filename):
    print(f"\nРазделение '{audio_filename}' на фрагменты...")
    duration = get_file_duration(input_file_path)
    if duration is None:
        return

    base_name = os.path.splitext(audio_filename)[0]
    output_chunk_dir = os.path.join(output_base_dir, base_name)
    os.makedirs(output_chunk_dir, exist_ok=True)

    chunk_duration_seconds = CHUNK_DURATION_MINUTES * 60
    num_chunks = math.ceil(duration / chunk_duration_seconds)

    for i in range(num_chunks):
        start_time = i * chunk_duration_seconds
        current_chunk_duration = chunk_duration_seconds

        # Применяем перекрытие
        if i > 0:
            start_time = max(0, start_time - OVERLAP_SECONDS)
            current_chunk_duration += OVERLAP_SECONDS
        
        # Убедимся, что последний фрагмент не выходит за пределы файла
        if start_time + current_chunk_duration > duration:
            current_chunk_duration = duration - start_time

        output_chunk_path = os.path.join(output_chunk_dir, f"{base_name}_part{i+1:03d}.mp3")
        
        print(f"  Создание фрагмента {i+1}/{num_chunks}: {output_chunk_path} (начало: {start_time:.2f}s, длительность: {current_chunk_duration:.2f}s)")
        try:
            subprocess.run(["ffmpeg", "-i", input_file_path, "-ss", str(start_time), "-t", str(current_chunk_duration), "-c", "copy", output_chunk_path], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Ошибка при создании фрагмента {i+1}: {e}")
            # Можно добавить логику для удаления неполного файла, если нужно
            if os.path.exists(output_chunk_path):
                os.remove(output_chunk_path)
            break # Прекращаем, если один фрагмент не удалось создать
    print(f"Разделение '{audio_filename}' завершено.")

def main():
    if not check_ffmpeg_and_ffprobe():
        return

    os.makedirs(CHUNKS_OUTPUT_DIR, exist_ok=True)

    audio_files = get_audio_files(AUDIO_INPUT_DIR)

    if not audio_files:
        print(f"В папке '{AUDIO_INPUT_DIR}' не найдено файлов .mp3.")
        return

    print("\nДоступные .mp3 файлы для разделения:")
    files_to_process = []
    for i, audio_file in enumerate(audio_files):
        chunks_exist = has_chunks_been_created(audio_file)
        status = " (фрагменты уже созданы)" if chunks_exist else ""
        print(f"{i + 1}. {audio_file}{status}")
        files_to_process.append((audio_file, chunks_exist))

    while True:
        try:
            choice = input("\nВыберите номер файла для разделения на фрагменты (или 'q' для выхода): ")
            if choice.lower() == 'q':
                break
            
            choice_index = int(choice) - 1
            if 0 <= choice_index < len(files_to_process):
                selected_audio_file, chunks_exist = files_to_process[choice_index]
                
                if chunks_exist:
                    confirm = input(f"Для '{selected_audio_file}' фрагменты уже созданы. Хотите создать их снова? (y/n): ")
                    if confirm.lower() != 'y':
                        continue

                input_path = os.path.join(AUDIO_INPUT_DIR, selected_audio_file)
                split_audio_into_chunks(input_path, CHUNKS_OUTPUT_DIR, selected_audio_file)
                
                # Обновить статус после успешного создания фрагментов
                files_to_process[choice_index] = (selected_audio_file, True)
                print("\nОбновленный список .mp3 файлов:")
                for i, (audio_file, extracted) in enumerate(files_to_process):
                    status = " (фрагменты уже созданы)" if extracted else ""
                    print(f"{i + 1}. {audio_file}{status}")

            else:
                print("Неверный выбор. Пожалуйста, введите действительный номер.")
        except ValueError:
            print("Неверный ввод. Пожалуйста, введите номер или 'q'.")

if __name__ == "__main__":
    main()
