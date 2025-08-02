import asyncio
from aiogram import Bot, Dispatcher
from config import load_config
from handlers import calc, history, misc


def create_dp() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(misc.router)
    dp.include_router(calc.router)
    dp.include_router(history.router)
    return dp


async def main():
    config = load_config()
    bot = Bot(token=config.bot_token, parse_mode="HTML")
    dp = create_dp()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
