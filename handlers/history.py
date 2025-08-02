from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from decimal import Decimal
from datetime import datetime
from typing import Any

from models.db import Database
from services.money import parse_money, format_money

router = Router()

db = Database()

MOOD_EMOJI = {"green": "🟢", "yellow": "🟡", "red": "🔴"}

PAGE_SIZE = 7


class AddHistory(StatesGroup):
    date = State()
    balance = State()
    delta = State()
    note = State()
    mood = State()


class EditHistory(StatesGroup):
    value = State()


def history_kb(records, page: int, total: int):
    rows = []
    for idx, r in enumerate(records, start=1):
        rows.append([
            InlineKeyboardButton(
                text=str(idx), callback_data=f"hist:view:{r['id']}:{page}"
            )
        ])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Пред.", callback_data=f"hist:page:{page-1}"))
    if (page + 1) * PAGE_SIZE < total:
        nav.append(InlineKeyboardButton(text="След. ▶️", callback_data=f"hist:page:{page+1}"))
    nav.append(InlineKeyboardButton(text="➕ Добавить", callback_data="hist:add"))
    rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(Command("history"))
@router.message(F.text == "📜 История")
async def cmd_history(message: Message, state: FSMContext):
    await state.clear()
    total = await db.count_history(message.from_user.id)
    records = await db.list_history(message.from_user.id, 0, PAGE_SIZE)
    text = make_history_list(records)
    await message.answer(text, reply_markup=history_kb(records, 0, total))


def make_history_list(records):
    if not records:
        return "История пуста"
    lines = []
    for idx, r in enumerate(records, start=1):
        mood = MOOD_EMOJI.get(r["mood"], "")
        balance = format_money(Decimal(str(r["balance"]))) if r["balance"] is not None else "-"
        delta = r["delta_text"] or "-"
        note = r["note"] or "-"
        lines.append(
            f"{idx}. {r['d']} | {balance} | Δ {delta} | {mood} | {note}"
        )
    return "\n".join(lines)


@router.callback_query(F.data.startswith("hist:page:"))
async def history_page(cb: CallbackQuery):
    page = int(cb.data.split(":")[-1])
    total = await db.count_history(cb.from_user.id)
    records = await db.list_history(cb.from_user.id, page * PAGE_SIZE, PAGE_SIZE)
    text = make_history_list(records)
    await cb.message.edit_text(text, reply_markup=history_kb(records, page, total))
    await cb.answer()


@router.callback_query(F.data == "hist:add")
async def history_add_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AddHistory.date)
    await cb.message.answer("📅 Введите дату в формате YYYY-MM-DD")
    await cb.answer()


@router.message(AddHistory.date)
async def history_add_date(message: Message, state: FSMContext):
    try:
        datetime.strptime(message.text, "%Y-%m-%d")
    except ValueError:
        await message.answer("Дата должна быть в формате YYYY-MM-DD")
        return
    await state.update_data(d=message.text)
    await state.set_state(AddHistory.balance)
    await message.answer("💰 Баланс")


@router.message(AddHistory.balance)
async def history_add_balance(message: Message, state: FSMContext):
    try:
        balance = parse_money(message.text)
    except Exception:
        await message.answer("Похоже, это не похоже на сумму. Введи число.")
        return
    await state.update_data(balance=float(balance))
    await state.set_state(AddHistory.delta)
    await message.answer("🔺 Δ (число или текст)")


@router.message(AddHistory.delta)
async def history_add_delta(message: Message, state: FSMContext):
    await state.update_data(delta_text=message.text)
    await state.set_state(AddHistory.note)
    await message.answer("📝 Заметка (можно пропустить)")


@router.message(AddHistory.note)
async def history_add_note(message: Message, state: FSMContext):
    await state.update_data(note=message.text)
    await state.set_state(AddHistory.mood)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🟢", callback_data="mood:green"), InlineKeyboardButton(text="🟡", callback_data="mood:yellow"), InlineKeyboardButton(text="🔴", callback_data="mood:red")]])
    await message.answer("Выберите настроение", reply_markup=kb)


@router.callback_query(F.data.startswith("mood:"))
async def history_add_mood(cb: CallbackQuery, state: FSMContext):
    mood = cb.data.split(":")[1]
    data = await state.get_data()
    await db.add_history(
        cb.from_user.id,
        data["d"],
        data["balance"],
        data["delta_text"],
        data["note"],
        mood,
    )
    await state.clear()
    await cb.message.edit_text("Запись добавлена")
    await cb.answer()


def make_history_card(r):
    balance = (
        format_money(Decimal(str(r["balance"]))) if r["balance"] is not None else "-"
    )
    delta = r["delta_text"] or "-"
    note = r["note"] or "-"
    mood = MOOD_EMOJI.get(r["mood"], "")
    return (
        f"📅 Дата: {r['d']}\n"
        f"💰 Баланс: {balance}\n"
        f"🔺 Δ: {delta}\n"
        f"📝 Заметка: {note}\n"
        f"🙂 Настроение: {mood}"
    )


