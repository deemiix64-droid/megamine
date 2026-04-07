import os
import json
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import WebAppInfo

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8239542728  # ВАШ ЧИСЛОВОЙ ID
APP_URL = "https://your-site.github.io" # Ссылка на ваш index.html

bot = Bot(token=TOKEN)
dp = Dispatcher()

# База данных (в памяти - сбросится при перезапуске Railway)
players_db = {} # { "Ник": ID_пользователя }
current_news = "Добро пожаловать на сервер MegaMine! Мы скоро открываемся."

# --- КЛАВИАТУРЫ ---

def main_kb():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="💎 Открыть MegaMine App", web_app=WebAppInfo(url=APP_URL)))
    builder.row(types.InlineKeyboardButton(text="📝 Подать заявку", callback_data="apply"))
    builder.row(types.InlineKeyboardButton(text="📢 Новости", callback_data="view_news"))
    builder.row(types.InlineKeyboardButton(text="👥 Игроки", callback_data="list_players"))
    builder.row(types.InlineKeyboardButton(text="⚠️ Жалоба", callback_data="report"))
    return builder.as_markup()

# --- ОБРАБОТЧИКИ КОМАНД ---

@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "👋 Привет! Ты в боте сервера **MegaMine**.\nИспользуй кнопку ниже, чтобы открыть приложение:", 
        reply_markup=main_kb()
    )

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("🛠 Вы вошли в панель администратора.")

@dp.message(Command("del"))
async def delete_by_nick(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        args = message.text.split(maxsplit=1)
        if len(args) < 2: 
            return await message.reply("Использование: `/del Ник` (например /del Steve)")
        
        target_nick = args[1].strip()
        # Поиск ID по нику (регистронезависимо)
        found_id = next((uid for nick, uid in players_db.items() if nick.lower() == target_nick.lower()), None)

        if found_id:
            real_nick = [n for n in players_db if n.lower() == target_nick.lower()][0]
            del players_db[real_nick]
            try:
                await bot.send_message(found_id, f"🚫 Ваш аккаунт **{real_nick}** удален из системы MegaMine.")
            except: pass
            await message.reply(f"✅ Игрок **{real_nick}** успешно удален.")
        else:
            await message.reply("❌ Игрок с таким ником не найден в базе.")

# --- ОБРАБОТКА ДАННЫХ ИЗ MINI APP ---

@dp.message(F.web_app_data)
async def handle_app_data(message: types.Message):
    global current_news
    data = json.loads(message.web_app_data.data)
    mid = message.from_user.id

    if data['type'] == 'apply':
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_{mid}"))
        builder.row(types.InlineKeyboardButton(text="❌ Отказ", callback_data=f"reject_{mid}"))
        
        msg_text = f"📩 **ЗАЯВКА (App)**\nЗаявка: {data['nick']} | {data['reason']}\nОт: @{message.from_user.username or mid}"
        await bot.send_message(ADMIN_ID, msg_text, reply_markup=builder.as_markup())
        await message.answer("✅ Ваша заявка отправлена через приложение!")

    elif data['type'] == 'edit_news' and mid == ADMIN_ID:
        current_news = data['text']
        await message.answer("✅ Новости успешно обновлены через приложение!")

    elif data['type'] == 'broadcast' and mid == ADMIN_ID:
        count = 0
        for p_id in players_db.values():
            try:
                await bot.send_message(p_id, f"📢 **Объявление MegaMine:**\n\n{data['text']}")
                count += 1
            except: pass
        await message.answer(f"🚀 Рассылка завершена. Получили: {count} чел.")

# --- КНОПКИ СООБЩЕНИЙ (CALLBACKS) ---

@dp.callback_query()
async def query_handler(call: types.CallbackQuery):
    global current_news
    if call.data == "view_news":
        await call.message.answer(f"📰 **НОВОСТИ MEGAMINE:**\n\n{current_news}")
    elif call.data == "list_players":
        names = "\n".join([f"• {n}" for n in players_db.keys()]) if players_db else "Список пуст"
        await call.message.answer(f"👥 **Игроки на сервере:**\n\n{names}")
    elif call.data == "apply":
        await call.message.answer("Пришлите сообщение в формате:\n`Заявка: Ник | Почему к нам` ")
    elif call.data == "report":
        await call.message.answer("Пришлите сообщение в формате:\n`Жалоба: Ник | Суть проблемы` ")
    
    elif call.data.startswith("accept_"):
        target_id = int(call.data.split("_")[1])
        try:
            # Парсинг ника из текста сообщения админа
            raw_line = call.message.text.split("\n")[1]
            nick = raw_line.split(":")[1].split("|")[0].strip()
            players_db[nick] = target_id
            await bot.send_message(target_id, f"🎉 Одобрено! Твой ник **{nick}** добавлен в WhiteList.")
            await call.message.edit_text(call.message.text + f"\n\n✅ ОДОБРЕНО ({nick})")
        except:
            await call.message.answer("❌ Ошибка: не удалось вырезать ник.")

    elif call.data.startswith("reject_"):
        target_id = call.data.split("_")[1]
        await bot.send_message(target_id, "❌ К сожалению, ваша заявка была отклонена.")
        await call.message.edit_text(call.message.text + "\n\n❌ ОТКЛОНЕНО")
    
    await call.answer()

# --- ОБРАБОТКА ТЕКСТОВЫХ ФОРМ (РАССЫЛКА, НОВОСТИ И Т.Д.) ---

@dp.message()
async def text_handler(message: types.Message):
    global current_news
    text = message.text
    mid = message.from_user.id

    # Админ-команды через текст
    if mid == ADMIN_ID:
        if text.startswith("НОВОСТЬ:"):
            current_news = text.replace("НОВОСТЬ:", "").strip()
            return await message.reply("✅ Новости обновлены.")
        
        if text.startswith("РАССЫЛКА:"):
            msg = text.replace("РАССЫЛКА:", "").strip()
            for p_id in players_db.values():
                try: await bot.send_message(p_id, f"📢 **Объявление:**\n{msg}")
                except: pass
            return await message.reply("✅ Рассылка завершена.")
        
        if text.startswith("ОТКАЗ:"):
            try:
                _, t_id, reason = text.split(":", 2)
                await bot.send_message(t_id, f"❌ Отказ. Причина: {reason}")
                return await message.reply("Игрок уведомлен.")
            except: pass

    # Формы от пользователей
    prefixes = ("Заявка:", "Жалоба:", "Изменение:", "Удаление:")
    if text.startswith(prefixes):
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_{mid}"))
        builder.row(types.InlineKeyboardButton(text="❌ Отказ", callback_data=f"reject_{mid}"))
        
        await bot.send_message(
            ADMIN_ID, 
            f"📩 **НОВОЕ УВЕДОМЛЕНИЕ**\n{text}\n\nОт: @{message.from_user.username or mid}", 
            reply_markup=builder.as_markup()
        )
        await message.reply("📡 Ваше сообщение отправлено администрации!")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
