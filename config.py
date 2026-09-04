import os

# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN", "8934749824:AAGkpFAwCADGa6mhFX6Pi8RvI827tNmIPV0")

# База данных
DB_PATH = "excursion_bot.db"

# Ссылка на бота
BOT_URL = "https://t.me/TomskGoBot"

# Точка (платежи)
TOCHKA_API_TOKEN = os.getenv("TOCHKA_API_TOKEN", "")
TOCHKA_CUSTOMER_CODE = "301511177"
TOCHKA_MERCHANT_ID = "200000000041437"
TOCHKA_CLIENT_ID = os.getenv("TOCHKA_CLIENT_ID", "2b517cb5ba55a0ab3d5b4a07374667ce")
