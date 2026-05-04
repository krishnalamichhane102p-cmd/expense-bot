# 💸 ExpenseBot — Telegram Expense Tracker

Track daily expenses via Telegram with charts, budgets & CSV export.
Deployed on **Railway** (free $5 credit/month) with **Supabase** PostgreSQL (free & persistent).

---

## 📁 Project Structure

```
expense-bot/
├── bot.py          # All Telegram handlers
├── database.py     # PostgreSQL via psycopg2
├── parser.py       # Smart text parser ("Coffee 3.50")
├── reports.py      # Summaries, charts, CSV export
├── config.py       # Reads all settings from env vars
├── railway.toml    # Railway build & deploy config
├── Procfile        # Tells Railway: run as background worker
└── requirements.txt
```

---

## 🚀 Full Deploy Guide

### Step 1 — Get your Telegram Bot Token

1. Open Telegram → search **@BotFather**
2. Send `/newbot` → follow the steps → copy your token
   - It looks like: `123456789:ABCdefGHI...`

---

### Step 2 — Set up Supabase (free PostgreSQL database)

1. Go to **[supabase.com](https://supabase.com)** → Sign up free
2. Click **"New Project"** → name it → set a DB password → Create
3. Wait ~1 minute for it to provision
4. Go to **Project Settings → Database**
5. Scroll to **Connection string → URI** tab → copy it
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxx.supabase.co:5432/postgres
   ```
6. Replace `[YOUR-PASSWORD]` with your actual password and save it

> ✅ Supabase free tier: 500 MB, no expiry, always-on. Your data survives Railway restarts.

---

### Step 3 — Push your code to GitHub

```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/YOUR_USERNAME/expense-bot.git
git push -u origin main
```

---

### Step 4 — Deploy on Railway

1. Go to **[railway.app](https://railway.app)** → Sign up with GitHub
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Select your `expense-bot` repo → Railway auto-detects Python ✅
4. Click your service → go to the **"Variables"** tab → add these:

   | Variable | Value |
   |---|---|
   | `BOT_TOKEN` | your token from BotFather |
   | `DATABASE_URL` | your Supabase URI from Step 2 |
   | `CURRENCY` | `$` (or `€`, `£`, `₹`) |
   | `FREE_TIER_LIMIT` | `50` |
   | `DB_SSL_MODE` | `require` ← required for Supabase |

5. Go to **"Settings"** tab → confirm Start Command is `python bot.py`
6. Railway auto-deploys — check the **"Deployments"** tab → click the latest → view logs

You'll see:
```
Database initialized ✅
Bot is running 🚀
```

---

## 🆓 Railway Free Tier Info

Railway gives **$5 free credit every month** — no credit card needed to start.

| What | Cost |
|---|---|
| 1 Python worker (your bot) | ~$0–2/month |
| RAM: 512 MB | included |
| CPU: shared | included |
| Bandwidth | included |

> ✅ A Telegram bot polling service uses very little RAM and CPU — $5/month easily covers it.

---

## 💬 Bot Commands

| Command / Input | What it does |
|---|---|
| `Coffee 3.50` | Log an expense (free text) |
| `/add Lunch 12` | Log with command prefix |
| `/today` | Today's expenses list |
| `/week` | Last 7 days + bar chart |
| `/month` | This month + pie chart |
| `/budget 500` | Set monthly budget |
| `/budget` | Check budget status |
| `/undo` | Delete last entry |
| `/export` | Download CSV _(Premium)_ |
| `/premium` | Upgrade info |
| `/help` | Show all commands |

---

## 💰 Enable Premium for a User

After someone pays, go to your **Supabase dashboard → Table Editor → users** and set `is_premium = true` for their row.

Or run this in Supabase **SQL Editor**:
```sql
UPDATE users SET is_premium = TRUE WHERE user_id = 123456789;
```

---

## 🛠 Customization

**Add your own categories** in `config.py`:
```python
"🐾 Pets": ["pet", "vet", "dog", "cat", "food"],
```

**Change currency** — set the Railway env var:
```
CURRENCY = €
```

**Raise free tier limit:**
```
FREE_TIER_LIMIT = 100
```

**Using Railway's built-in PostgreSQL instead of Supabase?**
Railway auto-sets `DATABASE_URL` when you add the PostgreSQL plugin. Just change:
```
DB_SSL_MODE = prefer
```

---

## ⚠️ Troubleshooting

| Problem | Fix |
|---|---|
| Bot not responding | Railway → Deployments → click latest → read logs |
| `KeyError: 'BOT_TOKEN'` | Variable not set — check Railway Variables tab |
| DB connection refused | Check `DATABASE_URL` is correct with password filled in |
| SSL error | Confirm `DB_SSL_MODE=require` for Supabase |
| Tables not created | `init_db()` runs on startup automatically — check logs for errors |
| Redeployment not triggering | Railway → Settings → ensure GitHub auto-deploy is ON |
