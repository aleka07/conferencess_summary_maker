

import os
import subprocess
import argparse
from datetime import datetime
import shutil
from google import genai
from google.genai import types
from dotenv import load_dotenv

# --- КОНСТАНТЫ ---
INPUT_DIR = "input"
AUDIO_FROM_INPUT_DIR = "audio-from-input"
CHUNKS_DIR = "chunks"
RAW_TEXT_DIR = "raw_text"
SUMMARIES_DIR = "summaries"

CHUNK_DURATION_MINUTES = 10
OVERLAP_SECONDS = 2
FULL_TRANSCRIPT_FILENAME = "_full_transcript.txt"
SUMMARY_FILENAME = "_summary.txt"

# --- УТИЛИТЫ ---
def check_ffmpeg_and_ffprobe():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        subprocess.run(["ffprobe", "-version"], capture_output=True, check=True)
        print("ffmpeg и ffprobe установлены.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Ошибка: ffmpeg или ffprobe не найдены. Пожалуйста, установите их для продолжения.")
        return False

def get_file_duration(file_path):
    try:
        result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path], capture_output=True, text=True, check=True)
        return float(result.stdout)
    except (subprocess.CalledProcessError, ValueError) as e:
        print(f"Ошибка при получении длительности файла {file_path}: {e}")
        return None

def format_seconds_to_hhmmss(seconds):
    hh = seconds // 3600
    mm = (seconds % 3600) // 60
    ss = seconds % 60
    return f"{hh:02}:{mm:02}:{ss:02}"

# --- ШАГ 1: ОБРАБОТКА ВХОДНОГО ФАЙЛА ---
def process_input_file(input_file_path):
    os.makedirs(AUDIO_FROM_INPUT_DIR, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(input_file_path))[0]
    timestamp = datetime.now().strftime("%Y-%m-%dT%H_%M_%S.%fZ")
    unique_name = f"{base_name}_{timestamp}"
    output_audio_path = os.path.join(AUDIO_FROM_INPUT_DIR, f"{unique_name}.mp3")

    file_extension = os.path.splitext(input_file_path)[1].lower()

    if file_extension == ".webm":
        print(f"Извлечение аудио из видеофайла '{input_file_path}' в '{output_audio_path}'...")
        try:
            subprocess.run(["ffmpeg", "-i", input_file_path, "-vn", "-acodec", "libmp3lame", "-q:a", "0", output_audio_path], check=True)
            print(f"Аудио успешно извлечено в '{output_audio_path}'.")
        except subprocess.CalledProcessError as e:
            print(f"Ошибка при извлечении аудио: {e}")
            return None
    elif file_extension in [".mp3", ".m4a", ".wav"]:
        print(f"Конвертация/копирование аудиофайла '{input_file_path}' в '{output_audio_path}'...")
        try:
            # Конвертируем в mp3, если формат отличается, или просто копируем, если уже mp3
            subprocess.run(["ffmpeg", "-i", input_file_path, "-acodec", "libmp3lame", "-q:a", "0", output_audio_path], check=True)
            print(f"Аудио успешно обработано и сохранено в '{output_audio_path}'.")
        except subprocess.CalledProcessError as e:
            print(f"Ошибка при обработке аудио: {e}")
            return None
    else:
        print(f"Неподдерживаемый формат входного файла: {file_extension}. Поддерживаются .webm, .mp3, .m4a, .wav.")
        return None
    
    return unique_name, output_audio_path

