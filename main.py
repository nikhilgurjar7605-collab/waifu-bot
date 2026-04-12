"""
IPL Telegram Bot + Mini Cricket Game
======================================
Features:
  - All original IPL bot features (live score, schedule, table, alerts)
  - /play        Start a mini cricket match vs bot
  - /bat /bowl   Choose your role
  - /shoot 1-6   Play a shot (batting) or bowl a delivery
  - /profile     View your skill points, wins, losses
  - /leaderboard Top 10 players by skill points
  - /setreward   [OWNER ONLY] Set skill points reward for winning
  - /setyen      [OWNER ONLY] Set Yen reward for winning
  - /rewards     View current reward settings

Game Logic:
  - Player picks bat or bowl vs bot
  - Each turn: player picks 1-6, bot picks 1-6 randomly
  - If same number → OUT (batting) / WICKET (bowling)
  - Target: 10 overs (60 balls) or all out
  - Winner gets configurable Skill Points + Yen

Dependencies:
  pip install python-telegram-bot[job-queue] httpx

"""

import asyncio
import logging
import random
import sqlite3
from datetime import datetime, timezone

import httpx
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
BOT_TOKEN    = "8309190047:AAEGzbZsonD9zY3tub8WB1fG-KM40a17FjI"   # from @BotFather
CRICAPI_KEY  = "bfb4ef11-21a2-45ff-bb66-e0212dba00b6"          # from cricapi.com
OWNER_ID     = 1214273889                   # your Telegram user ID (int)

CRICAPI_BASE   = "https://api.cricapi.com/v1"
ALERT_INTERVAL = 300  # 5 minutes

# Default rewards (owner can change these live)
DEFAULT_WIN_SKILL_POINTS = 50
DEFAULT_WIN_YEN          = 100

TEAM_NAMES = {
    "MI": "Mumbai Indians", "CSK": "Chennai Super Kings",
    "RCB": "Royal Challengers Bengaluru", "KKR": "Kolkata Knight Riders",
    "DC": "Delhi Capitals", "PBKS": "Punjab Kings",
    "RR": "Rajasthan Royals", "SRH": "Sunrisers Hyderabad",
    "GT": "Gujarat Titans", "LSG": "Lucknow Super Giants",
}

