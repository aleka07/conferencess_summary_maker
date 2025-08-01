# Указываем базовый образ, идеально подходящий под ваш PyTorch (собранный под CUDA 12.1)
# Мы берем Ubuntu 22.04 как надежную современную основу.
FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

# Устанавливаем переменные окружения, чтобы избежать интерактивных запросов при установке
ENV TZ=Etc/UTC
ENV DEBIAN_FRONTEND=noninteractive

# Устанавливаем системные зависимости
# Важно: Добавляем PPA (архив пакетов) для установки свежей версии Python 3.12, как у вас
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y \
    python3.12 \
    python3.12-pip \
    python3.12-venv \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Создаем символическую ссылку, чтобы команда `python3` указывала на `python3.12`
RUN ln -s /usr/bin/python3.12 /usr/bin/python3 && \
    ln -s /usr/bin/pip3.12 /usr/bin/pip3

# Устанавливаем рабочую директорию в контейнере
WORKDIR /app

# Копируем файл с зависимостями
COPY requirements.txt .

# Устанавливаем все Python-библиотеки из вашего файла.
# Это гарантирует точное совпадение версий.
RUN pip3 install --no-cache-dir --upgrade pip
RUN pip3 install --no-cache-dir -r requirements.txt

# Копируем скрипты в контейнер
COPY scripts/ /app/scripts/
COPY run.sh .

# Делаем скрипт-оркестратор исполняемым
RUN chmod +x run.sh

# Точка входа. Эта команда будет выполняться при запуске контейнера.
ENTRYPOINT ["./run.sh"]