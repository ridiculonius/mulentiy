from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

main = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📈 График")]],
    resize_keyboard=True,
)
