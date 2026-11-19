import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import ADMIN_BOT_TOKEN
from database import init_db
from admin import admin_router

logging.basicConfig(level=logging.INFO)
bot = Bot(token=ADMIN_BOT_TOKEN)
dp = Dispatcher()
dp.include_router(admin_router)

async def main():
    await init_db()
    print("👑 Admin Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
