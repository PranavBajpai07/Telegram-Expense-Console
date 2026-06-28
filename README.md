# Personal Telegram Expense Tracker

A local-first monthly expense tracker controlled from Telegram. You text a bot, it parses the message, stores the entry in SQLite, exports `data.js`, and `dashboard.html` opens offline with a double-click.

## Setup In 5 Steps

1. Create a Telegram bot with BotFather and copy the bot token.
2. Open `config.json`, paste the token into `telegram_token`, then adjust `monthlyBudget`, `currency`, and category caps.
3. Install the only Python dependency:
   ```powershell
   python -m pip install python-telegram-bot
   ```
4. Start the bot:
   ```powershell
   python bot.py
   ```
5. Open `dashboard.html` directly from this folder. It reads `data.js` with a script tag, so no web server or internet is needed for the dashboard.

## Example Messages

```text
spent 500 on ola
swiggy 420 dinner
1.5k myntra shirt
2l sip investment
got salary 75000
refund 300 from zomato
```

## Commands

```text
/start   show quick help
/help    show examples
/total   current month spend vs budget
/undo    remove the last entry from this chat
/budget  category caps and current usage
```

## Local Files

- `expenses.sqlite3` stores all transactions locally.
- `data.js` is regenerated after every saved Telegram message and after `/undo`.
- `dashboard.html` is fully offline and uses inline SVG charts.
- `telegram_token` is never written into `data.js`.

Category keyword lists live at the top of `parser.py`, and budget caps live in `config.json`, so both are easy to swap.
