#!/bin/bash
set -e # Останавливаем выполнение при любой ошибке

# --- Проверка входных аргументов ---
if [ -z "$1" ]; then
  echo "Ошибка: Укажите имя входного файла (включая расширение)."
  echo "Пример: ./run.sh meeting1.webm"
  echo "Пример: ./run.sh weekly-sync.mp3"
  exit 1
fi

INPUT_FILENAME=$1
# Извлекаем имя без расширения, например, 'meeting1' из 'meeting1.webm'
MEETING_NAME=$(basename "$INPUT_FILENAME" | sed 's/\(.*\)\..*/\1/')
EXTENSION="${INPUT_FILENAME##*.}"

echo "================================================="
echo "🚀 НАЧАЛО ОБРАБОТКИ ФАЙЛА: $INPUT_FILENAME"
echo "   (Название совещания: $MEETING_NAME)"
echo "================================================="

AUDIO_FOR_SPLITTING=""

# --- Шаг 1: Извлечение аудио (ТОЛЬКО ДЛЯ ВИДЕО) ---
case $EXTENSION in
  webm|mp4|mov|mkv|avi)
    echo -e "\n[1/5] Обнаружен видеофайл. Извлечение аудио..."
    EXTRACTED_AUDIO_PATH="/data/1_extracted_audio/${MEETING_NAME}.mp3"
    python3 scripts/1_extract_audio.py "/data/input/${INPUT_FILENAME}" "$EXTRACTED_AUDIO_PATH"
    AUDIO_FOR_SPLITTING=$EXTRACTED_AUDIO_PATH
    ;;
  mp3|wav|m4a|flac|ogg)
    echo -e "\n[1/5] Обнаружен аудиофайл. Шаг извлечения аудио пропущен."
    AUDIO_FOR_SPLITTING="/data/input/${INPUT_FILENAME}"
    ;;
  *)
    echo "Ошибка: Неподдерживаемый формат файла: .$EXTENSION"
    exit 1
    ;;
esac

if [ -z "$AUDIO_FOR_SPLITTING" ]; then
    echo "Критическая ошибка: не удалось определить аудиофайл для обработки."
    exit 1
fi

# --- Последующие шаги работают с определенным аудиофайлом ---
echo -e "\n[2/5] Разделение аудио на фрагменты..."
python3 scripts/2_split_audio.py "$AUDIO_FOR_SPLITTING" "$MEETING_NAME"

echo -e "\n[3/5] Запуск локальной транскрибации (Whisper)..."
python3 scripts/3_transcribe_local_batch.py "$MEETING_NAME"

echo -e "\n[4/5] Сборка полной транскрипции..."
python3 scripts/4_merge_transcripts.py "$MEETING_NAME"

echo -e "\n[5/5] Создание итогового резюме (OpenRouter)..."
python3 scripts/5_create_summary.py "$MEETING_NAME"

echo "================================================="
echo "✅ ПРОЦЕСС ОБРАБОТКИ ДЛЯ '$MEETING_NAME' УСПЕШНО ЗАВЕРШЕН!"
echo "================================================="