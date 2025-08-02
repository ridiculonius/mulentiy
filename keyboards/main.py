from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🚀 Начать расчёт"),
            KeyboardButton(text="📜 История"),
        ],
        [
            KeyboardButton(text="🔄 Повторить расчёт"),
            KeyboardButton(text="💾 Использовать прошлые значения"),
        ],
    ],
    resize_keyboard=True,
)