# --- ШАГ 2: РАЗДЕЛЕНИЕ АУДИО НА ЧАНКИ ---
def split_audio_into_chunks(audio_file_path, unique_name):
    print(f"\nРазделение '{os.path.basename(audio_file_path)}' на фрагменты...")
    duration = get_file_duration(audio_file_path)
    if duration is None:
        return False

    output_chunk_dir = os.path.join(CHUNKS_DIR, unique_name)
    os.makedirs(output_chunk_dir, exist_ok=True)

    chunk_duration_seconds = CHUNK_DURATION_MINUTES * 60
    num_chunks = int(math.ceil(duration / chunk_duration_seconds))

    for i in range(num_chunks):
        start_time = i * chunk_duration_seconds
        current_chunk_duration = chunk_duration_seconds

        if i > 0:
            start_time = max(0, start_time - OVERLAP_SECONDS)
            current_chunk_duration += OVERLAP_SECONDS
        
        if start_time + current_chunk_duration > duration:
            current_chunk_duration = duration - start_time

        output_chunk_path = os.path.join(output_chunk_dir, f"{unique_name}_part{i+1:03d}.mp3")
        
        print(f"  Создание фрагмента {i+1}/{num_chunks}: {os.path.basename(output_chunk_path)} (начало: {start_time:.2f}s, длительность: {current_chunk_duration:.2f}s)")
        try:
            subprocess.run(["ffmpeg", "-i", audio_file_path, "-ss", str(start_time), "-t", str(current_chunk_duration), "-c", "copy", output_chunk_path], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Ошибка при создании фрагмента {i+1}: {e}")
            if os.path.exists(output_chunk_path):
                os.remove(output_chunk_path)
            return False
    print(f"Разделение '{os.path.basename(audio_file_path)}' завершено.")
    return True

# --- ШАГ 3: ТРАНСКРИБАЦИЯ ЧАНКОВ ---
def transcribe_chunks(unique_name, api_key):
    if not api_key:
        print("Ошибка: API ключ Gemini не предоставлен. Транскрибация невозможна.")
        return False

    try:
        client = genai.Client(api_key=api_key)
        print("Клиент Gemini успешно инициализирован.")
    except Exception as e:
        print(f"Ошибка инициализации клиента Gemini: {e}\nПожалуйста, проверьте ваш API_KEY.")
        return False

    chunks_folder_path = os.path.join(CHUNKS_DIR, unique_name)
    output_meeting_folder = os.path.join(RAW_TEXT_DIR, unique_name)
    os.makedirs(output_meeting_folder, exist_ok=True)
    print(f"Результаты транскрибации будут сохранены в: {output_meeting_folder}")

    chunk_files = sorted([f for f in os.listdir(chunks_folder_path) if f.endswith('.mp3')])
    
    PROMPT = """
**Системная роль (System/Role Instruction)**

Ты — продвинутый ИИ-ассистент, специализирующийся на транскрибации сложных многоязычных аудиозаписей. Твоя главная задача — создать абсолютно точный текстовый документ, который сохраняет все языковые нюансы речи.

**Задача (Task)**

Транскрибируй предоставленный аудиофрагмент. Основа разговора ведется на русском языке, но он может содержать вставки на английском и казахском языках. Твоя задача — точно передать это смешение языков.

**Ключевое требование: Обработка нескольких языков**

**Не переводи и не транслитерируй слова и фразы с английского или казахского языков.** Записывай их в оригинале, используя соответствующий алфавит (латиницу для английского, кириллицу или латиницу для казахского). Это критически важно для сохранения точности технических терминов и культурного контекста.

**Остальные правила форматирования (Other Formatting Rules)**

1.  **Без определения спикеров:** Не помечай разных говорящих (без диаризации).
2.  **Структура по абзацам:** Разделяй текст на логические абзацы при смене темы или после паузы.
3.  **Тайм-коды:** В начале каждого нового абзаца ставь отметку времени в формате `[ЧЧ:ММ:СС]`.
4.  **Очистка речи:** Удаляй только очевидные слова-паразиты ("эээ", "ммм"), не меняя стиль и лексику говорящих.
5.  **Пунктуация:** Расставляй знаки препинания, чтобы текст был грамматически верным и читаемым.

**Пример требуемого формата вывода (Example of Required Output Format)**

Вот пример точного формата, которому ты должен следовать. Обрати внимание, как сохранены иноязычные слова:

```text
[00:01:23] Коллеги, наш ключевой KPI по new user acquisition пока не выполняется. Нужно срочно что-то предпринять. Предлагаю на следующей неделе провести несколько A/B-тестов, чтобы проверить гипотезы.

[00:01:55] Согласен, это хороший план. Также давайте не забывать про customer feedback. Я вчера получил письмо от клиента, он пишет, что в целом всё отлично, но есть пара мелких багов в интерфейсе. Жарайсыңдар, что мы так быстро реагируем на обратную связь.

[00:02:10] Отлично, тогда так и сделаем. Всем большое рахмет за продуктивное обсуждение. На сегодня всё, a meeting is over.
"""
    
    for i, filename in enumerate(chunk_files):
        print(f"\nОбрабатываю чанк {i+1}/{len(chunk_files)}: {filename}")
        file_path = os.path.join(chunks_folder_path, filename)
        
        try:
            print("Загружаю файл в Gemini...")
            myfile = client.files.upload(file=file_path)
            
            print("Отправляю на транскрибацию...")
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[PROMPT, myfile],
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=-1)
                )
            )
            
            text_to_save = response.text
            
            output_filepath = os.path.join(output_meeting_folder, os.path.splitext(filename)[0] + '.txt')
            with open(output_filepath, 'w', encoding='utf-8') as f:
                f.write(text_to_save)
            print(f"Транскрипция сохранена в: {output_filepath}")

            client.files.delete(name=myfile.name)
            print(f"Файл {myfile.name} удален из облака Gemini.")

        except Exception as e:
            print(f"!!! Произошла ошибка при обработке файла {filename}: {e}")
            print("!!! Пропускаю этот чанк и перехожу к следующему.")
            return False # Возвращаем False, если произошла ошибка
            
    print(f"\n--- Транскрибация для '{unique_name}' завершена! ---")
    return True

