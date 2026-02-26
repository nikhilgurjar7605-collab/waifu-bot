# ── Configuration ─────────────────────────────────────────────────────────────
BOT_TOKEN = "8489556351:AAGh7iZwfEG-DB3jx9itl8y4IkMl8oCWXxU"   # 👈 Replace with your token from @BotFather

# Telegram User IDs of bot admins (can add characters, force-spawn, etc.)
ADMIN_IDS = [1214273889]             # 👈 Replace with your Telegram user ID(s)

# ── Spawn Settings ─────────────────────────────────────────────────────────────
SPAWN_CHANCE          = 0.05   # 5 % chance a character spawns after each message
SPAWN_COOLDOWN_SEC    = 120    # seconds before the same group can spawn again
CATCH_WINDOW_SEC      = 90     # seconds players have to /catch the spawned char

# ── Economy ───────────────────────────────────────────────────────────────────
DAILY_COINS           = 100
BURN_COIN_VALUE       = 10     # coins earned when burning a duplicate
TRADE_MIN_COINS       = 0      # minimum coins required to trade

# ── Rarity Config (name → spawn weight) ───────────────────────────────────────
RARITY_WEIGHTS = {
    "⭐ Common":    60,
    "🌟 Uncommon":  25,
    "💫 Rare":      10,
    "✨ Epic":       4,
    "🌠 Legendary": 1,
}

RARITY_COLORS = {
    "⭐ Common":    "#9E9E9E",
    "🌟 Uncommon":  "#4CAF50",
    "💫 Rare":      "#2196F3",
    "✨ Epic":       "#9C27B0",
    "🌠 Legendary": "#FF9800",
}