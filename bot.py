import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import load_config
from handlers import calc, history, misc, analytics, orders


def create_dp() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(misc.router)
    dp.include_router(calc.router)
    dp.include_router(history.router)
    dp.include_router(analytics.router)
    dp.include_router(orders.router)
    return dp


async def main():
    config = load_config()
    bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = create_dp()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
