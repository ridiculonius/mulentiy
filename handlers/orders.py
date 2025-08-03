from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from decimal import Decimal

from services.orders import sum_rubles_from_text
from services.money import format_money

router = Router()


class OrdersSum(StatesGroup):
    collect = State()


def orders_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Готово", callback_data="orders:done"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="orders:cancel"),
            ]
        ]
    )


@router.message(F.text == "🧾 Сумма заказов")
async def orders_sum_start(message: Message, state: FSMContext):
    await state.set_state(OrdersSum.collect)
    await state.update_data(total=Decimal("0"))
    await message.answer(
        "Вставляй текст с заказами по частям. Когда закончишь, нажми «Готово».",
        reply_markup=orders_kb(),
    )


@router.message(OrdersSum.collect)
async def orders_sum_collect(message: Message, state: FSMContext):
    part = sum_rubles_from_text(message.text)
    data = await state.get_data()
    total = data.get("total", Decimal("0")) + part
    await state.update_data(total=total)
    await message.answer(f"Сейчас сумма: {format_money(total)}", reply_markup=orders_kb())


@router.callback_query(F.data == "orders:done")
async def orders_sum_done(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    total = data.get("total", Decimal("0"))
    await cb.message.edit_text(f"Итоговая сумма заказов: {format_money(total)}")
    await state.clear()
    await cb.answer()


@router.callback_query(F.data == "orders:cancel")
async def orders_sum_cancel(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("Операция отменена.")
    await cb.answer()
