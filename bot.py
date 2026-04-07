import logging
import sqlite3
import os
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import WebAppInfo

# Настройки (Токен берем из переменных Railway)
API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = 8239542728  # ЗАМЕНИ НА СВОЙ ID (цифрами)
DB_PATH = "data/server.db"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode="MarkdownV2")
dp = Dispatcher()

# Инициализация БД
if not os.path.exists("data"): os.makedirs("data")

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, status TEXT)')
        cursor.execute('CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, text TEXT)')
        conn.commit()

init_db()

# Главная клавиатура
def main_kb(user_id):
    builder = ReplyKeyboardBuilder()
    builder.button(text="📝 Подать заявку")
    builder.button(text="👥 Игроки")
    builder.button(text="👤 Мой аккаунт")
    builder.button(text="📢 Новости")
    builder.button(text="🚫 Жалоба")
    # Твоя ссылка на GitHub Pages
    builder.button(text="🌐 Mini App", web_app=WebAppInfo(url="https://deemiix64-droid.github.io/metro/"))
    
    if user_id == ADMIN_ID:
        builder.button(text="⚙️ Админ Панель")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("👋 Привет\! Добро пожаловать на сервер\.", reply_markup=main_kb(message.from_user.id))

# Обработка данных из Mini App
@dp.message(F.web_app_data)
async def web_app_receive(message: types.Message):
    data = json.loads(message.web_app_data.data)
    action = data.get("action")
    
    if action == "report":
        text = data.get("text").replace(".", "\\.")
        await message.answer(f"✅ Жалоба принята: _{text}_")
        await bot.send_message(ADMIN_ID, f"⚠️ *Новая жалоба:* {text}")

@dp.message(F.text == "⚙️ Админ Панель")
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    builder = InlineKeyboardBuilder()
    builder.button(text="🔍 Проверка на читы", callback_data="check_cheats")
    builder.button(text="📥 Заявки", callback_data="view_apps")
    builder.button(text="⚠️ Жалобы", callback_data="view_reports")
    builder.adjust(1)
    await message.answer("🛠 *Панель управления*", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "check_cheats")
async def check_cheats_call(callback: types.CallbackQuery):
    await bot.send_message(callback.message.chat.id, "📢 *РАССЫЛКА:* Игрок вызван на проверку читов\! Срочно отпишите админу\.")
    await callback.answer("Рассылка отправлена")

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
