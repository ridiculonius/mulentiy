from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from models.db import Database
from services.analytics import plot_mood_pie, plot_monthly_chart, MOOD_EMOJI

router = Router()
db = Database()


@router.message(Command("analytics"))
@router.message(F.text == "📊 Аналитика")
async def cmd_analytics(message: Message):
    mood_stats = await db.get_mood_stats(message.from_user.id)
    month_points = await db.get_monthly_balances(message.from_user.id)
    total = sum(mood_stats.values())
    lines = [f"Всего записей: {total}"]
    for mood, count in mood_stats.items():
        emoji = MOOD_EMOJI.get(mood, mood)
        lines.append(f"{emoji} {count}")
    await message.answer("\n".join(lines))
    if month_points:
        buf1 = plot_monthly_chart(month_points)
        await message.answer_photo(buf1, caption="Баланс по месяцам")
    if mood_stats:
        buf2 = plot_mood_pie(mood_stats)
        await message.answer_photo(buf2, caption="Настроение")
