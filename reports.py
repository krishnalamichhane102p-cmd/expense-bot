# ============================================
# reports.py — Summaries, Charts & CSV Export
# ============================================
import io
import csv
import matplotlib
matplotlib.use("Agg")          # Non-interactive backend (no display needed)
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime, timedelta
from parser import format_amount
from config import CURRENCY

# ── Text Summaries ────────────────────────
def build_today_summary(expenses: list[dict]) -> str:
    if not expenses:
        return "📭 No expenses logged today yet.\n\nSend me something like:\n`Coffee 3.50` or `Lunch 12`"

    total = sum(e["amount"] for e in expenses)
    lines = [f"📅 *Today's Expenses*\n"]
    for e in expenses:
        lines.append(f"  {e['category']}  {e['description'].title()} — *{format_amount(e['amount'], CURRENCY)}*")

    lines.append(f"\n💰 *Total: {format_amount(total, CURRENCY)}*")
    return "\n".join(lines)


def build_week_summary(expenses: list[dict], daily_totals: list[dict]) -> str:
    if not expenses:
        return "📭 No expenses in the last 7 days."

    total = sum(e["amount"] for e in expenses)

    # Group by category
    cats: dict[str, float] = {}
    for e in expenses:
        cats[e["category"]] = cats.get(e["category"], 0) + e["amount"]

    lines = [f"📊 *This Week's Expenses*\n"]

    # Category breakdown
    lines.append("*By Category:*")
    for cat, amt in sorted(cats.items(), key=lambda x: -x[1]):
        pct = (amt / total) * 100
        lines.append(f"  {cat} — {format_amount(amt, CURRENCY)} ({pct:.0f}%)")

    # Daily breakdown
    lines.append("\n*By Day:*")
    for day in daily_totals:
        d = datetime.strptime(day["date"], "%Y-%m-%d")
        lines.append(f"  {d.strftime('%a %d %b')} — {format_amount(day['total'], CURRENCY)}")

    lines.append(f"\n💰 *Total: {format_amount(total, CURRENCY)}*")
    return "\n".join(lines)


def build_month_summary(expenses: list[dict], category_totals: list[dict], budget: float) -> str:
    if not expenses:
        return "📭 No expenses this month yet."

    total = sum(e["amount"] for e in expenses)
    now   = datetime.now()
    lines = [f"📆 *{now.strftime('%B %Y')} Summary*\n"]

    lines.append("*By Category:*")
    for row in category_totals:
        pct = (row["total"] / total) * 100
        lines.append(f"  {row['category']} — {format_amount(row['total'], CURRENCY)} ({pct:.0f}%)")

    lines.append(f"\n💰 *Total Spent: {format_amount(total, CURRENCY)}*")

    if budget > 0:
        remaining = budget - total
        bar = _budget_bar(total, budget)
        lines.append(f"🎯 *Budget: {format_amount(budget, CURRENCY)}*")
        lines.append(f"{bar}")
        if remaining >= 0:
            lines.append(f"✅ *Remaining: {format_amount(remaining, CURRENCY)}*")
        else:
            lines.append(f"⚠️ *Over budget by {format_amount(abs(remaining), CURRENCY)}!*")

    return "\n".join(lines)


def _budget_bar(spent: float, budget: float, width: int = 10) -> str:
    if budget == 0:
        return ""
    pct  = min(spent / budget, 1.0)
    fill = int(pct * width)
    bar  = "█" * fill + "░" * (width - fill)
    return f"[{bar}] {pct*100:.0f}%"


# ── Charts ────────────────────────────────
COLORS = [
    "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7",
    "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E9",
]

def make_pie_chart(category_totals: list[dict], month_label: str) -> io.BytesIO | None:
    """Generate a pie chart of spending by category. Returns a PNG BytesIO."""
    if not category_totals:
        return None

    labels  = [r["category"] for r in category_totals]
    amounts = [r["total"]    for r in category_totals]
    colors  = COLORS[:len(labels)]

    fig, ax = plt.subplots(figsize=(7, 5), facecolor="#1a1a2e")
    ax.set_facecolor("#1a1a2e")

    wedges, texts, autotexts = ax.pie(
        amounts,
        labels=None,
        autopct="%1.1f%%",
        colors=colors,
        startangle=140,
        pctdistance=0.82,
        wedgeprops=dict(width=0.55, edgecolor="#1a1a2e", linewidth=2),
    )

    for at in autotexts:
        at.set_color("white")
        at.set_fontsize(9)

    # Legend
    legend_labels = [f"{l}  ${a:,.2f}" for l, a in zip(labels, amounts)]
    ax.legend(
        wedges, legend_labels,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.22),
        ncol=2,
        fontsize=8,
        facecolor="#16213e",
        labelcolor="white",
        edgecolor="none",
    )

    total = sum(amounts)
    ax.text(0, 0, f"${total:,.2f}\ntotal", ha="center", va="center",
            fontsize=11, fontweight="bold", color="white")

    ax.set_title(f"💸 {month_label} Spending", color="white", fontsize=13, pad=12)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor="#1a1a2e")
    plt.close(fig)
    buf.seek(0)
    return buf


def make_bar_chart(daily_totals: list[dict]) -> io.BytesIO | None:
    """Generate a bar chart of daily spending this week."""
    if not daily_totals:
        return None

    # Fill missing days
    today = datetime.today().date()
    days  = [(today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    total_map = {r["date"]: r["total"] for r in daily_totals}
    amounts   = [total_map.get(d, 0) for d in days]
    labels    = [datetime.strptime(d, "%Y-%m-%d").strftime("%a\n%d") for d in days]

    fig, ax = plt.subplots(figsize=(7, 4), facecolor="#1a1a2e")
    ax.set_facecolor("#1a1a2e")

    bars = ax.bar(labels, amounts, color=COLORS[2], edgecolor="#1a1a2e", linewidth=1.5, width=0.6)

    # Highlight today
    bars[-1].set_color(COLORS[0])

    # Value labels on bars
    for bar, amt in zip(bars, amounts):
        if amt > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(amounts) * 0.02,
                f"${amt:.0f}",
                ha="center", va="bottom", color="white", fontsize=8,
            )

    ax.set_title("📅 Last 7 Days Spending", color="white", fontsize=13, pad=10)
    ax.tick_params(colors="white")
    ax.spines[:].set_visible(False)
    ax.yaxis.set_visible(False)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor="#1a1a2e")
    plt.close(fig)
    buf.seek(0)
    return buf


# ── CSV Export (Premium) ──────────────────
def export_to_csv(expenses: list[dict]) -> io.BytesIO:
    """Return a BytesIO CSV of the given expenses list."""
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=["id", "date", "category", "description", "amount"],
        extrasaction="ignore",
    )
    writer.writeheader()
    for e in expenses:
        writer.writerow({
            "id":          e["id"],
            "date":        e["date"],
            "category":    e["category"],
            "description": e["description"],
            "amount":      e["amount"],
        })

    bytes_buf = io.BytesIO(buf.getvalue().encode("utf-8"))
    bytes_buf.seek(0)
    return bytes_buf
