import os
from dotenv import load_dotenv
from openai import OpenAI

# ---------------------------------------------------------------------------
# 📦 1.  ENV & CLIENT INITIALISATION
# ---------------------------------------------------------------------------
load_dotenv()

API_KEY = os.environ.get("OPENROUTER_API_KEY")  # <-- put your key in .env
if not API_KEY:
    raise EnvironmentError("Environment variable OPENROUTER_API_KEY not found.")

# Endpoint and model
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODEL_ID = "deepseek/deepseek-r1:free"  # free tier model slug

client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=API_KEY)
print("OpenRouter client initialised (DeepSeek‑R1).")

# ---------------------------------------------------------------------------
# 🗂️ 2.  PATHS & CONSTANTS (retain original directory logic)
# ---------------------------------------------------------------------------
RAW_TEXT_BASE_DIR = "raw_text"
FULL_TRANSCRIPT_FILENAME = "_full_transcript.txt"
SUMMARIES_BASE_DIR = "summaries"
SUMMARY_FILENAME = "_summary.txt"

# ---------------------------------------------------------------------------
# 📝 3.  FLEXIBLE MARKDOWN PROMPT (no system role)
# ---------------------------------------------------------------------------
SUMMARIZE_PROMPT = """
Ты — элитный бизнес‑аналитик. Твоя задача – превратить транскрипцию
совещания в профессиональное резюме (Markdown).

**Инструкции по стилю и формату**
1. Выбери только релевантные разделы из меню ниже.
2. Используй Markdown‑заголовки и списки.
3. Не придумывай фактов, опирайся строго на текст.
4. Пиши лаконично.

--- Меню разделов ---
### Итоги встречи: [Краткое название встречи]
#### 🔹 Ключевые темы обсуждения:
- …
#### 🎯 Главные выводы и результаты:
- …
#### ✅ Принятые решения:
- …
####  actionable Поставленные задачи (Action Items):
- **[Ответственный]**: …
#### ⚠️ Выявленные риски и проблемные зоны:
- …
#### ❓ Открытые вопросы и темы для будущих обсуждений:
- …
"""
# SUMMARIZE_PROMPT = "Проанализируй транскрипцию совещания в профессиональное резюме."

# ---------------------------------------------------------------------------
# 🔍 4.  UTILS (unchanged)
# ---------------------------------------------------------------------------

def get_meetings_for_summarization():
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
    summary_path = os.path.join(SUMMARIES_BASE_DIR, meeting_name, SUMMARY_FILENAME)
    return os.path.exists(summary_path)

# ---------------------------------------------------------------------------
# ✨ 5.  CORE SUMMARISATION FUNCTION (OpenRouter replacement)
# ---------------------------------------------------------------------------

def create_summary_for_meeting(meeting_name):
    print(f"\n--- Создаю резюме для: {meeting_name} ---")

    full_transcript_path = os.path.join(RAW_TEXT_BASE_DIR, meeting_name, FULL_TRANSCRIPT_FILENAME)
    output_dir = os.path.join(SUMMARIES_BASE_DIR, meeting_name)
    output_filepath = os.path.join(output_dir, SUMMARY_FILENAME)
    os.makedirs(output_dir, exist_ok=True)

    try:
        with open(full_transcript_path, "r", encoding="utf-8") as f:
            full_text = f.read()
        if not full_text.strip():
            print("Ошибка: Файл транскрипции пуст. Пропускаю.")
            return
    except FileNotFoundError:
        print(f"Ошибка: Файл '{full_transcript_path}' не найден.")
        return

    # Compose single‑message prompt as recommended for DeepSeek‑R1
    user_message = (
        SUMMARIZE_PROMPT.replace("[Краткое название встречи]", meeting_name)
        + "\n\n```TRANSCRIPT\n" + full_text + "\n```"
    )

    try:
        print("Отправляю запрос модели DeepSeek‑R1 (free)…")
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[{"role": "user", "content": user_message}],
            temperature=0.6,
            top_p=0.95,
        )
        summary_text = response.choices[0].message.content

        with open(output_filepath, "w", encoding="utf-8") as f:
            f.write(summary_text)
        print(f"✅ Резюме сохранено: {output_filepath}")

    except Exception as e:
        print(f"Ошибка запроса к OpenRouter / DeepSeek‑R1: {e}")

# ---------------------------------------------------------------------------
# 🏃‍♂️ 6.  MAIN LOOP (identical to original)
# ---------------------------------------------------------------------------

def main():
    os.makedirs(SUMMARIES_BASE_DIR, exist_ok=True)

    while True:
        meetings = get_meetings_for_summarization()
        if not meetings:
            print(f"В '{RAW_TEXT_BASE_DIR}' нет транскрипций ('{FULL_TRANSCRIPT_FILENAME}').")
            break

        print("\nДоступные совещания:")
        meetings_to_process = []
        for i, meeting_name in enumerate(meetings):
            status = "(резюме уже создано)" if get_summary_status(meeting_name) else ""
            print(f"{i + 1}. {meeting_name} {status}")
            meetings_to_process.append((meeting_name, get_summary_status(meeting_name)))

        choice = input("\nВыберите номер совещания (или 'q' для выхода): ")
        if choice.lower() == 'q':
            break
        if not choice.isdigit():
            print("Неверный ввод.")
            continue

        idx = int(choice) - 1
        if idx < 0 or idx >= len(meetings_to_process):
            print("Номер вне диапазона.")
            continue

        selected_meeting, already = meetings_to_process[idx]
        if already:
            if input(f"Резюме для '{selected_meeting}' существует. Пересоздать? (y/n): ").lower() != 'y':
                continue
        create_summary_for_meeting(selected_meeting)


if __name__ == "__main__":
    main()