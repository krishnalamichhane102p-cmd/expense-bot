# ============================================
# database.py — PostgreSQL Operations (Railway + Supabase)
# Uses psycopg2 with a connection pool.
# SSL mode is configurable via DB_SSL_MODE env var:
#   "require" → Supabase (default)
#   "prefer"  → Railway built-in PostgreSQL plugin
# ============================================
import psycopg2
import psycopg2.pool
import psycopg2.extras   # RealDictCursor — returns rows as dicts
from contextlib import contextmanager
from datetime import date
from config import DATABASE_URL, DB_SSL_MODE

# ── Connection Pool ───────────────────────
# Min 1, max 10 connections — fits Railway free tier limits.
_pool = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    dsn=DATABASE_URL,
    sslmode=DB_SSL_MODE,      # Configurable: "require" for Supabase, "prefer" for Railway PG
    cursor_factory=psycopg2.extras.RealDictCursor,
)

@contextmanager
def get_cursor():
    """Yield a cursor; auto-commit on success, rollback on error."""
    conn = _pool.getconn()
    try:
        with conn:
            with conn.cursor() as cur:
                yield cur
    finally:
        _pool.putconn(conn)


# ── Setup ─────────────────────────────────
def init_db():
    """Create tables if they don't exist. Safe to call on every startup."""
    with get_cursor() as cur:

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     BIGINT PRIMARY KEY,
                username    TEXT,
                first_name  TEXT,
                is_premium  BOOLEAN DEFAULT FALSE,
                joined_at   TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id          BIGSERIAL PRIMARY KEY,
                user_id     BIGINT NOT NULL REFERENCES users(user_id),
                category    TEXT NOT NULL,
                description TEXT NOT NULL,
                amount      NUMERIC(12, 2) NOT NULL,
                date        DATE NOT NULL,
                created_at  TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_expenses_user_date
            ON expenses (user_id, date)
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                user_id     BIGINT PRIMARY KEY REFERENCES users(user_id),
                monthly     NUMERIC(12, 2) DEFAULT 0
            )
        """)


# ── Users ─────────────────────────────────
def ensure_user(user_id: int, username: str, first_name: str):
    """Register user if not already present."""
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO users (user_id, username, first_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id) DO NOTHING
        """, (user_id, username, first_name))


def is_premium(user_id: int) -> bool:
    with get_cursor() as cur:
        cur.execute("SELECT is_premium FROM users WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        return bool(row["is_premium"]) if row else False


def set_premium(user_id: int, status: bool):
    with get_cursor() as cur:
        cur.execute(
            "UPDATE users SET is_premium = %s WHERE user_id = %s",
            (status, user_id)
        )


# ── Expenses ──────────────────────────────
def add_expense(user_id: int, category: str, description: str, amount: float) -> int:
    """Insert a new expense. Returns the new row id."""
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO expenses (user_id, category, description, amount, date)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (user_id, category, description, amount, date.today()))
        return cur.fetchone()["id"]


def delete_last_expense(user_id: int) -> dict | None:
    """Delete the most recent expense and return it, or None."""
    with get_cursor() as cur:
        cur.execute("""
            DELETE FROM expenses
            WHERE id = (
                SELECT id FROM expenses
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            )
            RETURNING *
        """, (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def delete_expense_by_id(user_id: int, expense_id: int) -> bool:
    with get_cursor() as cur:
        cur.execute(
            "DELETE FROM expenses WHERE id = %s AND user_id = %s",
            (expense_id, user_id)
        )
        return cur.rowcount > 0


def get_expenses_today(user_id: int) -> list[dict]:
    with get_cursor() as cur:
        cur.execute("""
            SELECT * FROM expenses
            WHERE user_id = %s AND date = CURRENT_DATE
            ORDER BY created_at DESC
        """, (user_id,))
        return [dict(r) for r in cur.fetchall()]


def get_expenses_week(user_id: int) -> list[dict]:
    with get_cursor() as cur:
        cur.execute("""
            SELECT * FROM expenses
            WHERE user_id = %s
              AND date >= CURRENT_DATE - INTERVAL '6 days'
            ORDER BY date DESC, created_at DESC
        """, (user_id,))
        return [dict(r) for r in cur.fetchall()]


def get_expenses_month(user_id: int) -> list[dict]:
    with get_cursor() as cur:
        cur.execute("""
            SELECT * FROM expenses
            WHERE user_id = %s
              AND TO_CHAR(date, 'YYYY-MM') = TO_CHAR(CURRENT_DATE, 'YYYY-MM')
            ORDER BY date DESC, created_at DESC
        """, (user_id,))
        return [dict(r) for r in cur.fetchall()]


def get_monthly_entry_count(user_id: int) -> int:
    with get_cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) AS cnt FROM expenses
            WHERE user_id = %s
              AND TO_CHAR(date, 'YYYY-MM') = TO_CHAR(CURRENT_DATE, 'YYYY-MM')
        """, (user_id,))
        row = cur.fetchone()
        return int(row["cnt"]) if row else 0


def get_category_totals_month(user_id: int) -> list[dict]:
    with get_cursor() as cur:
        cur.execute("""
            SELECT category, SUM(amount) AS total FROM expenses
            WHERE user_id = %s
              AND TO_CHAR(date, 'YYYY-MM') = TO_CHAR(CURRENT_DATE, 'YYYY-MM')
            GROUP BY category
            ORDER BY total DESC
        """, (user_id,))
        return [dict(r) for r in cur.fetchall()]


def get_daily_totals_week(user_id: int) -> list[dict]:
    with get_cursor() as cur:
        cur.execute("""
            SELECT date::text AS date, SUM(amount) AS total FROM expenses
            WHERE user_id = %s
              AND date >= CURRENT_DATE - INTERVAL '6 days'
            GROUP BY date
            ORDER BY date ASC
        """, (user_id,))
        return [dict(r) for r in cur.fetchall()]


# ── Budgets ───────────────────────────────
def set_budget(user_id: int, monthly: float):
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO budgets (user_id, monthly) VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET monthly = EXCLUDED.monthly
        """, (user_id, monthly))


def get_budget(user_id: int) -> float:
    with get_cursor() as cur:
        cur.execute("SELECT monthly FROM budgets WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        return float(row["monthly"]) if row else 0.0


def get_month_total(user_id: int) -> float:
    return sum(float(r["amount"]) for r in get_expenses_month(user_id))
