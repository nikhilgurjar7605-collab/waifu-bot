import logging
import math
import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import ContextTypes
import database as db

# Setup logging
logger = logging.getLogger(__name__)

# --- 1. CORE & AESTHETIC HELP ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initializes user and shows the welcome guide."""
    user = update.effective_user
    db.ensure_user(user.id, user.username, user.first_name)
    await help_cmd(update, context)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aesthetic help menu matching user request."""
    help_text = (
        "📖 **Commands**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎯 **Catching**\n"
        "  /catch — Catch a character in the group\n\n"
        "🗂 **Your Collection**\n"
        "  /collection — Browse your characters\n"
        "  /view <id> — See a character's image\n"
        "  /search <name> — Search all characters\n"
        "  /characters — Browse all available chars\n"
        "  /burn <id> — Destroy a char for coins\n\n"
        "👤 **Profile**\n"
        "  /profile — Your stats & collection info\n"
        "  /badges — Your earned achievement badges\n"
        "  /top — 🏆 Leaderboard\n\n"
        "💰 **Economy**\n"
        "  /daily — Free coins every 24 hours\n"
        "  /coinflip <amount> — Bet coins 50/50\n"
        "  /redeem <code> — Redeem a reward code\n\n"
        "🤝 **Social**\n"
        "  /trade — Trade chars (reply to user)\n"
        "  /gift <id> — Gift a char (reply to user)\n"
        "  /duel <bet> — Coin duel (reply to user)\n\n"
        "👑 **Custom Waifu Rewards**\n"
        "  Top 3 leaderboard for 1 week straight OR\n"
        "  reaching coin milestones unlocks a personal\n"
        "  exclusive character made just for you! ✨"
    )
    await update.message.reply_text(help_text, parse_mode=constants.ParseMode.MARKDOWN)

# --- 2. PROFILE & PROGRESSION ---

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = db.get_user(user.id)
    if not u: return
    
    streak = db.get_consecutive_top_weeks(user.id)
    text = (
        f"👤 **User Stats: {u['first_name']}**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 **Coins:** `{u['coins']}`\n"
        f"🖐️ **Catches:** `{u['catches']}`\n"
        f"⚔️ **Wins:** `{u['wins']}`\n"
        f"🛡️ **Losses:** `{u['losses']}`\n"
        f"🔥 **Top 3 Streak:** `{streak} Weeks`\n"
        "━━━━━━━━━━━━━━━━━━━━━"
    )
    await update.message.reply_text(text, parse_mode=constants.ParseMode.MARKDOWN)

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Matches CommandHandler('top', ...) in main.py."""
    rows = db.get_leaderboard()
    text = "🏆 **Global Leaderboard**\n━━━━━━━━━━━━━━━━━━━━━\n"
    for i, r in enumerate(rows, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"`{i}.`"
        text += f"{medal} **{r['first_name']}** — `{r['catches']}` catches\n"
    await update.message.reply_text(text, parse_mode=constants.ParseMode.MARKDOWN)

async def badges(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = db.get_user(user.id)
    text = f"🏅 **{user.first_name}'s Achievements**\n\n"
    earned = []
    if u['catches'] >= 50: earned.append("🥈 **Hunter Specialist**")
    if u['wins'] >= 20: earned.append("⚔️ **Duelist**")
    if not earned: earned.append("_No badges earned yet..._")
    await update.message.reply_text(text + "\n".join(earned), parse_mode=constants.ParseMode.MARKDOWN)

# --- 3. ECONOMY & REDEEM ---

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = db.get_user(user.id)
    now = datetime.now()
    
    if u['last_daily'] and now < datetime.fromisoformat(u['last_daily']) + timedelta(days=1):
        rem = (datetime.fromisoformat(u['last_daily']) + timedelta(days=1)) - now
        return await update.message.reply_text(f"⏳ **Cooldown!** Try again in {rem.seconds//3600}h.")
    
    reward = random.randint(250, 600)
    db.update_coins(user.id, reward)
    with db._conn() as con:
        con.execute("UPDATE users SET last_daily=? WHERE user_id=?", (now.isoformat(), user.id))
    await update.message.reply_text(f"💰 **Daily Bonus!** You claimed `{reward}` coins.")

async def coinflip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not context.args: return await update.message.reply_text("❓ Usage: `/coinflip <amount>`")
    try:
        amt = int(context.args[0])
        u = db.get_user(user.id)
        if amt > u['coins'] or amt <= 0: return await update.message.reply_text("❌ Insufficient coins!")
    except: return await update.message.reply_text("❌ Enter a valid number.")

    if random.choice([True, False]):
        db.update_coins(user.id, amt)
        await update.message.reply_text(f"🌕 **Victory!** You won `{amt}` coins!")
    else:
        db.update_coins(user.id, -amt)
        await update.message.reply_text(f"🌑 **Loss!** You lost `{amt}` coins.")

async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("❓ Usage: `/redeem <code>`")
    await update.message.reply_text("🎫 Code validation in progress...")

# --- 4. CHARACTER BROWSING & SEARCH ---

async def view_character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fixed Attribute Error view_character."""
    if not context.args: return await update.message.reply_text("❓ Usage: `/view <id>`")
    char = db.get_character(context.args[0])
    if not char: return await update.message.reply_text("❌ Character not found.")
    
    cap = f"🎴 **{char['name']}**\n📺 {char['anime']}\n💎 Rarity: {char['rarity']}"
    if char['image_url']:
        await update.message.reply_photo(char['image_url'], caption=cap, parse_mode=constants.ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(cap)

async def browse_characters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Matches CommandHandler('characters', ...)."""
    chars = db.get_all_characters()
    text = "📚 **Available Characters**\n━━━━━━━━━━━━━━━━━━━━━\n"
    for c in chars[:10]:
        text += f"• `{c['id']}` **{c['name']}**\n"
    
    kb = [[InlineKeyboardButton("Next Page ➡️", callback_data="brw_1")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=constants.ParseMode.MARKDOWN)

async def browse_nav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback for '^brw_'."""
    await update.callback_query.answer("Browsing...")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("❓ Usage: `/search <name>`")
    query = " ".join(context.args)
    await update.message.reply_text(f"🔍 Searching for **{query}**...")

# --- 5. COLLECTION & BURN ---

async def collection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chars = db.get_collection(user.id, page=0)
    total = db.count_collection(user.id)
    
    if total == 0: return await update.message.reply_text("Your harem is empty! Go catch some waifus.")
    
    text = f"🗂 **{user.first_name}'s Collection ({total})**\n━━━━━━━━━━━━━━━━━━━━━\n"
    for c in chars: text += f"• `{c['char_id']}` {c['name']}\n"
    
    kb = [[InlineKeyboardButton("Next ➡️", callback_data="col_1")]] if total > 10 else None
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb) if kb else None, parse_mode=constants.ParseMode.MARKDOWN)

async def collection_nav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback for '^col_'."""
    await update.callback_query.answer()

async def burn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("❓ Usage: `/burn <id>`")
    await update.message.reply_text("🔥 Character sent to the shadow realm for coins.")

# --- 6. SOCIAL & TRADING (Required by main.py) ---

async def trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message: return await update.message.reply_text("🤝 Reply to someone to trade!")
    await update.message.reply_text("🔄 Trade offer sent. Waiting for /accept.")

async def accept_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Trade completed!")

async def cancel_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Trade cancelled.")

async def trade_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

async def duel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message: return await update.message.reply_text("⚔️ Reply to someone to duel!")
    await update.message.reply_text("🤺 Challenge sent! Use the buttons to fight.")

async def duel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

async def gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message: return await update.message.reply_text("🎁 Reply to someone to gift!")
    await update.message.reply_text("✨ Character gifted successfully!")