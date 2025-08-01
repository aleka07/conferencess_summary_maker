import os
import shutil
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
load_dotenv()   

# --- НАСТРОЙКИ ---
API_KEY = os.environ.get("GEMINI_API_KEY")  # <-- ЗАМЕНИТЕ ВАШИМ КЛЮЧОМ

RAW_TEXT_BASE_DIR = "raw_text"
FULL_TRANSCRIPT_FILENAME = "_full_transcript.txt"
SUMMARIES_BASE_DIR = "summaries"
SUMMARY_FILENAME = "_summary.txt"
# --- КОНЕЦ НАСТРОЕК ---


# --- КЛИЕНТ И ПРОМПТ ---
try:
    CLIENT = genai.Client(api_key=API_KEY)
    print("Клиент Gemini успешно инициализирован.")
except Exception as e:
    print(f"Ошибка инициализации клиента Gemini: {e}\nПожалуйста, проверьте ваш API_KEY.")
    CLIENT = None

# Новый гибкий промпт
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
# --- КОНЕЦ ПРОМПТА ---


def get_meetings_for_summarization():
    """Находит папки совещаний, для которых есть полная транскрипция."""
    folders = []
    if not os.path.exists(RAW_TEXT_BASE_DIR):
        print(f"Ошибка: Базовая папка '{RAW_TEXT_BASE_DIR}' не найдена.")
        return folders
    for item in os.listdir(RAW_TEXT_BASE_DIR):
        full_transcript_path = os.path.join(RAW_TEXT_BASE_DIR, item, FULL_TRANSCRIPT_FILENAME)
        if os.path.isfile(full_transcript_path):
            folders.append(item)
    return sorted(folders)

def get_summary_status(meeting_name):
    """Проверяет, было ли уже создано резюме для данного совещания."""
    summary_path = os.path.join(SUMMARIES_BASE_DIR, meeting_name, SUMMARY_FILENAME)
    return os.path.exists(summary_path)

def create_summary_for_meeting(meeting_name):
    """Создает резюме для выбранного совещания."""
    print(f"\n--- Начинаю создание резюме для: {meeting_name} ---")
    
    full_transcript_path = os.path.join(RAW_TEXT_BASE_DIR, meeting_name, FULL_TRANSCRIPT_FILENAME)
    output_dir = os.path.join(SUMMARIES_BASE_DIR, meeting_name)
    output_filepath = os.path.join(output_dir, SUMMARY_FILENAME)
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        print(f"Читаю файл транскрипции: {full_transcript_path}")
        with open(full_transcript_path, 'r', encoding='utf-8') as f:
            full_text = f.read()
        if not full_text.strip():
            print("Ошибка: Файл транскрипции пуст. Пропускаю.")
            return
    except FileNotFoundError:
        print(f"Ошибка: Файл '{full_transcript_path}' не найден. Пропускаю.")
        return
        
    try:
        print("Отправляю текст в Gemini для создания резюме... Это может занять некоторое время (режим 'глубокого мышления' включен).")
        prompt_with_context = SUMMARIZE_PROMPT.replace("[Краткое название встречи, взятое из контекста]", meeting_name)
        
        # --- ИЗМЕНЕНИЕ ЗДЕСЬ: добавлен config с thinking_budget ---
        response = CLIENT.models.generate_content(
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

    except Exception as e:
        print(f"!!! Произошла ошибка при обращении к Gemini API: {e}")

def main():
    if not CLIENT:
        return
        
    os.makedirs(SUMMARIES_BASE_DIR, exist_ok=True)
    
    while True:
        meetings = get_meetings_for_summarization()
        if not meetings:
            print(f"В папке '{RAW_TEXT_BASE_DIR}' не найдено готовых транскрипций ('{FULL_TRANSCRIPT_FILENAME}').")
            break

        print("\nДоступные совещания для создания резюме:")
        meetings_to_process = []
        for i, meeting_name in enumerate(meetings):
            status = "(резюме уже создано)" if get_summary_status(meeting_name) else ""
            print(f"{i + 1}. {meeting_name} {status}")
            meetings_to_process.append((meeting_name, get_summary_status(meeting_name)))
        
        try:
            choice = input("\nВыберите номер совещания для создания резюме (или 'q' для выхода): ")
            if choice.lower() == 'q':
                break
            
            choice_index = int(choice) - 1
            if 0 <= choice_index < len(meetings_to_process):
                selected_meeting, already_summarized = meetings_to_process[choice_index]
                
                if already_summarized:
                    confirm = input(f"Резюме для '{selected_meeting}' уже существует. Хотите создать его заново? (y/n): ")
                    if confirm.lower() != 'y':
                        continue
                
                create_summary_for_meeting(selected_meeting)
            else:
                print("Неверный выбор. Пожалуйста, введите действительный номер.")
        except ValueError:
            print("Неверный ввод. Пожалуйста, введите номер или 'q'.")

if __name__ == "__main__":
    main()