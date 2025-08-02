from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from decimal import Decimal

from services.money import parse_money, format_money, calc_intermediate, calc_final
from models.db import Database

router = Router()

db = Database()


class Calc(StatesGroup):
    site = State()
    unconfirmed = State()
    confirm = State()
    tbank = State()
    ozone = State()


class EditLast(StatesGroup):
    input = State()


start_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🚀 Начать расчёт")]],
    resize_keyboard=True,
)


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет! Я помогу посчитать заработок за день и вести историю. Выбери действие👇",
        reply_markup=start_kb,
    )


@router.message(F.text == "🚀 Начать расчёт")
async def start_calc(message: Message, state: FSMContext):
    await state.set_state(Calc.site)
    await message.answer("💳 Сколько рублей на сайте?")


@router.message(Calc.site)
async def get_site(message: Message, state: FSMContext):
    try:
        site = parse_money(message.text)
    except Exception:
        await message.answer("Похоже, это не похоже на сумму. Введи число, например: 1234.56 или 1 234,56")
        return
    await state.update_data(site=site)
    await state.set_state(Calc.unconfirmed)
    await message.answer("💳 Сколько рублей в неподтверждённых заказах?")


@router.message(Calc.unconfirmed)
async def get_unconfirmed(message: Message, state: FSMContext):
    try:
        unconfirmed = parse_money(message.text)
    except Exception:
        await message.answer("Похоже, это не похоже на сумму. Введи число, например: 1234.56 или 1 234,56")
        return
    data = await state.get_data()
    site = data.get("site")
    intermediate = calc_intermediate(site, unconfirmed)
    await state.update_data(unconfirmed=unconfirmed, intermediate=intermediate)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Продолжить", callback_data="calc:cont"),
                InlineKeyboardButton(text="❌ Прервать", callback_data="calc:cancel"),
            ]
        ]
    )
    await state.set_state(Calc.confirm)
    await message.answer(
        f"Промежуточный результат: {format_money(intermediate)}", reply_markup=kb
    )


@router.callback_query(F.data == "calc:cancel")
async def calc_cancel(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("Расчёт прерван")


@router.callback_query(F.data == "calc:cont")
async def calc_continue(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_reply_markup()
    await state.set_state(Calc.tbank)
    await cb.message.answer("🟡 Сколько денег на Т-Банке?")


@router.message(Calc.tbank)
async def get_tbank(message: Message, state: FSMContext):
    try:
        tbank = parse_money(message.text)
    except Exception:
        await message.answer("Похоже, это не похоже на сумму. Введи число, например: 1234.56 или 1 234,56")
        return
    await state.update_data(tbank=tbank)
    await state.set_state(Calc.ozone)
    await message.answer("🔵 Сколько денег на Озоне?")


@router.message(Calc.ozone)
async def get_ozone(message: Message, state: FSMContext):
    try:
        ozone = parse_money(message.text)
    except Exception:
        await message.answer("Похоже, это не похоже на сумму. Введи число, например: 1234.56 или 1 234,56")
        return
    data = await state.get_data()
    intermediate = data.get("intermediate")
    tbank = data.get("tbank")
    final = calc_final(intermediate, tbank, ozone)
    await db.update_last_values(
        message.from_user.id,
        site=float(data["site"]),
        unconfirmed=float(data["unconfirmed"]),
        tbank=float(tbank),
        ozone=float(ozone),
    )
    await state.clear()
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🔄 Повторить расчёт"),
                KeyboardButton(text="💾 Использовать прошлые значения"),
            ],
            [KeyboardButton(text="📜 История")],
        ],
        resize_keyboard=True,
    )
    await message.answer(
        f"Итоговый заработок за день: {format_money(final)}",
        reply_markup=kb,
    )


@router.message(F.text == "🔄 Повторить расчёт")
async def repeat_calc(message: Message, state: FSMContext):
    await start_calc(message, state)


@router.message(F.text == "💾 Использовать прошлые значения")
async def use_last(message: Message, state: FSMContext):
    values = await db.get_last_values(message.from_user.id)
    if any(v is None for v in values.values()):
        await message.answer("Нет сохранённых значений. Нажми '🚀 Начать расчёт'.")
        return
    values = {k: Decimal(str(v)) for k, v in values.items()}
    await state.update_data(values=values, idx=0)
    await prompt_last_field(message, state)


FIELDS = [
    ("site", "💳 Сколько рублей на сайте?"),
    ("unconfirmed", "💳 Сколько рублей в неподтверждённых заказах?"),
    ("tbank", "🟡 Сколько денег на Т-Банке?"),
    ("ozone", "🔵 Сколько денег на Озоне?"),
]


async def prompt_last_field(target: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("idx", 0)
    if idx >= len(FIELDS):
        values = data["values"]
        intermediate = calc_intermediate(values["site"], values["unconfirmed"])
        final = calc_final(intermediate, values["tbank"], values["ozone"])
        await db.update_last_values(
            target.from_user.id,
            site=float(values["site"]),
            unconfirmed=float(values["unconfirmed"]),
            tbank=float(values["tbank"]),
            ozone=float(values["ozone"]),
        )
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="🔄 Повторить расчёт"),
                    KeyboardButton(text="💾 Использовать прошлые значения"),
                ],
                [KeyboardButton(text="📜 История")],
            ],
            resize_keyboard=True,
        )
        await target.answer(
            f"Итоговый заработок за день: {format_money(final)}",
            reply_markup=kb,
        )
        await state.clear()
        return
    field, question = FIELDS[idx]
    value = data["values"][field]
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Оставить", callback_data=f"last:keep:{field}"
                ),
                InlineKeyboardButton(
                    text="Изменить", callback_data=f"last:edit:{field}"
                ),
            ]
        ]
    )
    await target.answer(
        f"{question} (сейчас: {format_money(value)})",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("last:"))
async def last_callbacks(cb: CallbackQuery, state: FSMContext):
    _, action, field = cb.data.split(":")
    data = await state.get_data()
    idx = data.get("idx", 0)
    if action == "keep":
        await state.update_data(idx=idx + 1)
        await cb.message.edit_reply_markup()
        await prompt_last_field(cb.message, state)
    else:
        await state.update_data(current_field=field)
        await state.set_state(EditLast.input)
        await cb.message.edit_text(next(q for f, q in FIELDS if f == field))
    await cb.answer()


@router.message(EditLast.input)
async def last_input(message: Message, state: FSMContext):
    data = await state.get_data()
    field = data.get("current_field")
    try:
        value = parse_money(message.text)
    except Exception:
        await message.answer(
            "Похоже, это не похоже на сумму. Введи число, например: 1234.56 или 1 234,56"
        )
        return
    values = data["values"]
    values[field] = value
    idx = data.get("idx", 0) + 1
    await state.update_data(values=values, idx=idx)
    await state.set_state(None)
    await prompt_last_field(message, state)

