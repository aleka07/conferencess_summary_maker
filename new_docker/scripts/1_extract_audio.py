import os
import sys
import subprocess

def extract_audio(input_file_path, output_file_path):
    """Извлекает аудиодорожку из видеофайла с помощью ffmpeg."""
    print(f"Извлечение аудио из '{input_file_path}' в '{output_file_path}'...")
    
    # Создаем папку для выходного файла, если она не существует
    os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
    
    try:
        # -y: перезаписывать выходной файл без вопроса
        # -i: входной файл
        # -vn: отключить запись видео
        # -acodec libmp3lame: использовать кодек MP3
        # -q:a 0: установить наивысшее возможное качество для MP3
        command = [
            "ffmpeg", "-y", "-i", input_file_path,
            "-vn", "-acodec", "libmp3lame", "-q:a", "0",
            output_file_path
        ]
        
        result = subprocess.run(
            command, check=True, capture_output=True, text=True
        )
        print(f"Аудио успешно извлечено в '{output_file_path}'.")
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при извлечении аудио: {e}", file=sys.stderr)
        print(f"FFmpeg stderr: {e.stderr}", file=sys.stderr)
        sys.exit(1) # Выходим с ошибкой, чтобы остановить run.sh
    except FileNotFoundError:
        print("Ошибка: ffmpeg не найден. Он должен быть установлен в Docker-контейнере.", file=sys.stderr)
        sys.exit(1)

def main():
    if len(sys.argv) != 3:
        print("Использование: python3 1_extract_audio.py <путь_к_входному_видео> <путь_к_выходному_аудио>", file=sys.stderr)
        sys.exit(1)
        
    input_video = sys.argv[1]
    output_audio = sys.argv[2]
    
    if not os.path.exists(input_video):
        print(f"Ошибка: Входной файл не найден по пути: {input_video}", file=sys.stderr)
        sys.exit(1)
        
    extract_audio(input_video, output_audio)

if __name__ == "__main__":
    main()