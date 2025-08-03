from __future__ import annotations

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from models.db import get_balance_history
from services.plot import plot_balance_chart

router = Router()


class HistoryStates(StatesGroup):
    waiting_days = State()


@router.message(F.text == "📈 График")
async def ask_days(message: types.Message, state: FSMContext) -> None:
    """Ask user for number of days to show."""
    await state.set_state(HistoryStates.waiting_days)
    await message.answer("За сколько дней показать баланс? (по умолчанию 30)")


@router.message(HistoryStates.waiting_days)
async def send_chart(message: types.Message, state: FSMContext) -> None:
    """Generate chart and send it to the user."""
    await state.clear()
    try:
        days = int(message.text)
    except (TypeError, ValueError):
        days = 30

    points = get_balance_history(message.from_user.id, days)
    if not points:
        await message.answer("Нет данных для построения графика.")
        return

    image = plot_balance_chart(points)
    await message.answer_photo(
        types.BufferedInputFile(image.getvalue(), filename="balance.png")
    )
