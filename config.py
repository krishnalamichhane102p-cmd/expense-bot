# ============================================
# config.py — Bot Configuration
# All secrets are read from environment variables.
# Set them in Railway dashboard → your service → Variables tab.
# Never hardcode tokens or URLs in this file.
# ============================================
import os

# ── Required — set these in Railway Variables ─
BOT_TOKEN    = os.environ["8214132452:AAEy5f2iDS-d9tJbl1eQrCRR5z0bYL4D7hY"]     # From @BotFather on Telegram
DATABASE_URL = os.environ["postgresql://postgres.xahymwvyfbqxcwcjyuca:7aJeFcfSuxBtExVv@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres"]  # Auto-set if using Railway PostgreSQL plugin
                                           # OR paste your Supabase URI manually

# ── Optional — sensible defaults provided ────
FREE_TIER_LIMIT = int(os.getenv("FREE_TIER_LIMIT", "50"))
CURRENCY        = os.getenv("CURRENCY", "$")   # Change to €, £, ₹ etc. in Railway vars
DB_SSL_MODE     = os.getenv("DB_SSL_MODE", "require")
# DB_SSL_MODE:
#   "require"  → use for Supabase (default)
#   "prefer"   → use for Railway's built-in PostgreSQL plugin



# ── Category keyword mapping ───────────────
CATEGORY_KEYWORDS = {
    "🍔 Food":        ["food", "lunch", "dinner", "breakfast", "coffee", "cafe", "restaurant", "pizza", "burger", "eat", "meal", "snack", "drink", "tea", "juice", "bread", "rice", "chicken"],
    "🚗 Transport":   ["transport", "uber", "taxi", "bus", "train", "fuel", "gas", "grab", "car", "ride", "fare", "toll", "parking", "petrol"],
    "🛒 Shopping":    ["shopping", "clothes", "shirt", "shoes", "bag", "market", "store", "mall", "amazon", "online", "buy", "purchase"],
    "🏥 Health":      ["health", "medicine", "doctor", "pharmacy", "hospital", "clinic", "drug", "vitamin", "gym", "fitness"],
    "🎮 Entertainment":["entertainment", "movie", "netflix", "spotify", "game", "cinema", "concert", "event", "ticket", "fun"],
    "🏠 Bills":       ["bill", "rent", "electric", "water", "internet", "phone", "wifi", "subscription", "insurance", "tax"],
    "📚 Education":   ["education", "book", "course", "school", "tuition", "study", "class", "training"],
    "✈️ Travel":      ["travel", "hotel", "flight", "airbnb", "trip", "vacation", "holiday", "tour"],
}

DEFAULT_CATEGORY = "📦 Others"