@router.callback_query(F.data.startswith("hist:view:"))
async def history_view(cb: CallbackQuery):
    _, _, rid, page = cb.data.split(":")
    record = await db.get_history(cb.from_user.id, int(rid))
    if not record:
        await cb.answer("Не найдено", show_alert=True)
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"hist:edit:{rid}:{page}")],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"hist:del:{rid}:{page}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"hist:page:{page}")],
        ]
    )
    await cb.message.edit_text(make_history_card(record), reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("hist:edit:"))
async def history_edit_menu(cb: CallbackQuery, state: FSMContext):
    _, _, rid, page = cb.data.split(":")
    await state.update_data(edit_id=int(rid), page=int(page))
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Дата", callback_data="hist:field:d")],
            [InlineKeyboardButton(text="Баланс", callback_data="hist:field:balance")],
            [InlineKeyboardButton(text="Δ", callback_data="hist:field:delta_text")],
            [InlineKeyboardButton(text="Заметка", callback_data="hist:field:note")],
            [InlineKeyboardButton(text="Настроение", callback_data="hist:field:mood")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"hist:view:{rid}:{page}")],
        ]
    )
    await cb.message.edit_text("Что редактировать?", reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("hist:field:"))
async def history_edit_field(cb: CallbackQuery, state: FSMContext):
    field = cb.data.split(":")[2]
    data = await state.get_data()
    rid = data.get("edit_id")
    page = data.get("page", 0)
    if field == "mood":
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🟢", callback_data=f"hist:setmood:green"),
                    InlineKeyboardButton(text="🟡", callback_data=f"hist:setmood:yellow"),
                    InlineKeyboardButton(text="🔴", callback_data=f"hist:setmood:red"),
                ],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"hist:edit:{rid}:{page}")],
            ]
        )
        await cb.message.edit_text("Выберите настроение", reply_markup=kb)
    else:
        prompts = {
            "d": "📅 Введите дату в формате YYYY-MM-DD",
            "balance": "💰 Баланс",
            "delta_text": "🔺 Δ (число или текст)",
            "note": "📝 Заметка (можно пусто)",
        }
        await state.update_data(field=field)
        await state.set_state(EditHistory.value)
        await cb.message.edit_text(prompts[field])
    await cb.answer()


@router.message(EditHistory.value)
async def history_edit_value(message: Message, state: FSMContext):
    data = await state.get_data()
    field = data.get("field")
    rid = data.get("edit_id")
    page = data.get("page", 0)
    value: Any
    if field == "d":
        try:
            datetime.strptime(message.text, "%Y-%m-%d")
        except ValueError:
            await message.answer("Дата должна быть в формате YYYY-MM-DD")
            return
        value = message.text
    elif field == "balance":
        try:
            value = float(parse_money(message.text))
        except Exception:
            await message.answer("Похоже, это не похоже на сумму. Введи число.")
            return
    elif field == "delta_text":
        value = message.text
    else:  # note
        value = message.text
    await db.update_history(message.from_user.id, rid, **{field: value})
    await state.set_state(None)
    record = await db.get_history(message.from_user.id, rid)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"hist:edit:{rid}:{page}")],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"hist:del:{rid}:{page}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"hist:page:{page}")],
        ]
    )
    await message.answer("Обновлено")
    await message.answer(make_history_card(record), reply_markup=kb)


@router.callback_query(F.data.startswith("hist:setmood:"))
async def history_set_mood(cb: CallbackQuery, state: FSMContext):
    mood = cb.data.split(":")[2]
    data = await state.get_data()
    rid = data.get("edit_id")
    page = data.get("page", 0)
    await db.update_history(cb.from_user.id, rid, mood=mood)
    record = await db.get_history(cb.from_user.id, rid)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"hist:edit:{rid}:{page}")],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"hist:del:{rid}:{page}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"hist:page:{page}")],
        ]
    )
    await cb.message.edit_text(make_history_card(record), reply_markup=kb)
    await cb.answer("Обновлено")


@router.callback_query(F.data.startswith("hist:del:"))
async def history_delete_prompt(cb: CallbackQuery):
    _, _, rid, page = cb.data.split(":")
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да", callback_data=f"hist:delconf:{rid}:{page}"),
                InlineKeyboardButton(text="Нет", callback_data=f"hist:view:{rid}:{page}"),
            ]
        ]
    )
    await cb.message.edit_text("Удалить запись?", reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("hist:delconf:"))
async def history_delete_confirm(cb: CallbackQuery):
    _, _, rid, page = cb.data.split(":")
    await db.delete_history(cb.from_user.id, int(rid))
    total = await db.count_history(cb.from_user.id)
    page = int(page)
    if page * PAGE_SIZE >= total and page > 0:
        page -= 1
    records = await db.list_history(cb.from_user.id, page * PAGE_SIZE, PAGE_SIZE)
    text = make_history_list(records)
    await cb.message.edit_text(text, reply_markup=history_kb(records, page, total))
    await cb.answer("Удалено")

