# ============================================
# bot.py — Main Telegram Bot Logic
# ============================================
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters,
)
from telegram.constants import ParseMode

import database as db
import reports
from parser import parse_expense, format_amount
from config import BOT_TOKEN, CURRENCY, FREE_TIER_LIMIT

# ── Logging ───────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

# ── Helpers ───────────────────────────────
def _user(update: Update):
    return update.effective_user

def _ensure(update: Update):
    u = _user(update)
    db.ensure_user(u.id, u.username or "", u.first_name or "")

async def _reply(update: Update, text: str, **kwargs):
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, **kwargs)

def _over_limit(user_id: int) -> bool:
    if db.is_premium(user_id):
        return False
    return db.get_monthly_entry_count(user_id) >= FREE_TIER_LIMIT

# ── /start ────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure(update)
    u = _user(update)
    text = (
        f"👋 Hey *{u.first_name}*! Welcome to *ExpenseBot* 💸\n\n"
        "I help you track your daily spending super easily.\n\n"
        "*How to log an expense:*\n"
        "Just type it naturally:\n"
        "`Coffee 3.50`\n"
        "`Lunch 12`\n"
        "`Uber ride 8.75`\n\n"
        "*Commands:*\n"
        "/today — Today's expenses\n"
        "/week — Last 7 days + chart\n"
        "/month — This month's summary\n"
        "/budget — Set a monthly budget\n"
        "/undo — Delete last entry\n"
        "/export — Export CSV _(Premium)_\n"
        "/premium — Upgrade info\n"
        "/help — Show this message\n\n"
        "Let's go! Log your first expense 👆"
    )
    await _reply(update, text)

# ── /help ─────────────────────────────────
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)

# ── /today ────────────────────────────────
async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure(update)
    uid      = _user(update).id
    expenses = db.get_expenses_today(uid)
    summary  = reports.build_today_summary(expenses)
    await _reply(update, summary)

# ── /week ─────────────────────────────────
async def cmd_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure(update)
    uid          = _user(update).id
    expenses     = db.get_expenses_week(uid)
    daily_totals = db.get_daily_totals_week(uid)
    summary      = reports.build_week_summary(expenses, daily_totals)
    await _reply(update, summary)

    # Send bar chart
    chart = reports.make_bar_chart(daily_totals)
    if chart:
        await update.message.reply_photo(photo=chart, caption="📊 Daily spending — last 7 days")

# ── /month ────────────────────────────────
async def cmd_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure(update)
    uid             = _user(update).id
    expenses        = db.get_expenses_month(uid)
    category_totals = db.get_category_totals_month(uid)
    budget          = db.get_budget(uid)
    summary         = reports.build_month_summary(expenses, category_totals, budget)
    await _reply(update, summary)

    # Send pie chart
    month_label = datetime.now().strftime("%B %Y")
    chart       = reports.make_pie_chart(category_totals, month_label)
    if chart:
        await update.message.reply_photo(photo=chart, caption=f"🥧 {month_label} breakdown")

# ── /budget ───────────────────────────────
async def cmd_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure(update)
    uid = _user(update).id

    if not context.args:
        current = db.get_budget(uid)
        if current > 0:
            spent     = db.get_month_total(uid)
            remaining = current - spent
            status    = "✅ On track" if remaining >= 0 else "⚠️ Over budget!"
            await _reply(update,
                f"🎯 *Monthly Budget:* {format_amount(current, CURRENCY)}\n"
                f"💸 *Spent:* {format_amount(spent, CURRENCY)}\n"
                f"💰 *Remaining:* {format_amount(remaining, CURRENCY)}\n"
                f"{status}\n\n"
                f"To change it: `/budget 500`"
            )
        else:
            await _reply(update, "🎯 No budget set.\n\nUse `/budget 500` to set a $500 monthly limit.")
        return

    try:
        amount = float(context.args[0].replace(",", "."))
        if amount <= 0:
            raise ValueError
        db.set_budget(uid, amount)
        await _reply(update, f"✅ Monthly budget set to *{format_amount(amount, CURRENCY)}*!\nI'll warn you when you're getting close.")
    except (ValueError, IndexError):
        await _reply(update, "❌ Invalid amount. Example: `/budget 500`")

# ── /undo ─────────────────────────────────
async def cmd_undo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure(update)
    uid     = _user(update).id
    deleted = db.delete_last_expense(uid)
    if deleted:
        await _reply(update,
            f"🗑️ Deleted:\n"
            f"  {deleted['category']}  *{deleted['description'].title()}* — "
            f"*{format_amount(deleted['amount'], CURRENCY)}*"
        )
    else:
        await _reply(update, "📭 Nothing to undo — no expenses found.")

