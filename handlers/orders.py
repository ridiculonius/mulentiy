from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from services.analytics import sum_unconfirmed_rubles
from services.money import format_money

router = Router()

class OrdersSum(StatesGroup):
    text = State()

@router.message(F.text == "🧾 Сумма заказов")
async def orders_sum_start(message: Message, state: FSMContext):
    await state.set_state(OrdersSum.text)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="orders:cancel")]]
    )
    await message.answer("Вставь текст с заказами, я посчитаю сумму в рублях.", reply_markup=kb)

@router.message(OrdersSum.text)
async def orders_sum_process(message: Message, state: FSMContext):
    total = sum_unconfirmed_rubles(message.text)
    await message.answer(f"Сумма заказов: {format_money(total)} ₽")
    await state.clear()

@router.callback_query(F.data == "orders:cancel")
async def orders_sum_cancel(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text("Операция отменена.")
    await state.clear()
    await cb.answer()
