# syntax=docker/dockerfile:1

# ---------- Стадия 1: сборка ----------
# Полный образ языка (не -slim/-alpine): здесь есть всё для установки зависимостей.
FROM python:3.12 AS build

WORKDIR /app

# Сначала копируем ТОЛЬКО файл зависимостей.
# Пока requirements.txt не меняется, этот слой берётся из кэша,
# и при изменении исходного кода зависимости не переустанавливаются.
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Только после установки зависимостей копируем исходный код.
COPY app ./app
COPY run.py .

# ---------- Стадия 2: рабочий образ ----------
# Компактный базовый образ: без компиляторов и dev-зависимостей.
FROM python:3.12-slim AS runtime

WORKDIR /app

# Переносим только установленные пакеты из стадии сборки.
COPY --from=build /install /usr/local

# Переносим только необходимое для запуска, а не весь build-контекст.
COPY --from=build /app/app ./app
COPY --from=build /app/run.py ./run.py

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["python", "-m", "flask", "--app", "run", "run", "--host=0.0.0.0", "--port=5000"]
