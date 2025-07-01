import os
import subprocess

INPUT_DIR = "input"
OUTPUT_DIR = "audio-from-input"

def check_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        print("ffmpeg установлен.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Ошибка: ffmpeg не найден. Пожалуйста, установите ffmpeg для продолжения.")
        return False

def get_webm_files(directory):
    webm_files = []
    if not os.path.exists(directory):
        return webm_files
    for filename in os.listdir(directory):
        if filename.endswith(".webm"):
            webm_files.append(filename)
    return sorted(webm_files)

def get_extracted_audio_files(directory):
    mp3_files = []
    if not os.path.exists(directory):
        return mp3_files
    for filename in os.listdir(directory):
        if filename.endswith(".mp3"):
            mp3_files.append(filename)
    return sorted(mp3_files)

def extract_audio(input_file_path, output_file_path):
    print(f"Извлечение аудио из '{input_file_path}' в '{output_file_path}'...")
    try:
        # -vn: no video, -acodec libmp3lame: use mp3 codec, -q:a 0: highest quality mp3
        subprocess.run(["ffmpeg", "-i", input_file_path, "-vn", "-acodec", "libmp3lame", "-q:a", "0", output_file_path], check=True)
        print(f"Аудио успешно извлечено в '{output_file_path}'.")
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при извлечении аудио: {e}")
    except FileNotFoundError:
        print("Ошибка: ffmpeg не найден. Убедитесь, что ffmpeg установлен и доступен в PATH.")

def main():
    if not check_ffmpeg():
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    webm_files = get_webm_files(INPUT_DIR)
    extracted_audio_files = get_extracted_audio_files(OUTPUT_DIR)

    if not webm_files:
        print(f"В папке '{INPUT_DIR}' не найдено файлов .webm.")
        return

    print("\nДоступные .webm файлы:")
    files_to_process = []
    for i, webm_file in enumerate(webm_files):
        base_name = os.path.splitext(webm_file)[0]
        corresponding_mp3 = f"{base_name}.mp3"
        status = " (аудио уже извлечено)" if corresponding_mp3 in extracted_audio_files else ""
        print(f"{i + 1}. {webm_file}{status}")
        files_to_process.append((webm_file, corresponding_mp3 in extracted_audio_files))

    while True:
        try:
            choice = input("\nВыберите номер файла для извлечения аудио (или 'q' для выхода): ")
            if choice.lower() == 'q':
                break
            
            choice_index = int(choice) - 1
            if 0 <= choice_index < len(files_to_process):
                selected_webm_file, already_extracted = files_to_process[choice_index]
                
                if already_extracted:
                    confirm = input(f"Аудио для '{selected_webm_file}' уже извлечено. Хотите извлечь его снова? (y/n): ")
                    if confirm.lower() != 'y':
                        continue

                input_path = os.path.join(INPUT_DIR, selected_webm_file)
                output_base_name = os.path.splitext(selected_webm_file)[0]
                output_path = os.path.join(OUTPUT_DIR, f"{output_base_name}.mp3")
                
                extract_audio(input_path, output_path)
                # Обновить список извлеченных файлов после успешного извлечения
                extracted_audio_files = get_extracted_audio_files(OUTPUT_DIR)
                # Обновить статус в files_to_process
                files_to_process[choice_index] = (selected_webm_file, True)
                print("\nОбновленный список .webm файлов:")
                for i, (webm_file, extracted) in enumerate(files_to_process):
                    status = " (аудио уже извлечено)" if extracted else ""
                    print(f"{i + 1}. {webm_file}{status}")

            else:
                print("Неверный выбор. Пожалуйста, введите действительный номер.")
        except ValueError:
            print("Неверный ввод. Пожалуйста, введите номер или 'q'.")

if __name__ == "__main__":
    main()
