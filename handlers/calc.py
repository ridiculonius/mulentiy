from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from decimal import Decimal
from datetime import date

from services.money import parse_money, format_money, calc_intermediate, calc_final
from models.db import Database
from handlers.history import AddHistory

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
    await state.clear()
    last = await db.get_last_values(message.from_user.id)
    await state.update_data(last=last)
    await state.set_state(Calc.site)
    await ask_amount(
        message,
        "site",
        "💳 Сколько рублей на сайте?",
        last.get("site"),
    )


async def ask_amount(target: Message | CallbackQuery, field: str, question: str, last_value):
    buttons = []
    if last_value is not None:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"Использовать прошлое ({format_money(Decimal(str(last_value)))})",
                    callback_data=f"calc:last:{field}",
                )
            ]
        )
    buttons.append([InlineKeyboardButton(text="❌ Прервать", callback_data="calc:cancel")])
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    if isinstance(target, Message):
        await target.answer(question, reply_markup=markup)
    else:
        await target.message.answer(question, reply_markup=markup)


@router.message(Calc.site)
async def get_site(message: Message, state: FSMContext):
    try:
        site = parse_money(message.text)
    except Exception:
        await message.answer("Похоже, это не похоже на сумму. Введи число, например: 1234.56 или 1 234,56")
        return
    await state.update_data(site=site)
    data = await state.get_data()
    await state.set_state(Calc.unconfirmed)
    await ask_amount(
        message,
        "unconfirmed",
        "💳 Сколько рублей в неподтверждённых заказах?",
        data.get("last", {}).get("unconfirmed"),
    )


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
    await cb.message.answer("Выбери действие👇", reply_markup=start_kb)


@router.callback_query(F.data == "calc:cont")
async def calc_continue(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_reply_markup()
    data = await state.get_data()
    await state.set_state(Calc.tbank)
    await ask_amount(
        cb,
        "tbank",
        "🟡 Сколько денег на Т-Банке?",
        data.get("last", {}).get("tbank"),
    )


@router.message(Calc.tbank)
async def get_tbank(message: Message, state: FSMContext):
    try:
        tbank = parse_money(message.text)
    except Exception:
        await message.answer("Похоже, это не похоже на сумму. Введи число, например: 1234.56 или 1 234,56")
        return
    await state.update_data(tbank=tbank)
    data = await state.get_data()
    await state.set_state(Calc.ozone)
    await ask_amount(
        message,
        "ozone",
        "🔵 Сколько денег на Озоне?",
        data.get("last", {}).get("ozone"),
    )


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
    last_balance = await db.get_last_balance(message.from_user.id)
    if last_balance is None:
        delta_text = "начало"
    else:
        delta_text = format_money(final - Decimal(str(last_balance)))
    await state.set_state(AddHistory.reason)
    await state.update_data(
        d=date.today().isoformat(),
        balance=float(final),
        delta_text=delta_text,
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Прервать", callback_data="calc:cancel")]]
    )
    await message.answer(
        f"Итоговый заработок за день: {format_money(final)}\nПриход: {delta_text}\nПричина траты (если есть)?",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("calc:last:"))
async def calc_use_last(cb: CallbackQuery, state: FSMContext):
    field = cb.data.split(":")[2]
    data = await state.get_data()
    last = data.get("last", {})
    value = last.get(field)
    if value is None:
        await cb.answer("Нет прошлых данных", show_alert=True)
        return
    value = Decimal(str(value))
    if field == "site":
        await state.update_data(site=value)
        await state.set_state(Calc.unconfirmed)
        await ask_amount(
            cb,
            "unconfirmed",
            "💳 Сколько рублей в неподтверждённых заказах?",
            last.get("unconfirmed"),
        )
    elif field == "unconfirmed":
        site = data.get("site")
        intermediate = calc_intermediate(site, value)
        await state.update_data(unconfirmed=value, intermediate=intermediate)
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Продолжить", callback_data="calc:cont"),
                    InlineKeyboardButton(text="❌ Прервать", callback_data="calc:cancel"),
                ]
            ]
        )
        await state.set_state(Calc.confirm)
        await cb.message.edit_text(
            f"Промежуточный результат: {format_money(intermediate)}",
            reply_markup=kb,
        )
    elif field == "tbank":
        await state.update_data(tbank=value)
        await state.set_state(Calc.ozone)
        await ask_amount(
            cb,
            "ozone",
            "🔵 Сколько денег на Озоне?",
            last.get("ozone"),
        )
    elif field == "ozone":
        intermediate = data.get("intermediate")
        tbank = data.get("tbank")
        final = calc_final(intermediate, tbank, value)
        await db.update_last_values(
            cb.from_user.id,
            site=float(data["site"]),
            unconfirmed=float(data["unconfirmed"]),
            tbank=float(tbank),
            ozone=float(value),
        )
        last_balance = await db.get_last_balance(cb.from_user.id)
        if last_balance is None:
            delta_text = "начало"
        else:
            delta_text = format_money(final - Decimal(str(last_balance)))
        await state.set_state(AddHistory.reason)
        await state.update_data(
            d=date.today().isoformat(),
            balance=float(final),
            delta_text=delta_text,
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Прервать", callback_data="calc:cancel")]]
        )
        await cb.message.edit_text(
            f"Итоговый заработок за день: {format_money(final)}\nПриход: {delta_text}\nПричина траты (если есть)?",
            reply_markup=kb,
        )
    await cb.answer()


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