# ── /export (Premium) ─────────────────────
async def cmd_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure(update)
    uid = _user(update).id

    if not db.is_premium(uid):
        keyboard = [[InlineKeyboardButton("⭐ Upgrade to Premium", callback_data="premium_info")]]
        await update.message.reply_text(
            "⭐ *CSV Export is a Premium feature.*\n\n"
            "Upgrade to get:\n"
            "• Unlimited entries\n"
            "• CSV/Excel export\n"
            "• Priority support",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    expenses = db.get_expenses_month(uid)
    if not expenses:
        await _reply(update, "📭 No expenses this month to export.")
        return

    csv_buf   = reports.export_to_csv(expenses)
    filename  = f"expenses_{datetime.now().strftime('%Y_%m')}.csv"
    await update.message.reply_document(
        document=csv_buf,
        filename=filename,
        caption=f"📎 Your expenses for {datetime.now().strftime('%B %Y')}",
    )

# ── /premium ──────────────────────────────
async def cmd_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure(update)
    uid = _user(update).id
    if db.is_premium(uid):
        await _reply(update, "⭐ You already have *Premium* access!\n\nEnjoy unlimited entries, charts & CSV exports.")
        return

    count = db.get_monthly_entry_count(uid)
    await _reply(update,
        f"⭐ *ExpenseBot Premium*\n\n"
        f"*Free plan:* {count}/{FREE_TIER_LIMIT} entries used this month\n\n"
        f"*Premium — $3/month:*\n"
        f"  ✅ Unlimited entries\n"
        f"  ✅ CSV/Excel export\n"
        f"  ✅ Advanced charts\n"
        f"  ✅ Multi-currency\n\n"
        f"Contact @YourUsername to upgrade."
    )

# ── Free-text expense handler ─────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure(update)
    uid  = _user(update).id
    text = update.message.text.strip()

    parsed = parse_expense(text)
    if not parsed:
        await _reply(update,
            "🤔 I didn't understand that.\n\n"
            "Try: `Coffee 3.50` or `Lunch 12`\n"
            "Type /help for all commands."
        )
        return

    # Free-tier limit check
    if _over_limit(uid):
        keyboard = [[InlineKeyboardButton("⭐ Upgrade to Premium", callback_data="premium_info")]]
        await update.message.reply_text(
            f"⚠️ *Free limit reached!*\n\n"
            f"You've used all {FREE_TIER_LIMIT} entries for this month.\n"
            f"Upgrade to Premium for unlimited tracking.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # Save expense
    db.add_expense(uid, parsed["category"], parsed["description"], parsed["amount"])
    month_total = db.get_month_total(uid)
    budget      = db.get_budget(uid)

    # Base confirmation
    response = (
        f"✅ *{parsed['description'].title()}* logged!\n"
        f"{parsed['category']}  |  *{format_amount(parsed['amount'], CURRENCY)}*\n"
        f"Month total: {format_amount(month_total, CURRENCY)}"
    )

    # Budget warning
    if budget > 0:
        pct = month_total / budget
        if pct >= 1.0:
            response += f"\n\n⚠️ *Budget exceeded!* You're {format_amount(month_total - budget, CURRENCY)} over your {format_amount(budget, CURRENCY)} limit."
        elif pct >= 0.8:
            response += f"\n\n🟡 *Heads up!* You've used {pct*100:.0f}% of your monthly budget."

    await _reply(update, response)

# ── Callback Queries ─────────────────────
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "premium_info":
        await query.message.reply_text(
            "⭐ *ExpenseBot Premium — $3/month*\n\n"
            "• Unlimited entries\n"
            "• CSV export\n"
            "• Advanced charts\n\n"
            "Contact @YourUsername to upgrade.",
            parse_mode=ParseMode.MARKDOWN,
        )

# ── Main ──────────────────────────────────
def main():
    db.init_db()
    log.info("Database initialized ✅")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("help",    cmd_help))
    app.add_handler(CommandHandler("today",   cmd_today))
    app.add_handler(CommandHandler("week",    cmd_week))
    app.add_handler(CommandHandler("month",   cmd_month))
    app.add_handler(CommandHandler("budget",  cmd_budget))
    app.add_handler(CommandHandler("undo",    cmd_undo))
    app.add_handler(CommandHandler("export",  cmd_export))
    app.add_handler(CommandHandler("premium", cmd_premium))
    app.add_handler(CommandHandler("add",     handle_message))   # /add Coffee 3.50

    # Free-text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Button callbacks
    app.add_handler(CallbackQueryHandler(handle_callback))

    log.info("Bot is running 🚀")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
