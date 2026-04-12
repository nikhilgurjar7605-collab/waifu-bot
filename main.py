"""
IPL Telegram Bot + Mini Cricket Game (Cricbuzz API + Toss + Clean UI + HTTP Health Check)
===========================================================================================
- Live scores, schedule, points table from Cricbuzz (via RapidAPI)
- Mini cricket game with coin toss
- Player profiles, leaderboard, rewards
- Owner commands for reward settings
- Auto alerts for subscribed teams
- HTTP health check server for Render (port 10000)
"""

import asyncio
import logging
import random
import sqlite3
from datetime import datetime, timezone, timedelta

import httpx
from aiohttp import web
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
BOT_TOKEN    = "8309190047:AAEGzbZsonD9zY3tub8WB1fG-KM40a17FjI"
CRICBUZZ_HOST = "cricbuzz-cricket.p.rapidapi.com"
CRICBUZZ_KEY  = "d0ccb6ebe9msh6d053b983ab064fp16450ejsnf1327a64d9f3"
OWNER_ID     = 1214273889

ALERT_INTERVAL = 300  # 5 minutes

# Default rewards (owner can change)
DEFAULT_WIN_SKILL_POINTS = 50
DEFAULT_WIN_YEN          = 100

TEAM_NAMES = {
    "MI": "Mumbai Indians", "CSK": "Chennai Super Kings",
    "RCB": "Royal Challengers Bengaluru", "KKR": "Kolkata Knight Riders",
    "DC": "Delhi Capitals", "PBKS": "Punjab Kings",
    "RR": "Rajasthan Royals", "SRH": "Sunrisers Hyderabad",
    "GT": "Gujarat Titans", "LSG": "Lucknow Super Giants",
}

# Game constants
MAX_WICKETS = 10
MAX_OVERS   = 10

# Commentary
SHOT_COMMENTARY = {
    1: ["🟢 Pushed to mid-on for a single.", "🟢 Nudged off the pads — 1 run.", "🟢 Dabbed to third man, easy single."],
    2: ["🟡 Driven through covers — 2 runs!", "🟡 Clipped off the legs, good running — 2!", "🟡 Guided past point — 2 runs."],
    3: ["🟠 Lofted over mid-wicket — 3 runs!", "🟠 Driven wide of long-on — 3!", "🟠 Sliced over backward point — 3."],
    4: ["🔴 FOUR! Cracking drive through the covers! 🏏", "🔴 FOUR! Pulled hard, races to the boundary!", "🔴 FOUR! Edged but flies past the keeper!"],
    5: ["🟣 FIVE! Misfield on the boundary — 5 runs! 🔥", "🟣 FIVE! Overthrows add to the total!"],
    6: ["💥 SIX! Massive hit over long-on! 💥", "💥 SIX! Into the stands! The crowd goes wild! 🎉", "💥 SIX! Helicopter shot — maximum!"],
}
BOWL_COMMENTARY = [
    "🎯 Good length delivery.", "🎯 Yorker — right on the stumps!",
    "🎯 Short ball, rises sharply.", "🎯 Swinging delivery beats the bat.",
    "🎯 Slower ball — deceives the batter!", "🎯 Full toss delivered.",
]

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  DATABASE
# ─────────────────────────────────────────────
DB_FILE = "ipl_bot.db"

