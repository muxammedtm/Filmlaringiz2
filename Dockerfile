# Cinema Premium Bot — BotHost uchun toza Docker image (aiogram 3.x)
FROM python:3.11-slim

WORKDIR /app

# Avval requirements (kesh uchun)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kodni ko'chiramiz
COPY . .

# Doimiy saqlanadigan papka (DB, loglar) — BotHost volume bilan moslashadi
ENV DATA_DIR=/app/data
RUN mkdir -p /app/data

# aiogram 3.x to'g'ri o'rnatilganini tekshiramiz (build paytida)
RUN python -c "from aiogram import Bot; print('aiogram OK')"

CMD ["python", "main.py"]
