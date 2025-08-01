import os
import sys
from openai import OpenAI

# Загрузка API ключа происходит из .env файла, который монтируется в контейнер
API_KEY = os.environ.get("OPENROUTER_API_KEY")

# --- НАСТРОЙКИ ---
BASE_DATA_DIR = "/data"
# Папка, откуда берем полные транскрипции
FULL_TRANSCRIPT_DIR = os.path.join(BASE_DATA_DIR, "4_full_transcripts")
FULL_TRANSCRIPT_FILENAME_TEMPLATE = "{meeting_name}_full_transcript.txt"
SUMMARIES_BASE_DIR = os.path.join(BASE_DATA_DIR, "5_summaries")
SUMMARY_FILENAME_TEMPLATE = "{meeting_name}_summary.md" # Используем .md для Markdown

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODEL_ID = "deepseek/deepseek-r1:free"
# --- КОНЕЦ НАСТРОЕК ---

SUMMARIZE_PROMPT = """
Ты — элитный бизнес‑аналитик. Твоя задача – превратить транскрипцию
совещания в профессиональное резюме (Markdown).

**Инструкции по стилю и формату**
1.  Выбери только релевантные разделы из меню ниже.
2.  Используй Markdown‑заголовки и списки.
3.  Не придумывай фактов, опирайся строго на текст.
4.  Пиши лаконично и по делу.

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

def create_summary_for_meeting(meeting_name):
    """Создает резюме для совещания с помощью языковой модели."""
    print(f"\n--- Создаю резюме для: {meeting_name} ---")

    if not API_KEY:
        print("Ошибка: Переменная окружения OPENROUTER_API_KEY не найдена.", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=API_KEY)

    full_transcript_path = os.path.join(FULL_TRANSCRIPT_DIR, FULL_TRANSCRIPT_FILENAME_TEMPLATE.format(meeting_name=meeting_name))
    output_dir = os.path.join(SUMMARIES_BASE_DIR, meeting_name)
    output_filepath = os.path.join(output_dir, SUMMARY_FILENAME_TEMPLATE.format(meeting_name=meeting_name))
    os.makedirs(output_dir, exist_ok=True)

    try:
        with open(full_transcript_path, "r", encoding="utf-8") as f:
            full_text = f.read()
        if not full_text.strip():
            print("Ошибка: Файл транскрипции пуст. Резюме не будет создано.", file=sys.stderr)
            return
    except FileNotFoundError:
        print(f"Ошибка: Файл с полной транскрипцией не найден: '{full_transcript_path}'", file=sys.stderr)
        return

    user_message = (
        SUMMARIZE_PROMPT.replace("[Краткое название встречи]", meeting_name.replace("_", " ").title())
        + "\n\n---\n\nТРАНСКРИПЦИЯ:\n```\n" + full_text + "\n```"
    )

    try:
        print("Отправляю запрос модели DeepSeek‑R1 (free)…")
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[{"role": "user", "content": user_message}],
            temperature=0.5,
            top_p=0.9,
            stream=False
        )
        summary_text = response.choices[0].message.content

        with open(output_filepath, "w", encoding="utf-8") as f:
            f.write(summary_text)
        print(f"✅ Резюме сохранено: {output_filepath}")

    except Exception as e:
        print(f"Ошибка запроса к OpenRouter / DeepSeek‑R1: {e}", file=sys.stderr)

def main():
    if len(sys.argv) != 2:
        print("Использование: python3 5_create_summary.py <имя_совещания>", file=sys.stderr)
        sys.exit(1)
        
    meeting_name = sys.argv[1]
    create_summary_for_meeting(meeting_name)

if __name__ == "__main__":
    main()