def db_init():
    con = sqlite3.connect(DB_FILE)
    con.execute("""CREATE TABLE IF NOT EXISTS subscribers (
        chat_id INTEGER PRIMARY KEY, team_code TEXT NOT NULL, username TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS last_scores (
        match_id TEXT PRIMARY KEY, score TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS players (
        chat_id      INTEGER PRIMARY KEY,
        username     TEXT,
        skill_points INTEGER DEFAULT 0,
        yen          INTEGER DEFAULT 0,
        wins         INTEGER DEFAULT 0,
        losses       INTEGER DEFAULT 0,
        total_runs   INTEGER DEFAULT 0,
        total_wickets INTEGER DEFAULT 0)""")
    con.execute("""CREATE TABLE IF NOT EXISTS games (
        chat_id      INTEGER PRIMARY KEY,
        role         TEXT,
        phase        TEXT,
        player_runs  INTEGER DEFAULT 0,
        bot_runs     INTEGER DEFAULT 0,
        player_wickets INTEGER DEFAULT 0,
        bot_wickets  INTEGER DEFAULT 0,
        balls_played INTEGER DEFAULT 0,
        target       INTEGER DEFAULT 0,
        state        TEXT DEFAULT 'choose_role')""")
    con.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value TEXT)""")
    con.execute("INSERT OR IGNORE INTO settings VALUES ('win_skill_points', ?)",
                (str(DEFAULT_WIN_SKILL_POINTS),))
    con.execute("INSERT OR IGNORE INTO settings VALUES ('win_yen', ?)",
                (str(DEFAULT_WIN_YEN),))
    con.commit()
    con.close()

def db_get_player(chat_id):
    con = sqlite3.connect(DB_FILE)
    row = con.execute("SELECT * FROM players WHERE chat_id=?", (chat_id,)).fetchone()
    con.close()
    return row

def db_ensure_player(chat_id, username=""):
    con = sqlite3.connect(DB_FILE)
    con.execute("INSERT OR IGNORE INTO players VALUES (?,?,0,0,0,0,0,0)",
                (chat_id, username))
    con.commit()
    con.close()

def db_add_win(chat_id, skill_pts, yen, runs, wickets):
    con = sqlite3.connect(DB_FILE)
    con.execute("""UPDATE players SET wins=wins+1, skill_points=skill_points+?,
        yen=yen+?, total_runs=total_runs+?, total_wickets=total_wickets+?
        WHERE chat_id=?""", (skill_pts, yen, runs, wickets, chat_id))
    con.commit()
    con.close()

def db_add_loss(chat_id, runs, wickets):
    con = sqlite3.connect(DB_FILE)
    con.execute("""UPDATE players SET losses=losses+1,
        total_runs=total_runs+?, total_wickets=total_wickets+?
        WHERE chat_id=?""", (runs, wickets, chat_id))
    con.commit()
    con.close()

def db_get_leaderboard():
    con = sqlite3.connect(DB_FILE)
    rows = con.execute("""SELECT username, skill_points, yen, wins, losses
        FROM players ORDER BY skill_points DESC LIMIT 10""").fetchall()
    con.close()
    return rows

def db_get_game(chat_id):
    con = sqlite3.connect(DB_FILE)
    row = con.execute("SELECT * FROM games WHERE chat_id=?", (chat_id,)).fetchone()
    con.close()
    return row

def db_set_game(chat_id, **kwargs):
    con = sqlite3.connect(DB_FILE)
    row = con.execute("SELECT chat_id FROM games WHERE chat_id=?", (chat_id,)).fetchone()
    if row:
        sets = ", ".join(f"{k}=?" for k in kwargs)
        vals = list(kwargs.values()) + [chat_id]
        con.execute(f"UPDATE games SET {sets} WHERE chat_id=?", vals)
    else:
        cols = "chat_id, " + ", ".join(kwargs.keys())
        qs   = ", ".join("?" * (len(kwargs) + 1))
        con.execute(f"INSERT INTO games ({cols}) VALUES ({qs})",
                    [chat_id] + list(kwargs.values()))
    con.commit()
    con.close()

def db_delete_game(chat_id):
    con = sqlite3.connect(DB_FILE)
    con.execute("DELETE FROM games WHERE chat_id=?", (chat_id,))
    con.commit()
    con.close()

def db_get_setting(key):
    con = sqlite3.connect(DB_FILE)
    row = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    con.close()
    return row[0] if row else None

def db_set_setting(key, value):
    con = sqlite3.connect(DB_FILE)
    con.execute("INSERT OR REPLACE INTO settings VALUES (?, ?)", (key, str(value)))
    con.commit()
    con.close()

def db_subscribe(chat_id, team, username=""):
    con = sqlite3.connect(DB_FILE)
    con.execute("INSERT OR REPLACE INTO subscribers VALUES (?,?,?)", (chat_id, team.upper(), username))
    con.commit(); con.close()

def db_unsubscribe(chat_id):
    con = sqlite3.connect(DB_FILE)
    con.execute("DELETE FROM subscribers WHERE chat_id=?", (chat_id,))
    con.commit(); con.close()

def db_get_all_subscribers():
    con = sqlite3.connect(DB_FILE)
    rows = con.execute("SELECT chat_id, team_code FROM subscribers").fetchall()
    con.close(); return rows

def db_get_subscription(chat_id):
    con = sqlite3.connect(DB_FILE)
    row = con.execute("SELECT team_code FROM subscribers WHERE chat_id=?", (chat_id,)).fetchone()
    con.close(); return row[0] if row else None

def db_get_last_score(match_id):
    con = sqlite3.connect(DB_FILE)
    row = con.execute("SELECT score FROM last_scores WHERE match_id=?", (match_id,)).fetchone()
    con.close(); return row[0] if row else None

def db_set_last_score(match_id, score):
    con = sqlite3.connect(DB_FILE)
    con.execute("INSERT OR REPLACE INTO last_scores VALUES (?,?)", (match_id, score))
    con.commit(); con.close()


# ─────────────────────────────────────────────
#  CRICBUZZ API HELPERS
# ─────────────────────────────────────────────
async def cricbuzz_request(endpoint: str):
    """Make a request to Cricbuzz API and return JSON."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"https://{CRICBUZZ_HOST}{endpoint}",
                headers={
                    "x-rapidapi-key": CRICBUZZ_KEY,
                    "x-rapidapi-host": CRICBUZZ_HOST,
                }
            )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Cricbuzz API error: {e}")
        return None

async def get_ipl_series_id():
    """Find the series ID for IPL 2026."""
    data = await cricbuzz_request("/series/list")
    if not data:
        return None
    series_list = data.get("series", data.get("store", []))
    for series in series_list:
        name = series.get("name", "").lower()
        if "ipl" in name and "2026" in name:
            return series.get("id")
    return None

async def fetch_live_matches():
    """Return live IPL matches with scorecards."""
    series_id = await get_ipl_series_id()
    if not series_id:
        return []
    data = await cricbuzz_request(f"/series/{series_id}/matches")
    if not data:
        return []
    matches = data.get("matches", data.get("store", []))
    live = []
    for m in matches:
        state = m.get("state", "").lower()
        status = m.get("matchStatus", "").lower()
        if state == "in progress" or status == "live":
            match_id = m.get("matchId")
            if match_id:
                scorecard = await cricbuzz_request(f"/mcenter/v1/{match_id}/hscard")
                if scorecard:
                    m["score"] = scorecard.get("score", [])
            live.append(m)
    return live

async def fetch_upcoming_matches():
    """Return upcoming IPL matches (schedule)."""
    series_id = await get_ipl_series_id()
    if not series_id:
        return []
    data = await cricbuzz_request(f"/series/{series_id}/matches")
    if not data:
        return []
    matches = data.get("matches", data.get("store", []))
    upcoming = []
    for m in matches:
        state = m.get("state", "").lower()
        status = m.get("matchStatus", "").lower()
        if state == "upcoming" or status == "scheduled":
            upcoming.append(m)
    return upcoming

async def fetch_points_table(series_id):
    """Fetch points table for a given series ID."""
    data = await cricbuzz_request(f"/points_table/series/{series_id}")
    if not data:
        return None
    return data.get("pointsTable", data.get("store", []))

def is_ipl(match):
    name = match.get("name", "").lower()
    return "ipl" in name

def format_score_block(match):
    """Format a match's scorecard nicely."""
    name = match.get("name", "Match")
    scores = match.get("score", [])
    status = match.get("status", match.get("matchStatus", ""))
    lines = [f"🏏 *{name}*", "```"]
    for inn in scores:
        inn_name = inn.get('inning', '').replace('Inning', 'Inn')
        runs = inn.get('runs', inn.get('r', '-'))
        wkts = inn.get('wickets', inn.get('w', '-'))
        overs = inn.get('overs', inn.get('o', '-'))
        lines.append(f"{inn_name:<10} {runs}/{wkts} ({overs} ov)")
    if status:
        lines.append(f"\n📌 {status}")
    lines.append("```")
    return "\n".join(lines)


