from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

router = Router()


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer("Доступные команды:\n/start - начать\n/history - история\n/cancel - отмена")


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено")