# --- ШАГ 4: ОБЪЕДИНЕНИЕ ТРАНСКРИПЦИЙ ---
def merge_transcripts(unique_name):
    meeting_folder_path = os.path.join(RAW_TEXT_DIR, unique_name)
    output_file_path = os.path.join(meeting_folder_path, FULL_TRANSCRIPT_FILENAME)

    print(f"\n--- Начинаю сборку транскрипции для: {unique_name} ---")

    try:
        txt_files = [f for f in os.listdir(meeting_folder_path) if f.endswith('.txt') and f != FULL_TRANSCRIPT_FILENAME]
        txt_files.sort()
    except FileNotFoundError:
        print(f"Ошибка: Папка {meeting_folder_path} не найдена.")
        return False

    if not txt_files:
        print("В папке не найдено .txt файлов для объединения.")
        return False

    print(f"Найдено {len(txt_files)} файлов для объединения.")
    
    chunk_duration_seconds = CHUNK_DURATION_MINUTES * 60

    try:
        with open(output_file_path, 'w', encoding='utf-8') as outfile:
            for i, filename in enumerate(txt_files):
                file_path = os.path.join(meeting_folder_path, filename)
                
                with open(file_path, 'r', encoding='utf-8') as infile:
                    content = infile.read().strip()
                    outfile.write(content)
                
                part_num = i + 1
                start_seconds = i * chunk_duration_seconds
                end_seconds = part_num * chunk_duration_seconds
                
                start_time_str = format_seconds_to_hhmmss(start_seconds)
                end_time_str = format_seconds_to_hhmmss(end_seconds)

                metadata_line = f"\n\n--- Конец Части-{part_num}, Время: {start_time_str} - {end_time_str} ---"
                outfile.write(metadata_line)
                
                if i < len(txt_files) - 1:
                    outfile.write("\n\n")
        
        print(f"Успешно! Все части собраны в один файл: {output_file_path}")
        return True

    except Exception as e:
        print(f"Произошла ошибка во время сборки файлов: {e}")
        return False

# --- ШАГ 5: СОЗДАНИЕ РЕЗЮМЕ ---
def create_summary(unique_name, api_key):
    if not api_key:
        print("Ошибка: API ключ Gemini не предоставлен. Создание резюме невозможно.")
        return False

    try:
        client = genai.Client(api_key=api_key)
        print("Клиент Gemini успешно инициализирован для создания резюме.")
    except Exception as e:
        print(f"Ошибка инициализации клиента Gemini: {e}\nПожалуйста, проверьте ваш API_KEY.")
        return False

    full_transcript_path = os.path.join(RAW_TEXT_DIR, unique_name, FULL_TRANSCRIPT_FILENAME)
    output_dir = os.path.join(SUMMARIES_DIR, unique_name)
    output_filepath = os.path.join(output_dir, SUMMARY_FILENAME)
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        print(f"Читаю файл транскрипции: {full_transcript_path}")
        with open(full_transcript_path, 'r', encoding='utf-8') as f:
            full_text = f.read()
        if not full_text.strip():
            print("Ошибка: Файл транскрипции пуст. Пропускаю создание резюме.")
            return False
    except FileNotFoundError:
        print(f"Ошибка: Файл '{full_transcript_path}' не найден. Пропускаю создание резюме.")
        return False
        
    SUMMARIZE_PROMPT = """
**Системная роль (System/Role Instruction)**

Ты — элитный бизнес-аналитик. Твоя суперспособность — превращать хаотичные записи встреч в кристально чистые, структурированные и полезные отчеты. Ты умеешь улавливать главное и отсеивать второстепенное.

**Задача (Task)**

Проанализируй предоставленную транскрипцию совещания. Твоя цель — создать профессиональное резюме в формате Markdown. **Внимательно изучи содержание разговора и самостоятельно реши, какие из предложенных ниже разделов наиболее точно отражают его суть. Используй только релевантные разделы.**

**Контекст входных данных:**

Текст является полной транскрипцией совещания. Он может содержать технические термины и фразы на разных языках.

**Инструкции по стилю и формату:**

1.  **Гибкая структура:** Выбери и используй только те разделы из списка ниже, для которых в тексте есть значимая информация. Если, например, на встрече не было принято никаких решений, не включай раздел "✅ Принятые решения".
2.  **Формат Markdown:** Используй Markdown для заголовков и списков.
3.  **Строго по тексту:** Не додумывай информацию. Все выводы должны быть основаны исключительно на предоставленном тексте.
4.  **Лаконичный язык:** Пиши ясно, по делу, без воды.

**--- Меню разделов для отчета (выбери подходящие) ---**

### Итоги встречи: [Краткое название встречи, взятое из контекста]

#### 🔹 Ключевые темы обсуждения:
- (Список основных тем, которые поднимались)

#### 🎯 Главные выводы и результаты:
- (Основные заключения, итоги анализа или результаты, к которым пришла команда)

#### ✅ Принятые решения:
- (Список конкретных, утвержденных решений)

####  actionable Поставленные задачи (Action Items):
- **[Ответственный, если упоминается]**: (Описание задачи и, если есть, крайний срок)

#### ⚠️ Выявленные риски и проблемные зоны:
- (Список потенциальных проблем, рисков или препятствий, которые были озвучены)

#### ❓ Открытые вопросы и темы для будущих обсуждений:
- (Список вопросов, которые остались нерешенными или были отложены)

"""
    
    try:
        print("Отправляю текст в Gemini для создания резюме... Это может занять некоторое время (режим 'глубокого мышления' включен).")
        prompt_with_context = SUMMARIZE_PROMPT.replace("[Краткое название встречи, взятое из контекста]", unique_name)
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt_with_context, full_text],
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=-1)
            )
        )
        summary_text = response.text
        
        with open(output_filepath, 'w', encoding='utf-8') as f:
            f.write(summary_text)
        print(f"Успешно! Резюме сохранено в: {output_filepath}")
        return True

    except Exception as e:
        print(f"!!! Произошла ошибка при обращении к Gemini API: {e}")
        return False

