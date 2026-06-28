"""Telegram bot entry point for the local expense tracker."""

from __future__ import annotations

from datetime import date
from typing import Any

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

import db
from export import export_data, load_config
from parser import ParseError, parse_message


HELP_TEXT = """Send expenses in plain English:
spent 500 on ola
swiggy 420 dinner
1.5k myntra shirt
got salary 75000

Commands: /total /undo /budget /help"""


def current_month() -> str:
    return date.today().strftime("%Y-%m")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Local expense tracker is ready.\n\n" + HELP_TEXT)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    config = load_config()
    chat_id = update.effective_chat.id

    try:
        parsed = parse_message(text)
    except ParseError as exc:
        await update.message.reply_text(f"{exc}\n\nTry: spent 500 on ola")
        return

    saved = db.add(parsed, chat_id=chat_id)
    export_data()
    month = saved["date"][:7]
    await update.message.reply_text(_confirmation(saved, config, month))


async def total(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config = load_config()
    await update.message.reply_text(_month_total_text(config, current_month()))


async def undo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    removed = db.undo_last(chat_id)
    if removed is None:
        await update.message.reply_text("Nothing to undo for this chat.")
        return

    export_data()
    config = load_config()
    removed_text = (
        f"Removed {removed['type']} {format_money(removed['amount'], config)} "
        f"from {removed['category']}: {removed['note']}"
    )
    await update.message.reply_text(removed_text + "\n\n" + _month_total_text(config, removed["date"][:7]))


async def budget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config = load_config()
    month = current_month()
    totals = db.category_totals(month)
    budgets = config.get("budgets", {})
    currency = config.get("currency", "₹")

    lines = [f"Category caps for {month}:"]
    for category, cap in budgets.items():
        spent = totals.get(category, 0)
        ratio = spent / cap if cap else 0
        status = "OVER" if cap and spent > cap else "OK"
        lines.append(
            f"{category}: {format_money(spent, config)} / {currency}{_indian_number(cap)} "
            f"{progress_bar(ratio, 10)} {status}"
        )
    await update.message.reply_text("\n".join(lines))


def _confirmation(row: dict[str, Any], config: dict[str, Any], month: str) -> str:
    sign = "+" if row["type"] == "income" else "-"
    return (
        f"Saved {row['type']}: {sign}{format_money(row['amount'], config)} "
        f"as {row['category']}\n"
        f"Note: {row['note']}\n\n"
        + _month_total_text(config, month)
    )


def _month_total_text(config: dict[str, Any], month: str) -> str:
    spent = db.month_total(month)
    budget_amount = float(config.get("monthlyBudget", 0) or 0)
    ratio = spent / budget_amount if budget_amount else 0
    remaining = budget_amount - spent
    status = "remaining" if remaining >= 0 else "over"
    return (
        f"{month} spend: {format_money(spent, config)} / {format_money(budget_amount, config)}\n"
        f"{progress_bar(ratio)} {ratio * 100:.0f}%\n"
        f"{format_money(abs(remaining), config)} {status}"
    )


def progress_bar(ratio: float, width: int = 18) -> str:
    safe_ratio = max(0, min(ratio, 1))
    filled = round(safe_ratio * width)
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def format_money(value: float, config: dict[str, Any]) -> str:
    currency = config.get("currency", "₹")
    return f"{currency}{_indian_number(value)}"


def _indian_number(value: float) -> str:
    sign = "-" if float(value) < 0 else ""
    rounded = round(abs(float(value)), 2)
    number = f"{rounded:.2f}".rstrip("0").rstrip(".")
    whole, _, decimal = number.partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    return sign + whole + (f".{decimal}" if decimal else "")


def main() -> None:
    config = load_config()
    token = config.get("telegram_token", "")
    if not token or "PASTE" in token:
        raise SystemExit("Add your BotFather token to config.json before running bot.py.")

    db.init_db()
    export_data()

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("total", total))
    app.add_handler(CommandHandler("undo", undo))
    app.add_handler(CommandHandler("budget", budget))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()


if __name__ == "__main__":
    main()
