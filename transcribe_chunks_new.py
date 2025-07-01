import os
import shutil
from google import genai
from google.genai import types

# --- НАСТРОЙКИ ---
# ВАЖНО: Укажите ваш API ключ
API_KEY = os.environ.get("GEMINI_API_KEY")  # <-- ЗАМЕНИТЕ ВАШИМ КЛЮЧОМ

CHUNKS_BASE_DIR = "chunks"
RAW_TEXT_BASE_DIR = "raw_text"
# --- КОНЕЦ НАСТРОЕК ---


# --- КЛИЕНТ И ПРОМПТ ---
try:
    # Используем ваш рабочий способ инициализации клиента
    CLIENT = genai.Client(api_key=API_KEY)
    print("Клиент Gemini успешно инициализирован.")
except Exception as e:
    print(f"Ошибка инициализации клиента Gemini: {e}")
    print("Пожалуйста, проверьте ваш API_KEY.")
    CLIENT = None

PROMPT = """
**Системная роль (System/Role Instruction)**

Ты — продвинутый ИИ-ассистент, специализирующийся на транскрибации сложных многоязычных аудиозаписей. Твоя главная задача — создать абсолютно точный текстовый документ, который сохраняет все языковые нюансы речи.

**Задача (Task)**

Транскрибируй предоставленный аудиофрагмент. Основа разговора ведется на русском языке, но он содержит вставки на английском и казахском языках. Твоя задача — точно передать это смешение языков.

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
# --- КОНЕЦ ПРОМПТА ---


def get_meeting_folders(directory):
    """Находит папки совещаний в директории с чанками."""
    folders = []
    if not os.path.exists(directory):
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
        num_mp3 = len([f for f in os.listdir(chunks_dir) if f.endswith('.mp3')])
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

def process_meeting_folder(meeting_name, force_rerun=False):
    """Основная функция обработки папки с чанками одного совещания."""
    print(f"\n--- Начинаю обработку совещания: {meeting_name} ---")
    chunks_folder_path = os.path.join(CHUNKS_BASE_DIR, meeting_name)
    output_meeting_folder = os.path.join(RAW_TEXT_BASE_DIR, meeting_name)

    if force_rerun and os.path.exists(output_meeting_folder):
        print(f"Удаляю предыдущие результаты из: {output_meeting_folder}")
        shutil.rmtree(output_meeting_folder)
    
    os.makedirs(output_meeting_folder, exist_ok=True)
    print(f"Результаты будут сохранены в: {output_meeting_folder}")

    chunk_files = sorted([f for f in os.listdir(chunks_folder_path) if f.endswith('.mp3')])
    
    for i, filename in enumerate(chunk_files):
        print(f"\nОбрабатываю чанк {i+1}/{len(chunk_files)}: {filename}")
        file_path = os.path.join(chunks_folder_path, filename)
        
        try:
            print("Загружаю файл в Gemini...")
            myfile = CLIENT.files.upload(file=file_path)
            
            print("Отправляю на транскрибацию...")
            response = CLIENT.models.generate_content(
                model='gemini-2.5-flash',
                contents=[PROMPT, myfile],
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=-1)
                )
            )
            
            # Текст сохраняется как есть, без коррекции тайм-кодов
            text_to_save = response.text
            
            output_filepath = os.path.join(output_meeting_folder, os.path.splitext(filename)[0] + '.txt')
            with open(output_filepath, 'w', encoding='utf-8') as f:
                f.write(text_to_save)
            print(f"Транскрипция сохранена в: {output_filepath}")

            CLIENT.files.delete(name=myfile.name)
            print(f"Файл {myfile.name} удален из облака Gemini.")

        except Exception as e:
            print(f"!!! Произошла ошибка при обработке файла {filename}: {e}")
            print("!!! Пропускаю этот чанк и перехожу к следующему.")
            continue
            
    print(f"\n--- Обработка совещания {meeting_name} завершена! ---")


def main():
    if not CLIENT:
        return
        
    os.makedirs(RAW_TEXT_BASE_DIR, exist_ok=True)
    
    while True:
        meeting_folders = get_meeting_folders(CHUNKS_BASE_DIR)

        if not meeting_folders:
            print(f"В папке '{CHUNKS_BASE_DIR}' не найдено папок с чанками.")
            break

        print("\nДоступные совещания для транскрибации:")
        meetings_to_process = []
        for i, folder_name in enumerate(meeting_folders):
            status = get_transcription_status(folder_name)
            print(f"{i + 1}. {folder_name} - Статус: {status}")
            meetings_to_process.append((folder_name, status))
        
        try:
            choice = input("\nВыберите номер совещания для транскрибации (или 'q' для выхода): ")
            if choice.lower() == 'q':
                break
            
            choice_index = int(choice) - 1
            if 0 <= choice_index < len(meetings_to_process):
                selected_meeting, status = meetings_to_process[choice_index]
                
                force_rerun = False
                if status not in ["Не начато", "Нет аудио-чанков"]:
                    confirm = input(f"Транскрипция для '{selected_meeting}' уже существует. Хотите запустить заново и перезаписать все файлы? (y/n): ")
                    if confirm.lower() != 'y':
                        continue
                    force_rerun = True
                
                process_meeting_folder(selected_meeting, force_rerun=force_rerun)

            else:
                print("Неверный выбор. Пожалуйста, введите действительный номер.")
        except ValueError:
            print("Неверный ввод. Пожалуйста, введите номер или 'q'.")

if __name__ == "__main__":
    main()