# ─────────────────────────────────────────────
#  IPL COMMAND HANDLERS
# ─────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_ensure_player(update.effective_chat.id, user.username or user.first_name)
    keyboard = [
        [InlineKeyboardButton("🔴 Live Scores", callback_data="score"),
         InlineKeyboardButton("📅 Today's Matches", callback_data="today")],
        [InlineKeyboardButton("📊 Points Table", callback_data="table"),
         InlineKeyboardButton("🏆 Latest Result", callback_data="result")],
        [InlineKeyboardButton("🎮 Play Mini Cricket", callback_data="play"),
         InlineKeyboardButton("🏅 Leaderboard", callback_data="leaderboard")],
        [InlineKeyboardButton("👤 My Profile", callback_data="profile"),
         InlineKeyboardButton("🔔 Subscribe", callback_data="subscribe_menu")],
    ]
    welcome = (
        f"*🏏 Welcome to IPL 2026 Bot, {user.first_name}!*\n\n"
        "📡 *Live scores* | 📅 *Schedule* | 📊 *Points Table*\n"
        "🎮 *Mini Cricket Game* | 🏅 *Leaderboard*\n\n"
        "▸ Type /help to see all commands\n"
        "▸ Use the buttons below to get started 👇"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def cmd_score(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.callback_query.message
    await msg.reply_text("⏳ *Fetching live scores from Cricbuzz...*", parse_mode="Markdown")
    matches = await fetch_live_matches()
    if not matches:
        await msg.reply_text("😴 *No IPL match live right now.*\nUse /today for schedule.", parse_mode="Markdown")
        return
    blocks = [format_score_block(m) for m in matches]
    reply = "🔴 *LIVE IPL SCORES*\n\n" + "\n\n──────────\n\n".join(blocks)
    await msg.reply_text(reply, parse_mode="Markdown")

async def cmd_today(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.callback_query.message
    await msg.reply_text("⏳ *Fetching schedule from Cricbuzz...*", parse_mode="Markdown")
    matches = await fetch_upcoming_matches()
    if not matches:
        await msg.reply_text("📅 *No IPL matches scheduled today.*", parse_mode="Markdown")
        return
    lines = ["📅 *Today's IPL Matches*\n"]
    for m in matches:
        start_time = m.get("startTime", "")
        try:
            dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            ist = dt + timedelta(hours=5, minutes=30)
            t = ist.strftime("%I:%M %p IST").lstrip("0")
        except:
            t = "TBA"
        venue = m.get("venue", m.get("ground", "TBA"))
        lines.append(f"🏏 *{m.get('name', 'Match')}*\n🕐 {t} | 🏟 {venue}\n")
    await msg.reply_text("\n".join(lines), parse_mode="Markdown")

async def cmd_result(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.callback_query.message
    await msg.reply_text("⏳ *Fetching latest result...*", parse_mode="Markdown")
    series_id = await get_ipl_series_id()
    if not series_id:
        await msg.reply_text("⚠️ Could not fetch series data.", parse_mode="Markdown")
        return
    data = await cricbuzz_request(f"/series/{series_id}/matches")
    if not data:
        await msg.reply_text("No recent matches found.", parse_mode="Markdown")
        return
    matches = data.get("matches", data.get("store", []))
    ended = [m for m in matches if m.get("state", "").lower() == "complete" or m.get("matchStatus", "").lower() == "ended"]
    if not ended:
        await msg.reply_text("No completed IPL matches recently.", parse_mode="Markdown")
        return
    latest = ended[0]
    match_id = latest.get("matchId")
    if match_id:
        scorecard = await cricbuzz_request(f"/mcenter/v1/{match_id}/hscard")
        if scorecard:
            latest["score"] = scorecard.get("score", [])
    await msg.reply_text(f"🏆 *Latest Result*\n\n{format_score_block(latest)}", parse_mode="Markdown")

async def cmd_table(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.callback_query.message
    await msg.reply_text("⏳ *Fetching live points table...*", parse_mode="Markdown")
    series_id = await get_ipl_series_id()
    if not series_id:
        await msg.reply_text("⚠️ Could not find IPL 2026 series ID. Showing static preview.", parse_mode="Markdown")
        await show_static_table(msg)
        return
    table_data = await fetch_points_table(series_id)
    if not table_data:
        await msg.reply_text("⚠️ Live points table unavailable. Showing static preview.", parse_mode="Markdown")
        await show_static_table(msg)
        return
    lines = ["📊 *IPL 2026 Points Table*", "```"]
    lines.append(f"{'#':<3} {'Team':<6} {'P':<3} {'W':<3} {'L':<3} {'NRR':<7} {'Pts'}")
    lines.append("─" * 38)
    sorted_teams = sorted(table_data, key=lambda x: (-int(x.get('points',0)), -float(x.get('netRunRate',0))))
    for i, team in enumerate(sorted_teams[:10], 1):
        name = team.get('teamName', '???')[:6]
        p = team.get('matchesPlayed', '0')
        w = team.get('wins', '0')
        l = team.get('losses', '0')
        nrr = team.get('netRunRate', '0.00')
        pts = team.get('points', '0')
        lines.append(f"{i:<3} {name:<6} {p:<3} {w:<3} {l:<3} {nrr:<7} {pts}")
    lines.append("```")
    lines.append("\n🟢 = Playoff zone (top 4)")
    await msg.reply_text("\n".join(lines), parse_mode="Markdown")

async def show_static_table(msg):
    table = [
        ("CSK",6,5,1,"+0.82",10),("MI",6,4,2,"+0.44",8),
        ("GT",6,4,2,"+0.31",8),("RCB",6,3,3,"-0.12",6),
        ("KKR",6,3,3,"-0.18",6),("PBKS",6,2,4,"+0.05",4),
        ("DC",6,2,4,"-0.33",4),("RR",6,2,4,"-0.41",4),
        ("SRH",6,1,5,"-0.55",2),("LSG",6,1,5,"-0.62",2),
    ]
    lines = ["📊 *IPL 2026 Points Table (Preview)*", "```"]
    lines.append(f"{'#':<3} {'Team':<6} {'P':<3} {'W':<3} {'L':<3} {'NRR':<7} {'Pts'}")
    lines.append("─" * 38)
    for i, (team, p, w, l, nrr, pts) in enumerate(table, 1):
        lines.append(f"{i:<3} {team:<6} {p:<3} {w:<3} {l:<3} {nrr:<7} {pts}")
    lines.append("```")
    lines.append("\n⚠️ *Live data unavailable – showing static preview.*")
    await msg.reply_text("\n".join(lines), parse_mode="Markdown")

async def cmd_subscribe(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not ctx.args:
        buttons = [[InlineKeyboardButton(n, callback_data=f"sub_{c}")] for c, n in TEAM_NAMES.items()]
        await msg.reply_text(
            "🔔 *Subscribe to Team Alerts*\n\nChoose your favorite team to get live score updates:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
    team = ctx.args[0].upper()
    if team not in TEAM_NAMES:
        await msg.reply_text(f"❌ Unknown team code. Try: {', '.join(TEAM_NAMES)}")
        return
    db_subscribe(update.effective_chat.id, team, update.effective_user.username or "")
    await msg.reply_text(f"✅ *Subscribed to {TEAM_NAMES[team]} alerts!*\n\nYou'll receive live score updates.", parse_mode="Markdown")

async def cmd_unsubscribe(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    cur = db_get_subscription(chat_id)
    if not cur:
        await update.message.reply_text("ℹ️ You are not subscribed to any alerts.")
        return
    db_unsubscribe(chat_id)
    await update.message.reply_text(f"🔕 *Unsubscribed from {TEAM_NAMES.get(cur, cur)} alerts.*", parse_mode="Markdown")

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "*🏏 IPL Bot - Help Center*\n\n"
        "*📡 Live Cricket*\n"
        "• /score - Live IPL scores (Cricbuzz)\n"
        "• /today - Today's fixtures\n"
        "• /table - Points table\n"
        "• /result - Latest match result\n"
        "• /subscribe [TEAM] - Get team alerts\n"
        "• /unsubscribe - Stop alerts\n\n"
        "*🎮 Mini Cricket Game*\n"
        "• /play - Start a new match (with toss!)\n"
        "• /bat - Bat first (manual override)\n"
        "• /bowl - Bowl first (manual override)\n"
        "• /shoot [1-6] - Play your shot/delivery\n"
        "• /profile - Your stats\n"
        "• /leaderboard - Top players\n"
        "• /rewards - Current rewards\n\n"
        "*👑 Owner Commands*\n"
        "• /setreward [points] - Set skill reward\n"
        "• /setyen [amount] - Set Yen reward\n\n"
        "*Team Codes:* MI, CSK, RCB, KKR, DC, PBKS, RR, SRH, GT, LSG"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


# ─────────────────────────────────────────────
#  MINI CRICKET GAME (with Toss)
# ─────────────────────────────────────────────
def overs_str(balls):
    return f"{balls // 6}.{balls % 6}"

def number_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1", callback_data="shoot_1"),
         InlineKeyboardButton("2", callback_data="shoot_2"),
         InlineKeyboardButton("3", callback_data="shoot_3")],
        [InlineKeyboardButton("4", callback_data="shoot_4"),
         InlineKeyboardButton("5", callback_data="shoot_5"),
         InlineKeyboardButton("6", callback_data="shoot_6")],
        [InlineKeyboardButton("❌ Quit Game", callback_data="quit_game")]
    ])

async def cmd_play(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    db_ensure_player(chat_id, user.username or user.first_name)
    db_delete_game(chat_id)

    toss_result = random.choice(["player", "bot"])
    if toss_result == "player":
        db_set_game(chat_id, role="", phase="", player_runs=0, bot_runs=0,
                    player_wickets=0, bot_wickets=0, balls_played=0, target=0, state="toss_player")
        toss_message = "*🎲 COIN TOSS*\n\n🪙 *You won the toss!*\n\nChoose to bat or bowl first:"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏏 Bat First", callback_data="toss_bat"),
             InlineKeyboardButton("🎳 Bowl First", callback_data="toss_bowl")]
        ])
        await (update.message or update.callback_query.message).reply_text(
            toss_message, parse_mode="Markdown", reply_markup=keyboard
        )
    else:
        db_set_game(chat_id, role="", phase="", player_runs=0, bot_runs=0,
                    player_wickets=0, bot_wickets=0, balls_played=0, target=0, state="toss_bot")
        toss_message = "*🎲 COIN TOSS*\n\n🤖 *Bot won the toss!*\n\nBot chooses to bat or bowl..."
        bot_choice = random.choice(["bat", "bowl"])
        if bot_choice == "bat":
            db_set_game(chat_id, role="bowl", phase="bowling", state="playing")
            await (update.message or update.callback_query.message).reply_text(
                f"{toss_message}\n\n🤖 Bot chooses to *BAT first*!\n\n🎳 You will bowl first. Pick your delivery (1–6):",
                parse_mode="Markdown",
                reply_markup=number_keyboard(),
            )
        else:
            db_set_game(chat_id, role="bat", phase="batting", state="playing")
            await (update.message or update.callback_query.message).reply_text(
                f"{toss_message}\n\n🤖 Bot chooses to *BOWL first*!\n\n🏏 You will bat first. Pick your shot (1–6):",
                parse_mode="Markdown",
                reply_markup=number_keyboard(),
            )

async def cmd_bat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    game = db_get_game(chat_id)
    if not game:
        await update.message.reply_text("❌ No active game. Use /play to start!")
        return
    db_set_game(chat_id, role="bat", phase="batting", state="playing")
    await update.message.reply_text(
        "*🏏 You chose to BAT first!*\n\nPick your shot:",
        parse_mode="Markdown",
        reply_markup=number_keyboard(),
    )

async def cmd_bowl(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    game = db_get_game(chat_id)
    if not game:
        await update.message.reply_text("❌ No active game. Use /play to start!")
        return
    db_set_game(chat_id, role="bowl", phase="bowling", state="playing")
    await update.message.reply_text(
        "*🎳 You chose to BOWL first!*\n\nPick your delivery:",
        parse_mode="Markdown",
        reply_markup=number_keyboard(),
    )

async def cmd_shoot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not ctx.args or not ctx.args[0].isdigit():
        await update.message.reply_text("Usage: /shoot [1-6]")
        return
    n = int(ctx.args[0])
    if n < 1 or n > 6:
        await update.message.reply_text("Please pick a number between 1 and 6.")
        return
    await process_shot(update, ctx, n, via_callback=False)

async def process_shot(update: Update, ctx: ContextTypes.DEFAULT_TYPE, player_pick: int, via_callback=False):
    chat_id = update.effective_chat.id
    msg = update.message if not via_callback else update.callback_query.message
    game = db_get_game(chat_id)
    if not game or game[9] != "playing":
        await msg.reply_text("❌ No active game. Use /play to start!")
        return

    _, role, phase, player_runs, bot_runs, player_wickets, bot_wickets, balls_played, target, state = game
    bot_pick = random.randint(1, 6)
    is_out = (player_pick == bot_pick)
    response_lines = []

    if phase == "batting":
        commentary = random.choice(BOWL_COMMENTARY)
        response_lines.append(f"🎳 *Bot bowls:* {bot_pick} — {commentary}")
        response_lines.append(f"🏏 *You play:* {player_pick}\n")
        if is_out:
            player_wickets += 1
            response_lines.append(f"💥 *OUT!* ({player_wickets}/{MAX_WICKETS} wickets)")
            if player_wickets >= MAX_WICKETS:
                response_lines.append(f"\n🏏 *All Out!* Your score: *{player_runs}/{player_wickets}* ({overs_str(balls_played)} ov)")
                await msg.reply_text("\n".join(response_lines), parse_mode="Markdown")
                await start_second_innings(msg, chat_id, player_runs, player_wickets, bot_runs, bot_wickets, balls_played, role)
                return
        else:
            player_runs += player_pick
            shot_com = random.choice(SHOT_COMMENTARY.get(player_pick, ["Good shot!"]))
            response_lines.append(f"✅ {shot_com} *+{player_pick} runs*")
        balls_played += 1
        db_set_game(chat_id, player_runs=player_runs, player_wickets=player_wickets, balls_played=balls_played)
        if balls_played >= MAX_OVERS * 6:
            response_lines.append(f"\n⏱ *Innings Over!* Your score: *{player_runs}/{player_wickets}* ({overs_str(balls_played)} ov)")
            await msg.reply_text("\n".join(response_lines), parse_mode="Markdown")
            await start_second_innings(msg, chat_id, player_runs, player_wickets, bot_runs, bot_wickets, balls_played, role)
            return
        response_lines.append(f"\n📊 *Score:* {player_runs}/{player_wickets} ({overs_str(balls_played)} ov)")
        if balls_played % 6 == 0:
            response_lines.append(f"🔔 *End of Over {balls_played//6}*")

    elif phase == "bowling":
        response_lines.append(f"🏏 *Bot plays:* {bot_pick}")
        response_lines.append(f"🎳 *You bowled:* {player_pick}\n")
        if is_out:
            bot_wickets += 1
            response_lines.append(f"💥 *WICKET!* Bot: {bot_wickets}/{MAX_WICKETS}")
            if bot_wickets >= MAX_WICKETS:
                response_lines.append(f"\n🤖 *Bot All Out!* Bot scored: *{bot_runs}/{bot_wickets}* ({overs_str(balls_played)} ov)")
                await msg.reply_text("\n".join(response_lines), parse_mode="Markdown")
                await start_second_innings(msg, chat_id, player_runs, player_wickets, bot_runs, bot_wickets, balls_played, role)
                return
        else:
            bot_runs += bot_pick
            if bot_pick == 6:
                response_lines.append(f"💥 *SIX!* Bot scores 6 runs!")
            elif bot_pick == 4:
                response_lines.append(f"🔴 *FOUR!* Bot scores 4 runs!")
            else:
                response_lines.append(f"🤖 Bot scores {bot_pick} runs.")
        if target > 0 and bot_runs > target:
            db_set_game(chat_id, bot_runs=bot_runs, bot_wickets=bot_wickets, balls_played=balls_played)
            await msg.reply_text("\n".join(response_lines), parse_mode="Markdown")
            await end_game(msg, chat_id, player_runs, bot_runs, player_wickets, bot_wickets, role)
            return
        balls_played += 1
        db_set_game(chat_id, bot_runs=bot_runs, bot_wickets=bot_wickets, balls_played=balls_played)
        if balls_played >= MAX_OVERS * 6:
            response_lines.append(f"\n⏱ *Bot Innings Over!* Bot: *{bot_runs}/{bot_wickets}* ({overs_str(balls_played)} ov)")
            await msg.reply_text("\n".join(response_lines), parse_mode="Markdown")
            await start_second_innings(msg, chat_id, player_runs, player_wickets, bot_runs, bot_wickets, balls_played, role)
            return
        response_lines.append(f"\n🤖 *Bot:* {bot_runs}/{bot_wickets} ({overs_str(balls_played)} ov)")
        if target > 0:
            need = target - bot_runs + 1
            left = MAX_OVERS*6 - balls_played
            response_lines.append(f"🎯 *Bot needs {need} runs from {left} balls*")
        if balls_played % 6 == 0:
            response_lines.append(f"🔔 *End of Over {balls_played//6}*")

    elif phase == "batting2":
        commentary = random.choice(BOWL_COMMENTARY)
        response_lines.append(f"🎳 *Bot bowls:* {bot_pick} — {commentary}")
        response_lines.append(f"🏏 *You play:* {player_pick}\n")
        if is_out:
            player_wickets += 1
            response_lines.append(f"💥 *OUT!* ({player_wickets}/{MAX_WICKETS} wickets)")
            if player_wickets >= MAX_WICKETS:
                response_lines.append(f"🏏 *All Out!* You scored: *{player_runs}/{player_wickets}*")
                db_set_game(chat_id, player_runs=player_runs, player_wickets=player_wickets, balls_played=balls_played)
                await msg.reply_text("\n".join(response_lines), parse_mode="Markdown")
                await end_game(msg, chat_id, player_runs, bot_runs, player_wickets, bot_wickets, role)
                return
        else:
            player_runs += player_pick
            shot_com = random.choice(SHOT_COMMENTARY.get(player_pick, ["Good shot!"]))
            response_lines.append(f"✅ {shot_com} *+{player_pick}*")
            if player_runs > target:
                db_set_game(chat_id, player_runs=player_runs, player_wickets=player_wickets)
                response_lines.append(f"\n🎉 *YOU WIN!* You reached the target!")
                await msg.reply_text("\n".join(response_lines), parse_mode="Markdown")
                await end_game(msg, chat_id, player_runs, bot_runs, player_wickets, bot_wickets, role)
                return
        balls_played += 1
        db_set_game(chat_id, player_runs=player_runs, player_wickets=player_wickets, balls_played=balls_played)
        if balls_played >= MAX_OVERS * 6:
            await msg.reply_text("\n".join(response_lines), parse_mode="Markdown")
            await end_game(msg, chat_id, player_runs, bot_runs, player_wickets, bot_wickets, role)
            return
        need = target - player_runs + 1
        left = MAX_OVERS*6 - balls_played
        response_lines.append(f"\n📊 *You:* {player_runs}/{player_wickets} ({overs_str(balls_played)} ov)")
        response_lines.append(f"🎯 *Need {need} runs from {left} balls*")

    elif phase == "bowling2":
        response_lines.append(f"🏏 *Bot plays:* {bot_pick}")
        response_lines.append(f"🎳 *You bowled:* {player_pick}\n")
        if is_out:
            bot_wickets += 1
            response_lines.append(f"💥 *WICKET!* Bot: {bot_wickets}/{MAX_WICKETS}")
            if bot_wickets >= MAX_WICKETS:
                db_set_game(chat_id, bot_wickets=bot_wickets)
                await msg.reply_text("\n".join(response_lines), parse_mode="Markdown")
                await end_game(msg, chat_id, player_runs, bot_runs, player_wickets, bot_wickets, role)
                return
        else:
            bot_runs += bot_pick
            if bot_pick == 6:
                response_lines.append(f"💥 *SIX!* Bot scores 6 runs!")
            elif bot_pick == 4:
                response_lines.append(f"🔴 *FOUR!* Bot scores 4 runs!")
            else:
                response_lines.append(f"🤖 Bot scores {bot_pick} runs.")
            if bot_runs > target:
                db_set_game(chat_id, bot_runs=bot_runs, bot_wickets=bot_wickets)
                response_lines.append("\n🤖 *Bot reaches the target!*")
                await msg.reply_text("\n".join(response_lines), parse_mode="Markdown")
                await end_game(msg, chat_id, player_runs, bot_runs, player_wickets, bot_wickets, role)
                return
        balls_played += 1
        db_set_game(chat_id, bot_runs=bot_runs, bot_wickets=bot_wickets, balls_played=balls_played)
        if balls_played >= MAX_OVERS * 6:
            await msg.reply_text("\n".join(response_lines), parse_mode="Markdown")
            await end_game(msg, chat_id, player_runs, bot_runs, player_wickets, bot_wickets, role)
            return
        need = target - bot_runs + 1
        left = MAX_OVERS*6 - balls_played
        response_lines.append(f"\n🤖 *Bot:* {bot_runs}/{bot_wickets} ({overs_str(balls_played)} ov)")
        response_lines.append(f"🎯 *Bot needs {need} runs from {left} balls*")

    await msg.reply_text("\n".join(response_lines), parse_mode="Markdown", reply_markup=number_keyboard())

async def start_second_innings(msg, chat_id, player_runs, player_wickets, bot_runs, bot_wickets, balls_played, role):
    if role == "bat":
        target = player_runs
        db_set_game(chat_id, phase="bowling2", balls_played=0, target=target, bot_runs=0, bot_wickets=0, state="playing")
        need = target + 1
        await msg.reply_text(
            f"🔄 *SECOND INNINGS - Bot Chasing*\n\n"
            f"Your total: *{player_runs}/{player_wickets}*\n"
            f"🎯 *Bot needs {need} runs to win*\n\n"
            f"Pick your delivery (1–6):",
            parse_mode="Markdown",
            reply_markup=number_keyboard(),
        )
    else:
        target = bot_runs
        db_set_game(chat_id, phase="batting2", balls_played=0, target=target, player_runs=0, player_wickets=0, state="playing")
        need = target + 1
        await msg.reply_text(
            f"🔄 *SECOND INNINGS - You Chase*\n\n"
            f"Bot's total: *{bot_runs}/{bot_wickets}*\n"
            f"🎯 *You need {need} runs to win*\n\n"
            f"Pick your shot (1–6):",
            parse_mode="Markdown",
            reply_markup=number_keyboard(),
        )

async def end_game(msg, chat_id, player_runs, bot_runs, player_wickets, bot_wickets, role):
    db_delete_game(chat_id)
    win_sp = int(db_get_setting("win_skill_points") or DEFAULT_WIN_SKILL_POINTS)
    win_yen = int(db_get_setting("win_yen") or DEFAULT_WIN_YEN)

    player_won = player_runs > bot_runs
    margin = abs(player_runs - bot_runs)

    scoreboard = (
        f"```\n"
        f"YOU: {player_runs}/{player_wickets}\n"
        f"BOT: {bot_runs}/{bot_wickets}\n"
        f"```"
    )

    if player_won:
        db_add_win(chat_id, win_sp, win_yen, player_runs, player_wickets)
        result = (
            f"*🎉 VICTORY!*\n\n"
            f"You win by *{margin}* runs!\n\n"
            f"{scoreboard}\n"
            f"*🏅 Rewards Earned:*\n"
            f"⭐ +{win_sp} Skill Points\n"
            f"💴 +{win_yen} Yen\n\n"
            f"Check /profile for your total."
        )
    else:
        db_add_loss(chat_id, player_runs, player_wickets)
        result = (
            f"*😔 DEFEAT*\n\n"
            f"Bot wins by *{margin}* runs.\n\n"
            f"{scoreboard}\n"
            f"Better luck next time! Use /play to try again."
        )

    play_again = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 Play Again", callback_data="play"),
        InlineKeyboardButton("🏅 Leaderboard", callback_data="leaderboard"),
    ]])
    await msg.reply_text(result, parse_mode="Markdown", reply_markup=play_again)


# ─────────────────────────────────────────────
#  PROFILE & LEADERBOARD
# ─────────────────────────────────────────────
async def cmd_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = update.message or update.callback_query.message
    db_ensure_player(chat_id, update.effective_user.username or update.effective_user.first_name)
    p = db_get_player(chat_id)
    if not p:
        await msg.reply_text("❌ Profile not found. Use /play to start playing!")
        return
    _, username, sp, yen, wins, losses, runs, wickets = p
    total = wins + losses
    wr = f"{wins/total*100:.1f}%" if total > 0 else "N/A"
    win_sp = db_get_setting("win_skill_points") or DEFAULT_WIN_SKILL_POINTS
    win_yen = db_get_setting("win_yen") or DEFAULT_WIN_YEN
    profile_text = (
        f"*👤 Player Profile: {username}*\n\n"
        f"⭐ Skill Points: *{sp}*\n"
        f"💴 Yen: *{yen}*\n\n"
        f"*📊 Match Stats*\n"
        f"🏆 Wins: {wins}  |  Losses: {losses}\n"
        f"📈 Win Rate: {wr}\n\n"
        f"*🏏 Batting*\n"
        f"Total Runs: {runs}\n\n"
        f"*🎳 Bowling*\n"
        f"Total Wickets: {wickets}\n\n"
        f"*💰 Win Reward:* {win_sp} SP + {win_yen} Yen"
    )
    await msg.reply_text(profile_text, parse_mode="Markdown")

async def cmd_leaderboard(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.callback_query.message
    rows = db_get_leaderboard()
    if not rows:
        await msg.reply_text("🏆 *No players yet.* Be the first to play!", parse_mode="Markdown")
        return
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = ["*🏆 TOP 10 PLAYERS*", "```"]
    lines.append(f"{'#':<3} {'Player':<15} {'SP':<6} {'Yen':<6} {'W/L'}")
    lines.append("─" * 38)
    for i, (username, sp, yen, wins, losses) in enumerate(rows, 1):
        name = (username or "Unknown")[:12]
        lines.append(f"{medals[i-1]} {name:<12} {sp:<6} {yen:<6} {wins}/{losses}")
    lines.append("```")
    await msg.reply_text("\n".join(lines), parse_mode="Markdown")

async def cmd_rewards(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sp = db_get_setting("win_skill_points") or DEFAULT_WIN_SKILL_POINTS
    yen = db_get_setting("win_yen") or DEFAULT_WIN_YEN
    await (update.message or update.callback_query.message).reply_text(
        f"*🎁 Current Game Rewards*\n\n"
        f"🏆 *Win Reward*\n"
        f"⭐ Skill Points: {sp}\n"
        f"💴 Yen: {yen}\n\n"
        f"_Only the bot owner can change these._",
        parse_mode="Markdown",
    )


# ─────────────────────────────────────────────
#  OWNER COMMANDS
# ─────────────────────────────────────────────
async def cmd_setreward(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ *Owner only command.*", parse_mode="Markdown")
        return
    if not ctx.args or not ctx.args[0].isdigit():
        await update.message.reply_text("Usage: /setreward [points]\nExample: /setreward 100")
        return
    pts = int(ctx.args[0])
    db_set_setting("win_skill_points", pts)
    await update.message.reply_text(f"✅ *Win reward updated!*\n⭐ Skill Points per win: *{pts}*", parse_mode="Markdown")

async def cmd_setyen(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ *Owner only command.*", parse_mode="Markdown")
        return
    if not ctx.args or not ctx.args[0].isdigit():
        await update.message.reply_text("Usage: /setyen [amount]\nExample: /setyen 500")
        return
    yen = int(ctx.args[0])
    db_set_setting("win_yen", yen)
    await update.message.reply_text(f"✅ *Win reward updated!*\n💴 Yen per win: *{yen}*", parse_mode="Markdown")


# ─────────────────────────────────────────────
#  CALLBACK HANDLER
# ─────────────────────────────────────────────
async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "score": await cmd_score(update, ctx)
    elif data == "today": await cmd_today(update, ctx)
    elif data == "table": await cmd_table(update, ctx)
    elif data == "result": await cmd_result(update, ctx)
    elif data == "play": await cmd_play(update, ctx)
    elif data == "leaderboard": await cmd_leaderboard(update, ctx)
    elif data == "profile": await cmd_profile(update, ctx)
    elif data == "subscribe_menu":
        buttons = [[InlineKeyboardButton(n, callback_data=f"sub_{c}")] for c, n in TEAM_NAMES.items()]
        await query.message.reply_text("🔔 *Select your team:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
    elif data == "quit_game":
        db_delete_game(update.effective_chat.id)
        await query.message.reply_text("❌ *Game cancelled.* Use /play to start a new match.", parse_mode="Markdown")
    elif data == "toss_bat":
        chat_id = update.effective_chat.id
        game = db_get_game(chat_id)
        if not game or game[9] != "toss_player":
            await query.message.reply_text("❌ No active toss. Use /play to start a new game.")
            return
        db_set_game(chat_id, role="bat", phase="batting", state="playing")
        await query.message.reply_text(
            "*🏏 You chose to BAT first!*\n\nPick your shot:",
            parse_mode="Markdown",
            reply_markup=number_keyboard(),
        )
    elif data == "toss_bowl":
        chat_id = update.effective_chat.id
        game = db_get_game(chat_id)
        if not game or game[9] != "toss_player":
            await query.message.reply_text("❌ No active toss. Use /play to start a new game.")
            return
        db_set_game(chat_id, role="bowl", phase="bowling", state="playing")
        await query.message.reply_text(
            "*🎳 You chose to BOWL first!*\n\nPick your delivery:",
            parse_mode="Markdown",
            reply_markup=number_keyboard(),
        )
    elif data.startswith("shoot_"):
        n = int(data.split("_")[1])
        await process_shot(update, ctx, n, via_callback=True)
    elif data.startswith("sub_"):
        team = data[4:]
        chat_id = update.effective_chat.id
        username = update.effective_user.username or ""
        db_subscribe(chat_id, team, username)
        await query.message.reply_text(f"✅ *Subscribed to {TEAM_NAMES.get(team, team)} alerts!*", parse_mode="Markdown")


# ─────────────────────────────────────────────
#  AUTO-ALERT JOB
# ─────────────────────────────────────────────
async def alert_job(ctx: ContextTypes.DEFAULT_TYPE):
    subscribers = db_get_all_subscribers()
    if not subscribers:
        return

    matches = await fetch_live_matches()
    series_id = await get_ipl_series_id()
    if not series_id:
        return
    series_data = await cricbuzz_request(f"/series/{series_id}/matches")
    all_matches = series_data.get("matches", series_data.get("store", [])) if series_data else []
    ended = [m for m in all_matches if m.get("state", "").lower() == "complete" or m.get("matchStatus", "").lower() == "ended"]

    team_match_map = {}
    for m in matches + ended:
        for code, full in TEAM_NAMES.items():
            if code.lower() in m.get("name", "").lower() or full.lower() in m.get("name", "").lower():
                team_match_map[code] = m
                break

    for chat_id, team_code in subscribers:
        match = team_match_map.get(team_code)
        if not match:
            continue

        match_id = str(match.get("matchId", ""))
        scores = match.get("score", [])
        score_str = "|".join(f"{s.get('runs',0)}/{s.get('wickets',0)}({s.get('overs',0)})" for s in scores)
        last = db_get_last_score(match_id)

        if match.get("state", "").lower() == "complete" and last != "ENDED":
            db_set_last_score(match_id, "ENDED")
            try:
                await ctx.bot.send_message(
                    chat_id=chat_id,
                    text=f"🏆 *Match Over!*\n\n{format_score_block(match)}",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.warning(f"Alert failed {chat_id}: {e}")
            continue

        if score_str and score_str != last:
            db_set_last_score(match_id, score_str)
            if last is None:
                try:
                    await ctx.bot.send_message(
                        chat_id=chat_id,
                        text=f"🏏 *Match Started!*\n{TEAM_NAMES.get(team_code, team_code)} are playing!\n\n{format_score_block(match)}",
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    logger.warning(f"Alert failed {chat_id}: {e}")
            else:
                try:
                    prev_w = sum(int(p.split("/")[1].split("(")[0]) for p in last.split("|") if "/" in p)
                    curr_w = sum(s.get("wickets", 0) for s in scores)
                    if curr_w > prev_w:
                        await ctx.bot.send_message(
                            chat_id=chat_id,
                            text=f"🚨 *WICKET!* ({TEAM_NAMES.get(team_code, team_code)})\n\n{format_score_block(match)}",
                            parse_mode="Markdown"
                        )
                except Exception as e:
                    logger.warning(f"Wicket alert failed {chat_id}: {e}")


# ─────────────────────────────────────────────
#  HTTP HEALTH CHECK SERVER (for Render)
# ─────────────────────────────────────────────
async def health_check(request):
    """Simple health check endpoint for Render."""
    return web.Response(text="OK", status=200)

async def run_http_server():
    """Run a minimal HTTP server on port 10000."""
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()
    logger.info("✅ HTTP health check server running on port 10000")
    # Keep the server running forever
    await asyncio.Event().wait()


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
async def post_init(app: Application):
    await app.bot.set_my_commands([
        BotCommand("start", "🏠 Main menu"),
        BotCommand("score", "🔴 Live IPL scores (Cricbuzz)"),
        BotCommand("today", "📅 Today's matches"),
        BotCommand("table", "📊 Points table"),
        BotCommand("result", "🏆 Latest result"),
        BotCommand("subscribe", "🔔 Subscribe to team alerts"),
        BotCommand("unsubscribe", "🔕 Stop alerts"),
        BotCommand("play", "🎮 Start mini cricket (with toss)"),
        BotCommand("bat", "🏏 Bat first (manual)"),
        BotCommand("bowl", "🎳 Bowl first (manual)"),
        BotCommand("shoot", "🎯 Play a shot (1-6)"),
        BotCommand("profile", "👤 Your stats"),
        BotCommand("leaderboard", "🏅 Top players"),
        BotCommand("rewards", "🎁 Current rewards"),
        BotCommand("setreward", "👑 Set skill reward (owner)"),
        BotCommand("setyen", "👑 Set Yen reward (owner)"),
        BotCommand("help", "📖 All commands"),
    ])

def main():
    db_init()
    logger.info("🏏 IPL Bot with Cricbuzz API, Mini Cricket, Toss, and Clean UI starting...")

    # Build the Telegram bot application
    app = (Application.builder()
           .token(BOT_TOKEN)
           .post_init(post_init)
           .build())

    # Add all handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("score", cmd_score))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("table", cmd_table))
    app.add_handler(CommandHandler("result", cmd_result))
    app.add_handler(CommandHandler("subscribe", cmd_subscribe))
    app.add_handler(CommandHandler("unsubscribe", cmd_unsubscribe))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("play", cmd_play))
    app.add_handler(CommandHandler("bat", cmd_bat))
    app.add_handler(CommandHandler("bowl", cmd_bowl))
    app.add_handler(CommandHandler("shoot", cmd_shoot))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("leaderboard", cmd_leaderboard))
    app.add_handler(CommandHandler("rewards", cmd_rewards))
    app.add_handler(CommandHandler("setreward", cmd_setreward))
    app.add_handler(CommandHandler("setyen", cmd_setyen))
    app.add_handler(CallbackQueryHandler(button_handler))

    # Start the job queue
    app.job_queue.run_repeating(alert_job, interval=ALERT_INTERVAL, first=10)

    # Run both the bot polling and the HTTP server concurrently
    async def run_bot_and_http():
        # Start HTTP server in background
        http_task = asyncio.create_task(run_http_server())
        # Start the bot polling
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        # Keep both running
        await asyncio.gather(app.updater.running, http_task)

    try:
        asyncio.run(run_bot_and_http())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")

if __name__ == "__main__":
    main()