# --- ОСНОВНАЯ ЛОГИКА ---
def main():
    parser = argparse.ArgumentParser(description="Мастер-скрипт для обработки аудио/видео, транскрибации и создания резюме.")
    parser.add_argument("input_file", help="Путь к входному аудио или видео файлу (.webm, .mp3, .m4a, .wav).")
    parser.add_argument("--clean_up", action="store_true", help="Удалить промежуточные файлы (чанки, отдельные транскрипции) после завершения.")
    
    args = parser.parse_args()

    load_dotenv() # Загружаем переменные из .env файла

    if not check_ffmpeg_and_ffprobe():
        return

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Ошибка: API ключ Gemini не найден. Пожалуйста, установите переменную окружения GEMINI_API_KEY в файле .env или в вашей системе.")
        return

    # Шаг 1
    print("\n--- Шаг 1: Обработка входного файла ---")
    result_step1 = process_input_file(args.input_file)
    if result_step1 is None:
        print("Обработка входного файла завершилась с ошибкой. Выход.")
        return
    unique_name, processed_audio_path = result_step1

    # Шаг 2
    print("\n--- Шаг 2: Разделение аудио на чанки ---")
    if not split_audio_into_chunks(processed_audio_path, unique_name):
        print("Разделение аудио на чанки завершилось с ошибкой. Выход.")
        return

    # Шаг 3
    print("\n--- Шаг 3: Транскрибация чанков ---")
    if not transcribe_chunks(unique_name, api_key):
        print("Транскрибация чанков завершилась с ошибкой. Выход.")
        return

    # Шаг 4
    print("\n--- Шаг 4: Объединение транскрипций ---")
    if not merge_transcripts(unique_name):
        print("Объединение транскрипций завершилось с ошибкой. Выход.")
        return

    # Шаг 5
    print("\n--- Шаг 5: Создание резюме ---")
    if not create_summary(unique_name, api_key):
        print("Создание резюме завершилось с ошибкой. Выход.")
        return

    # Очистка
    if args.clean_up:
        print("\n--- Очистка промежуточных файлов ---")
        try:
            shutil.rmtree(os.path.join(CHUNKS_DIR, unique_name))
            print(f"Удалена папка чанков: {os.path.join(CHUNKS_DIR, unique_name)}")
            shutil.rmtree(os.path.join(RAW_TEXT_DIR, unique_name))
            print(f"Удалена папка с отдельными транскрипциями: {os.path.join(RAW_TEXT_DIR, unique_name)}")
            # Удаляем исходный обработанный аудиофайл
            os.remove(processed_audio_path)
            print(f"Удален обработанный аудиофайл: {processed_audio_path}")
        except OSError as e:
            print(f"Ошибка при очистке: {e}")

    print("\n--- Все операции успешно завершены! ---")
    print(f"Полная транскрипция: {os.path.join(RAW_TEXT_DIR, unique_name, FULL_TRANSCRIPT_FILENAME)}")
    print(f"Резюме: {os.path.join(SUMMARIES_DIR, unique_name, SUMMARY_FILENAME)}")

if __name__ == "__main__":
    import math # Импортируем math здесь, так как он используется в split_audio_into_chunks
    main()