# Shot/delivery commentary
SHOT_COMMENTARY = {
    1: ["Pushed to mid-on for a single.", "Nudged off the pads — 1 run.", "Dabbed to third man, easy single."],
    2: ["Driven through covers — 2 runs!", "Clipped off the legs, good running — 2!", "Guided past point — 2 runs."],
    3: ["Lofted over mid-wicket — 3 runs!", "Driven wide of long-on — 3!", "Sliced over backward point — 3."],
    4: ["FOUR! Cracking drive through the covers! 🏏", "FOUR! Pulled hard, races to the boundary!", "FOUR! Edged but flies past the keeper!"],
    5: ["FIVE! Misfield on the boundary — 5 runs! 🔥", "FIVE! Overthrows add to the total!"],
    6: ["SIX! Massive hit over long-on! 💥", "SIX! Into the stands! The crowd goes wild! 🎉", "SIX! Helicopter shot — maximum!"],
}
BOWL_COMMENTARY = [
    "Good length delivery.", "Yorker — right on the stumps!",
    "Short ball, rises sharply.", "Swinging delivery beats the bat.",
    "Slower ball — deceives the batter!", "Full toss delivered.",
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
    # Subscribers for match alerts
    con.execute("""CREATE TABLE IF NOT EXISTS subscribers (
        chat_id INTEGER PRIMARY KEY, team_code TEXT NOT NULL, username TEXT)""")
    # Last known scores for alert dedup
    con.execute("""CREATE TABLE IF NOT EXISTS last_scores (
        match_id TEXT PRIMARY KEY, score TEXT)""")
    # Player profiles
    con.execute("""CREATE TABLE IF NOT EXISTS players (
        chat_id      INTEGER PRIMARY KEY,
        username     TEXT,
        skill_points INTEGER DEFAULT 0,
        yen          INTEGER DEFAULT 0,
        wins         INTEGER DEFAULT 0,
        losses       INTEGER DEFAULT 0,
        total_runs   INTEGER DEFAULT 0,
        total_wickets INTEGER DEFAULT 0)""")
    # Active game sessions
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
    # Owner reward settings
    con.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value TEXT)""")
    # Seed default rewards
    con.execute("INSERT OR IGNORE INTO settings VALUES ('win_skill_points', ?)",
                (str(DEFAULT_WIN_SKILL_POINTS),))
    con.execute("INSERT OR IGNORE INTO settings VALUES ('win_yen', ?)",
                (str(DEFAULT_WIN_YEN),))
    con.commit()
    con.close()

# --- Player helpers ---
def db_get_player(chat_id):
    con = sqlite3.connect(DB_FILE)
    row = con.execute("SELECT * FROM players WHERE chat_id=?", (chat_id,)).fetchone()
    con.close()
    return row  # (chat_id, username, skill_points, yen, wins, losses, total_runs, total_wickets)

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

# --- Game helpers ---
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

# --- Settings helpers ---
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

# --- Subscriber helpers ---
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
#  CRICKET API HELPERS
# ─────────────────────────────────────────────
async def fetch_live_matches():
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{CRICAPI_BASE}/currentMatches",
                                 params={"apikey": CRICAPI_KEY, "offset": 0})
        data = r.json()
        return data.get("data", []) if data.get("status") == "success" else []
    except Exception as e:
        logger.error(f"API error: {e}"); return []

async def fetch_upcoming_matches():
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{CRICAPI_BASE}/matches",
                                 params={"apikey": CRICAPI_KEY, "offset": 0})
        data = r.json()
        return data.get("data", []) if data.get("status") == "success" else []
    except Exception as e:
        logger.error(f"API error: {e}"); return []

def is_ipl(match):
    series = match.get("series_id", "") or match.get("series", "") or ""
    name   = match.get("name", "")
    return "ipl" in series.lower() or "indian premier league" in name.lower()

def format_score_block(match):
    name   = match.get("name", "Match")
    scores = match.get("score", [])
    status = match.get("status", "")
    lines  = [f"🏏 *{name}*"]
    for inn in scores:
        lines.append(f"  {inn.get('inning','')}: {inn.get('r','-')}/{inn.get('w','-')} ({inn.get('o','-')} ov)")
    if status:
        lines.append(f"📌 {status}")
    return "\n".join(lines)


# ─────────────────────────────────────────────
#  IPL COMMAND HANDLERS
# ─────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_ensure_player(update.effective_chat.id, user.username or user.first_name)
    keyboard = [
        [InlineKeyboardButton("🔴 Live Score", callback_data="score"),
         InlineKeyboardButton("📅 Today", callback_data="today")],
        [InlineKeyboardButton("📊 Points Table", callback_data="table"),
         InlineKeyboardButton("🏆 Last Result", callback_data="result")],
        [InlineKeyboardButton("🏏 Play Mini Cricket", callback_data="play"),
         InlineKeyboardButton("🏅 Leaderboard", callback_data="leaderboard")],
        [InlineKeyboardButton("👤 My Profile", callback_data="profile")],
    ]
    await update.message.reply_text(
        f"👋 Hello *{user.first_name}*!\n\n"
        "Welcome to *IPL 2026 Bot* 🏏\n\n"
        "📡 Live scores • 📅 Schedule • 📊 Table\n"
        "🎮 Mini Cricket Game • 🏅 Leaderboard\n\n"
        "Type /help for all commands.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def cmd_score(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.callback_query.message
    await msg.reply_text("⏳ Fetching live scores...")
    matches  = await fetch_live_matches()
    ipl_live = [m for m in matches if is_ipl(m) and not m.get("matchEnded")]
    if not ipl_live:
        ended = [m for m in matches if is_ipl(m) and m.get("matchEnded")]
        reply = ("✅ Recently ended:\n\n" + format_score_block(ended[0])
                 if ended else "😴 No IPL match live right now. Use /today for schedule.")
    else:
        blocks = [format_score_block(m) for m in ipl_live]
        reply  = "🔴 *LIVE IPL SCORES*\n\n" + "\n\n──────────\n\n".join(blocks)
    await msg.reply_text(reply, parse_mode="Markdown")

async def cmd_today(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.callback_query.message
    await msg.reply_text("⏳ Fetching schedule...")
    all_m     = await fetch_upcoming_matches()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today     = [m for m in all_m if is_ipl(m) and m.get("dateTimeGMT","").startswith(today_str)]
    if not today:
        await msg.reply_text("📅 No IPL matches today. Use /result for latest result."); return
    lines = ["📅 *Today's IPL Matches*\n"]
    for m in today:
        gmt = m.get("dateTimeGMT","")
        try:
            dt = datetime.fromisoformat(gmt.replace("Z","+00:00"))
            h,mn = (dt.hour+5)%24, dt.minute+30
            if mn>=60: h,mn=(h+1)%24,mn-60
            t = f"{h:02d}:{mn:02d} IST"
        except: t="TBA"
        lines.append(f"🏏 *{m.get('name','')}*\n🕐 {t} | 🏟 {m.get('venue','TBA')}\n")
    await msg.reply_text("\n".join(lines), parse_mode="Markdown")

async def cmd_result(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.callback_query.message
    await msg.reply_text("⏳ Fetching result...")
    matches = await fetch_live_matches()
    ended   = [m for m in matches if is_ipl(m) and m.get("matchEnded")]
    if not ended:
        all_m = await fetch_upcoming_matches()
        ended = [m for m in all_m if is_ipl(m) and m.get("matchEnded")]
    if not ended:
        await msg.reply_text("No recent IPL result. Check back after a match!"); return
    await msg.reply_text(f"🏆 *Latest Result*\n\n{format_score_block(ended[0])}", parse_mode="Markdown")

async def cmd_table(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.callback_query.message
    table = [
        ("CSK",6,5,1,"+0.82",10),("MI",6,4,2,"+0.44",8),
        ("GT",6,4,2,"+0.31",8),("RCB",6,3,3,"-0.12",6),
        ("KKR",6,3,3,"-0.18",6),("PBKS",6,2,4,"+0.05",4),
        ("DC",6,2,4,"-0.33",4),("RR",6,2,4,"-0.41",4),
        ("SRH",6,1,5,"-0.55",2),("LSG",6,1,5,"-0.62",2),
    ]
    lines = ["📊 *IPL 2026 Points Table*\n","`#   Team  P  W  L   NRR   Pts`","`"+"─"*32+"`"]
    for i,(team,p,w,l,nrr,pts) in enumerate(table,1):
        q = "🟢" if i<=4 else "⚪"
        lines.append(f"`{i:<3} {team:<5}{p:<3}{w:<3}{l:<4}{nrr:<7}{pts}`  {q}")
    lines.append("\n🟢 = Playoff zone")
    await msg.reply_text("\n".join(lines), parse_mode="Markdown")

async def cmd_subscribe(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not ctx.args:
        buttons = [[InlineKeyboardButton(n, callback_data=f"sub_{c}")] for c,n in TEAM_NAMES.items()]
        await msg.reply_text("🔔 *Choose your team:*", parse_mode="Markdown",
                             reply_markup=InlineKeyboardMarkup(buttons)); return
    team = ctx.args[0].upper()
    if team not in TEAM_NAMES:
        await msg.reply_text(f"❌ Unknown code. Try: {', '.join(TEAM_NAMES)}"); return
    db_subscribe(update.effective_chat.id, team, update.effective_user.username or "")
    await msg.reply_text(f"✅ Subscribed to *{TEAM_NAMES[team]}* alerts!", parse_mode="Markdown")

async def cmd_unsubscribe(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    cur = db_get_subscription(chat_id)
    if not cur:
        await update.message.reply_text("You are not subscribed to any alerts."); return
    db_unsubscribe(chat_id)
    await update.message.reply_text(f"🔕 Unsubscribed from *{TEAM_NAMES.get(cur,cur)}*.", parse_mode="Markdown")

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "🏏 *IPL Bot Commands*\n\n"
        "*📡 Live Cricket*\n"
        "/score — Live IPL scores\n"
        "/today — Today's fixtures\n"
        "/table — Points table\n"
        "/result — Latest result\n"
        "/subscribe \\[TEAM\\] — Team alerts\n"
        "/unsubscribe — Stop alerts\n\n"
        "*🎮 Mini Cricket Game*\n"
        "/play — Start a new game\n"
        "/bat — Choose to bat first\n"
        "/bowl — Choose to bowl first\n"
        "/shoot \\[1\\-6\\] — Play a shot or delivery\n"
        "/profile — Your stats & rewards\n"
        "/leaderboard — Top 10 players\n"
        "/rewards — View reward settings\n\n"
        "*👑 Owner Only*\n"
        "/setreward \\[points\\] — Set skill point reward\n"
        "/setyen \\[amount\\] — Set Yen reward\n\n"
        "*Team codes:* MI, CSK, RCB, KKR, DC, PBKS, RR, SRH, GT, LSG"
    )
    await update.message.reply_text(text, parse_mode="MarkdownV2")


# ─────────────────────────────────────────────
#  MINI CRICKET GAME HANDLERS
# ─────────────────────────────────────────────

MAX_WICKETS = 10
MAX_OVERS   = 10   # 10 overs = 60 balls per innings

def overs_str(balls):
    return f"{balls // 6}.{balls % 6}"

def number_keyboard(prompt="Pick a number:"):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(str(i), callback_data=f"shoot_{i}") for i in range(1, 4)
    ],[
        InlineKeyboardButton(str(i), callback_data=f"shoot_{i}") for i in range(4, 7)
    ]])

async def cmd_play(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Start a new mini cricket game."""
    chat_id = update.effective_chat.id
    user    = update.effective_user
    db_ensure_player(chat_id, user.username or user.first_name)

    # Clear any existing game
    db_delete_game(chat_id)
    db_set_game(chat_id, role="", phase="choose_role", player_runs=0, bot_runs=0,
                player_wickets=0, bot_wickets=0, balls_played=0, target=0, state="choose_role")

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🏏 Bat First", callback_data="game_bat"),
        InlineKeyboardButton("🎳 Bowl First", callback_data="game_bowl"),
    ]])
    await (update.message or update.callback_query.message).reply_text(
        "🏏 *Mini Cricket — New Match!*\n\n"
        "You vs 🤖 Bot\n"
        "📋 Rules:\n"
        "• Pick a number 1–6 each ball\n"
        "• Bot picks 1–6 randomly\n"
        "• *Same number = OUT / WICKET!*\n"
        "• 10 overs (60 balls) or 10 wickets per innings\n\n"
        "Do you want to bat or bowl first?",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

async def cmd_bat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    game    = db_get_game(chat_id)
    if not game:
        await update.message.reply_text("No active game. Use /play to start!"); return
    db_set_game(chat_id, role="bat", phase="batting", state="playing")
    await update.message.reply_text(
        "✅ You chose to *bat first*!\n\n"
        "🏏 Your innings begins. Pick a number 1–6:",
        parse_mode="Markdown",
        reply_markup=number_keyboard(),
    )

async def cmd_bowl(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    game    = db_get_game(chat_id)
    if not game:
        await update.message.reply_text("No active game. Use /play to start!"); return
    db_set_game(chat_id, role="bowl", phase="bowling", state="playing")
    await update.message.reply_text(
        "✅ You chose to *bowl first*!\n\n"
        "🎳 Bot bats first. Pick a delivery number 1–6:",
        parse_mode="Markdown",
        reply_markup=number_keyboard(),
    )

async def cmd_shoot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /shoot N command (text-based play)."""
    chat_id = update.effective_chat.id
    if not ctx.args or not ctx.args[0].isdigit():
        await update.message.reply_text("Usage: /shoot [1-6]"); return
    n = int(ctx.args[0])
    if n < 1 or n > 6:
        await update.message.reply_text("Pick a number between 1 and 6."); return
    await process_shot(update, ctx, n, via_callback=False)

async def process_shot(update: Update, ctx: ContextTypes.DEFAULT_TYPE, player_pick: int, via_callback=False):
    """Core game logic for each ball."""
    chat_id = update.effective_chat.id
    msg     = update.message if not via_callback else update.callback_query.message
    game    = db_get_game(chat_id)

    if not game or game[9] != "playing":
        await msg.reply_text("No active game. Start with /play!"); return

    # Unpack game row
    # (chat_id, role, phase, player_runs, bot_runs, player_wickets, bot_wickets, balls_played, target, state)
    _, role, phase, player_runs, bot_runs, player_wickets, bot_wickets, balls_played, target, state = game

    bot_pick = random.randint(1, 6)
    is_out   = (player_pick == bot_pick)
    response_lines = []

    if phase == "batting":
        # ── PLAYER BATTING ──────────────────
        commentary = random.choice(BOWL_COMMENTARY)
        response_lines.append(f"🎳 Bot bowls: *{bot_pick}* — {commentary}")
        response_lines.append(f"🏏 You played: *{player_pick}*\n")

        if is_out:
            player_wickets += 1
            response_lines.append(f"💥 *OUT!* ({player_wickets} wicket{'s' if player_wickets>1 else ''})")
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

        response_lines.append(f"\n📊 Score: *{player_runs}/{player_wickets}* ({overs_str(balls_played)} ov)")
        if balls_played % 6 == 0:
            response_lines.append(f"🔔 Over {balls_played//6} complete!")

    elif phase == "bowling":
        # ── PLAYER BOWLING (bot bats) ────────
        response_lines.append(f"🏏 Bot plays: *{bot_pick}*")
        response_lines.append(f"🎳 You bowled: *{player_pick}*\n")

        if is_out:
            bot_wickets += 1
            response_lines.append(f"💥 *WICKET!* Bot: {bot_wickets} out")
            if bot_wickets >= MAX_WICKETS:
                response_lines.append(f"\n🤖 Bot All Out! Bot scored: *{bot_runs}/{bot_wickets}* ({overs_str(balls_played)} ov)")
                await msg.reply_text("\n".join(response_lines), parse_mode="Markdown")
                await start_second_innings(msg, chat_id, player_runs, player_wickets, bot_runs, bot_wickets, balls_played, role)
                return
        else:
            bot_runs += bot_pick
            response_lines.append(f"🤖 Bot scores {bot_pick}. {'SIX! 💥' if bot_pick==6 else 'FOUR! 🏏' if bot_pick==4 else 'Good shot.'}")

        # Check if bot already chasing — target exceeded
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

        response_lines.append(f"\n🤖 Bot: *{bot_runs}/{bot_wickets}* ({overs_str(balls_played)} ov)")
        if target > 0:
            need = target - bot_runs + 1
            left = MAX_OVERS*6 - balls_played
            response_lines.append(f"🎯 Bot needs *{need}* off *{left}* balls")
        if balls_played % 6 == 0:
            response_lines.append(f"🔔 Over {balls_played//6} complete!")

    elif phase == "batting2":
        # ── PLAYER CHASING ──────────────────
        commentary = random.choice(BOWL_COMMENTARY)
        response_lines.append(f"🎳 Bot bowls: *{bot_pick}* — {commentary}")
        response_lines.append(f"🏏 You played: *{player_pick}*\n")

        if is_out:
            player_wickets += 1
            response_lines.append(f"💥 *OUT!* ({player_wickets} wickets)")
            if player_wickets >= MAX_WICKETS:
                response_lines.append(f"All Out! You scored: *{player_runs}/{player_wickets}*")
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
                response_lines.append(f"🎉 *You Win!* Reached target!")
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
        response_lines.append(f"\n📊 You: *{player_runs}/{player_wickets}* ({overs_str(balls_played)} ov)")
        response_lines.append(f"🎯 Need *{need}* off *{left}* balls")

    elif phase == "bowling2":
        # ── BOT CHASING, PLAYER BOWLING ─────
        response_lines.append(f"🏏 Bot plays: *{bot_pick}*")
        response_lines.append(f"🎳 You bowled: *{player_pick}*\n")

        if is_out:
            bot_wickets += 1
            response_lines.append(f"💥 *WICKET!* Bot: {bot_wickets} out")
            if bot_wickets >= MAX_WICKETS:
                db_set_game(chat_id, bot_wickets=bot_wickets)
                await msg.reply_text("\n".join(response_lines), parse_mode="Markdown")
                await end_game(msg, chat_id, player_runs, bot_runs, player_wickets, bot_wickets, role)
                return
        else:
            bot_runs += bot_pick
            response_lines.append(f"🤖 Bot scores {bot_pick}.")
            if bot_runs > target:
                db_set_game(chat_id, bot_runs=bot_runs, bot_wickets=bot_wickets)
                response_lines.append("🤖 Bot reached target!")
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
        response_lines.append(f"\n🤖 Bot: *{bot_runs}/{bot_wickets}* ({overs_str(balls_played)} ov)")
        response_lines.append(f"🎯 Bot needs *{need}* off *{left}* balls")

    await msg.reply_text("\n".join(response_lines), parse_mode="Markdown",
                         reply_markup=number_keyboard())


async def start_second_innings(msg, chat_id, player_runs, player_wickets, bot_runs, bot_wickets, balls_played, role):
    """Switch to the second innings."""
    if role == "bat":
        # Player batted first → bot now chases
        target = player_runs
        db_set_game(chat_id, phase="bowling2", balls_played=0,
                    target=target, bot_runs=0, bot_wickets=0, state="playing")
        need = target + 1
        await msg.reply_text(
            f"🔄 *2nd Innings — Bot Chases!*\n\n"
            f"Your score: *{player_runs}/{player_wickets}*\n"
            f"🎯 Bot needs *{need}* to win\n\n"
            f"🎳 Pick your delivery (1–6):",
            parse_mode="Markdown",
            reply_markup=number_keyboard(),
        )
    else:
        # Player bowled first → player now chases bot's score
        target = bot_runs
        db_set_game(chat_id, phase="batting2", balls_played=0,
                    target=target, player_runs=0, player_wickets=0, state="playing")
        need = target + 1
        await msg.reply_text(
            f"🔄 *2nd Innings — You Chase!*\n\n"
            f"Bot's score: *{bot_runs}/{bot_wickets}*\n"
            f"🎯 You need *{need}* to win\n\n"
            f"🏏 Pick your shot (1–6):",
            parse_mode="Markdown",
            reply_markup=number_keyboard(),
        )


async def end_game(msg, chat_id, player_runs, bot_runs, player_wickets, bot_wickets, role):
    """Declare winner, award rewards, clean up."""
    db_delete_game(chat_id)

    win_sp  = int(db_get_setting("win_skill_points") or DEFAULT_WIN_SKILL_POINTS)
    win_yen = int(db_get_setting("win_yen") or DEFAULT_WIN_YEN)

    # Determine winner
    # If player batted first: player_runs vs bot_runs (bot was chasing)
    # If player bowled first: bot_runs vs player_runs (player was chasing)
    player_won = player_runs > bot_runs

    margin = abs(player_runs - bot_runs)

    scoreboard = (
        f"📋 *Match Summary*\n\n"
        f"🏏 You: *{player_runs}* runs\n"
        f"🤖 Bot: *{bot_runs}* runs\n"
    )

    if player_won:
        db_add_win(chat_id, win_sp, win_yen, player_runs, player_wickets)
        result = (
            f"🎉 *YOU WIN!* by *{margin}* runs\n\n"
            + scoreboard +
            f"\n🏅 *Rewards Earned:*\n"
            f"⭐ Skill Points: *+{win_sp}*\n"
            f"💴 Yen: *+{win_yen}*\n\n"
            f"Use /profile to see your total rewards!"
        )
    else:
        db_add_loss(chat_id, player_runs, player_wickets)
        result = (
            f"😔 *Bot Wins* by *{margin}* runs\n\n"
            + scoreboard +
            f"\nBetter luck next time! Use /play to try again."
        )

    play_again = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 Play Again", callback_data="play"),
        InlineKeyboardButton("🏅 Leaderboard", callback_data="leaderboard"),
    ]])
    await msg.reply_text(result, parse_mode="Markdown", reply_markup=play_again)


async def cmd_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Show player profile and stats."""
    chat_id = update.effective_chat.id
    msg     = update.message or update.callback_query.message
    db_ensure_player(chat_id, update.effective_user.username or update.effective_user.first_name)
    p = db_get_player(chat_id)
    if not p:
        await msg.reply_text("Profile not found. Use /play to start playing!"); return

    _, username, sp, yen, wins, losses, runs, wickets = p
    total = wins + losses
    wr    = f"{wins/total*100:.0f}%" if total > 0 else "N/A"

    win_sp  = db_get_setting("win_skill_points") or DEFAULT_WIN_SKILL_POINTS
    win_yen = db_get_setting("win_yen") or DEFAULT_WIN_YEN

    await msg.reply_text(
        f"👤 *Player Profile: {username}*\n\n"
        f"⭐ Skill Points: *{sp}*\n"
        f"💴 Yen: *{yen}*\n\n"
        f"🏆 Wins: *{wins}* | Losses: *{losses}*\n"
        f"📈 Win Rate: *{wr}*\n"
        f"🏏 Total Runs Scored: *{runs}*\n"
        f"🎳 Total Wickets Taken: *{wickets}*\n\n"
        f"💡 Win reward: *{win_sp} SP* + *{win_yen} Yen* per match",
        parse_mode="Markdown",
    )


async def cmd_leaderboard(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Show top 10 players by skill points."""
    msg  = update.message or update.callback_query.message
    rows = db_get_leaderboard()
    if not rows:
        await msg.reply_text("No players yet. Use /play to start!"); return

    medals = ["🥇","🥈","🥉"] + ["🏅"]*7
    lines  = ["🏆 *IPL Bot Leaderboard*\n"]
    for i, (username, sp, yen, wins, losses) in enumerate(rows):
        name = username or "Unknown"
        lines.append(f"{medals[i]} *{name}* — ⭐{sp} SP | 💴{yen} Yen | {wins}W/{losses}L")

    await msg.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_rewards(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Show current reward settings."""
    sp  = db_get_setting("win_skill_points") or DEFAULT_WIN_SKILL_POINTS
    yen = db_get_setting("win_yen") or DEFAULT_WIN_YEN
    await (update.message or update.callback_query.message).reply_text(
        f"🎁 *Current Game Rewards*\n\n"
        f"🏆 Win reward:\n"
        f"  ⭐ Skill Points: *{sp}*\n"
        f"  💴 Yen: *{yen}*\n\n"
        f"_(Only the bot owner can change these)_",
        parse_mode="Markdown",
    )


# ─────────────────────────────────────────────
#  OWNER-ONLY COMMANDS
# ─────────────────────────────────────────────

async def cmd_setreward(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """OWNER: Set skill point reward for winning."""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ Only the bot owner can use this command."); return
    if not ctx.args or not ctx.args[0].isdigit():
        await update.message.reply_text("Usage: /setreward [points]\nExample: /setreward 100"); return
    pts = int(ctx.args[0])
    db_set_setting("win_skill_points", pts)
    await update.message.reply_text(
        f"✅ Win reward updated!\n⭐ Skill Points per win: *{pts}*",
        parse_mode="Markdown"
    )

async def cmd_setyen(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """OWNER: Set Yen reward for winning."""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ Only the bot owner can use this command."); return
    if not ctx.args or not ctx.args[0].isdigit():
        await update.message.reply_text("Usage: /setyen [amount]\nExample: /setyen 500"); return
    yen = int(ctx.args[0])
    db_set_setting("win_yen", yen)
    await update.message.reply_text(
        f"✅ Win reward updated!\n💴 Yen per win: *{yen}*",
        parse_mode="Markdown"
    )


# ─────────────────────────────────────────────
#  INLINE KEYBOARD CALLBACK ROUTER
# ─────────────────────────────────────────────

async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "score":          await cmd_score(update, ctx)
    elif data == "today":        await cmd_today(update, ctx)
    elif data == "table":        await cmd_table(update, ctx)
    elif data == "result":       await cmd_result(update, ctx)
    elif data == "play":         await cmd_play(update, ctx)
    elif data == "leaderboard":  await cmd_leaderboard(update, ctx)
    elif data == "profile":      await cmd_profile(update, ctx)
    elif data == "game_bat":
        chat_id = update.effective_chat.id
        db_set_game(chat_id, role="bat", phase="batting", state="playing")
        await query.message.reply_text(
            "✅ You chose to *bat first*!\n\n🏏 Pick a shot (1–6):",
            parse_mode="Markdown",
            reply_markup=number_keyboard(),
        )
    elif data == "game_bowl":
        chat_id = update.effective_chat.id
        db_set_game(chat_id, role="bowl", phase="bowling", state="playing")
        await query.message.reply_text(
            "✅ You chose to *bowl first*!\n\n🎳 Pick a delivery (1–6):",
            parse_mode="Markdown",
            reply_markup=number_keyboard(),
        )
    elif data.startswith("shoot_"):
        n = int(data.split("_")[1])
        await process_shot(update, ctx, n, via_callback=True)
    elif data.startswith("sub_"):
        team     = data[4:]
        chat_id  = update.effective_chat.id
        username = update.effective_user.username or ""
        db_subscribe(chat_id, team, username)
        await query.message.reply_text(
            f"✅ Subscribed to *{TEAM_NAMES.get(team, team)}* alerts!",
            parse_mode="Markdown",
        )
    elif data == "subscribe_menu":
        buttons = [[InlineKeyboardButton(n, callback_data=f"sub_{c}")] for c,n in TEAM_NAMES.items()]
        await query.message.reply_text("🔔 Choose your team:",
                                       reply_markup=InlineKeyboardMarkup(buttons))


# ─────────────────────────────────────────────
#  AUTO-ALERT JOB
# ─────────────────────────────────────────────

async def alert_job(ctx: ContextTypes.DEFAULT_TYPE):
    subscribers = db_get_all_subscribers()
    if not subscribers: return

    matches   = await fetch_live_matches()
    ipl_live  = [m for m in matches if is_ipl(m) and not m.get("matchEnded")]
    ipl_ended = [m for m in matches if is_ipl(m) and m.get("matchEnded")]

    team_match_map = {}
    for m in ipl_live + ipl_ended:
        for team in m.get("teams", []):
            for code, full in TEAM_NAMES.items():
                if code.lower() in team.lower() or full.lower() in team.lower():
                    team_match_map[code] = m

    for chat_id, team_code in subscribers:
        match = team_match_map.get(team_code)
        if not match: continue

        match_id  = match.get("id","")
        scores    = match.get("score", [])
        score_str = "|".join(f"{s.get('r')}/{s.get('w')}({s.get('o')})" for s in scores)
        last      = db_get_last_score(match_id)

        if match.get("matchEnded") and last != "ENDED":
            db_set_last_score(match_id, "ENDED")
            try:
                await ctx.bot.send_message(chat_id=chat_id,
                    text=f"🏆 *Match Over!*\n\n{format_score_block(match)}",
                    parse_mode="Markdown")
            except Exception as e:
                logger.warning(f"Alert failed {chat_id}: {e}")
            continue

        if score_str and score_str != last:
            db_set_last_score(match_id, score_str)
            if last is None:
                try:
                    await ctx.bot.send_message(chat_id=chat_id,
                        text=f"🏏 *Match Started!*\n{TEAM_NAMES.get(team_code,team_code)} are playing!\n\n{format_score_block(match)}",
                        parse_mode="Markdown")
                except Exception as e:
                    logger.warning(f"Alert failed {chat_id}: {e}")
            else:
                try:
                    prev_w = sum(int(p.split("/")[1].split("(")[0]) for p in last.split("|") if "/" in p)
                    curr_w = sum(s.get("w",0) for s in scores)
                    if curr_w > prev_w:
                        await ctx.bot.send_message(chat_id=chat_id,
                            text=f"🚨 *WICKET!* ({TEAM_NAMES.get(team_code,team_code)})\n\n{format_score_block(match)}",
                            parse_mode="Markdown")
                except Exception as e:
                    logger.warning(f"Alert failed {chat_id}: {e}")


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

async def post_init(app: Application):
    await app.bot.set_my_commands([
        BotCommand("start",       "Welcome & main menu"),
        BotCommand("score",       "Live IPL scores"),
        BotCommand("today",       "Today's fixtures"),
        BotCommand("table",       "Points table"),
        BotCommand("result",      "Latest result"),
        BotCommand("subscribe",   "Subscribe to team alerts"),
        BotCommand("unsubscribe", "Stop alerts"),
        BotCommand("play",        "Start mini cricket game"),
        BotCommand("bat",         "Bat first in game"),
        BotCommand("bowl",        "Bowl first in game"),
        BotCommand("shoot",       "Play a shot /shoot [1-6]"),
        BotCommand("profile",     "Your stats & rewards"),
        BotCommand("leaderboard", "Top 10 players"),
        BotCommand("rewards",     "Current reward settings"),
        BotCommand("setreward",   "[Owner] Set skill point reward"),
        BotCommand("setyen",      "[Owner] Set Yen reward"),
        BotCommand("help",        "All commands"),
    ])

def main():
    db_init()
    logger.info("🏏 IPL Bot with Mini Cricket Game starting...")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # IPL handlers
    app.add_handler(CommandHandler("start",       cmd_start))
    app.add_handler(CommandHandler("score",       cmd_score))
    app.add_handler(CommandHandler("today",       cmd_today))
    app.add_handler(CommandHandler("table",       cmd_table))
    app.add_handler(CommandHandler("result",      cmd_result))
    app.add_handler(CommandHandler("subscribe",   cmd_subscribe))
    app.add_handler(CommandHandler("unsubscribe", cmd_unsubscribe))
    app.add_handler(CommandHandler("help",        cmd_help))

    # Game handlers
    app.add_handler(CommandHandler("play",        cmd_play))
    app.add_handler(CommandHandler("bat",         cmd_bat))
    app.add_handler(CommandHandler("bowl",        cmd_bowl))
    app.add_handler(CommandHandler("shoot",       cmd_shoot))
    app.add_handler(CommandHandler("profile",     cmd_profile))
    app.add_handler(CommandHandler("leaderboard", cmd_leaderboard))
    app.add_handler(CommandHandler("rewards",     cmd_rewards))

    # Owner commands
    app.add_handler(CommandHandler("setreward",   cmd_setreward))
    app.add_handler(CommandHandler("setyen",      cmd_setyen))

    # Inline keyboard
    app.add_handler(CallbackQueryHandler(button_handler))

    # Auto-alert job
    app.job_queue.run_repeating(alert_job, interval=ALERT_INTERVAL, first=10)

    logger.info("✅ Bot running! Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
  
