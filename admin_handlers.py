"""
handlers/admin_handlers.py  –  Admin-only commands
Every command shows full usage + example when called incorrectly.
"""

import random
import string
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes

import database as db
from config import ADMIN_IDS, RARITY_WEIGHTS


# ── Helpers ────────────────────────────────────────────────────────────────
def _is_admin(uid): return uid in ADMIN_IDS

def _admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not _is_admin(update.effective_user.id):
            await update.message.reply_text("🚫 *Admin only command.*", parse_mode="Markdown")
            return
        return await func(update, context)
    return wrapper

def _resolve_rarity(s):
    s = s.lower().strip()
    for r in RARITY_WEIGHTS:
        if r.split(" ",1)[-1].lower() == s or r.lower() == s:
            return r
    return None

def _gen_code(n=8):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))

def _usage(cmd, desc, syntax, example, notes=""):
    return (
        f"📋 */{cmd}* — {desc}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"*Syntax:*\n`{syntax}`\n\n"
        f"*Example:*\n`{example}`"
        + (f"\n\n*Notes:*\n{notes}" if notes else "")
    )


# ══════════════════════════════════════════════════════════════════════════════
# /adminhelp  —  Admin command reference (admin only)
# ══════════════════════════════════════════════════════════════════════════════
@_admin_only
async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛡 *Admin Command Reference*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"

        "🎴 *Characters*\n"
        "  /addchar `Name|Anime|Rarity` _(reply to image)_\n"
        "  /addimage `<id>` _(send photo with this caption)_\n"
        "  /editchar `<id> <field> <value>`\n"
        "  /delchar `<id>`\n"
        "  /listchars\n\n"

        "👑 *Custom Waifus*\n"
        "  /customwaifu `<user_id> <name> | <anime> | <reason>`\n"
        "  /customimage `<char_id>` _(send photo with this caption)_\n"
        "  /customlist — list all custom waifus\n\n"

        "🎟 *Redeem Codes*\n"
        "  /gencode `<coins> [uses] [Xd] [char:<id>]`\n"
        "  /codes — list all codes\n"
        "  /delcode `<CODE>`\n\n"

        "⚙️ *Management*\n"
        "  /spawn — force-spawn in group\n"
        "  /givecoins `<user_id> <amount>`\n"
        "  /givechar `<user_id> <char_id>`\n"
        "  /ban `<user_id>`\n"
        "  /unban `<user_id>`\n"
        "  /broadcast `<message>`\n"
        "  /stats\n\n"

        "💡 Type any command without arguments to see its full usage & example.",
        parse_mode="Markdown"
    )


# ══════════════════════════════════════════════════════════════════════════════
# /addchar
# ══════════════════════════════════════════════════════════════════════════════
@_admin_only
async def add_character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    USAGE = _usage(
        "addchar", "Add a new character",
        "/addchar Name|Anime|Rarity",
        "/addchar Rem|Re:Zero|Rare",
        f"• Reply to an image to attach it\n"
        f"• Or add URL: `Name|Anime|Rarity|https://img.url`\n"
        f"• Valid rarities: {', '.join(r.split()[-1] for r in RARITY_WEIGHTS)}"
    )

    if not context.args:
        await update.message.reply_text(USAGE, parse_mode="Markdown"); return

    raw   = " ".join(context.args)
    parts = [p.strip() for p in raw.split("|")]
    image_url = None

    if len(parts) == 4:
        name, anime, rarity, image_url = parts
    elif len(parts) == 3:
        name, anime, rarity = parts
    else:
        await update.message.reply_text(
            f"❌ Wrong format.\n\n{USAGE}", parse_mode="Markdown"
        ); return

    rarity = _resolve_rarity(rarity)
    if not rarity:
        await update.message.reply_text(
            f"❌ Invalid rarity.\n\n{USAGE}", parse_mode="Markdown"
        ); return

    if update.message.reply_to_message and update.message.reply_to_message.photo:
        image_url = update.message.reply_to_message.photo[-1].file_id

    char_id = db.add_character(name, anime, rarity, image_url, update.effective_user.id)
    img_note = "🖼 Image attached" if image_url else "⚠️ No image — use: send photo with caption `/addimage " + str(char_id) + "`"

    await update.message.reply_text(
        f"✅ *Character Added!*\n\n"
        f"🆔 ID: `{char_id}`\n"
        f"🎴 *{name}* — _{anime}_\n"
        f"{rarity}\n{img_note}",
        parse_mode="Markdown"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Photo handler for /addimage  and  /customimage
# ══════════════════════════════════════════════════════════════════════════════
async def add_image_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id): return
    msg = update.message
    if not msg.caption: return

    cap   = msg.caption.strip()
    parts = cap.split()
    cmd   = parts[0].lower()

    if cmd not in ("/addimage", "/customimage"): return

    if len(parts) < 2:
        await msg.reply_text(
            f"ℹ️ *Usage:* Send a photo with caption `{cmd} <char_id>`\n*Example:* `{cmd} 5`",
            parse_mode="Markdown"
        ); return

    try:
        char_id = int(parts[1])
    except ValueError:
        await msg.reply_text(f"❌ Invalid ID.\n*Example:* `{cmd} 5`", parse_mode="Markdown"); return

    char = db.get_character(char_id)
    if not char:
        await msg.reply_text("❌ Character not found."); return

    db.update_character(char_id, image_url=msg.photo[-1].file_id)
    await msg.reply_text(
        f"✅ Image updated for *{char['name']}* (`#{char_id}`)!", parse_mode="Markdown"
    )


# ══════════════════════════════════════════════════════════════════════════════
# /editchar
# ══════════════════════════════════════════════════════════════════════════════
@_admin_only
async def edit_character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    USAGE = _usage(
        "editchar", "Edit a character field",
        "/editchar <id> <field> <value>",
        "/editchar 5 name Sakura",
        "Fields: `name`, `anime`, `rarity`, `image_url`"
    )
    if len(context.args) < 3:
        await update.message.reply_text(USAGE, parse_mode="Markdown"); return

    try:
        char_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(f"❌ ID must be a number.\n\n{USAGE}", parse_mode="Markdown"); return

    field = context.args[1].lower()
    value = " ".join(context.args[2:])

    if field not in ("name","anime","rarity","image_url"):
        await update.message.reply_text(f"❌ Invalid field.\n\n{USAGE}", parse_mode="Markdown"); return
    if field == "rarity":
        value = _resolve_rarity(value)
        if not value:
            await update.message.reply_text(
                f"❌ Invalid rarity. Valid: {', '.join(RARITY_WEIGHTS.keys())}", parse_mode="Markdown"
            ); return

    char = db.get_character(char_id)
    if not char:
        await update.message.reply_text("❌ Character not found."); return

    db.update_character(char_id, **{field: value})
    await update.message.reply_text(
        f"✅ Updated `{field}` for *{char['name']}*\n→ `{value}`", parse_mode="Markdown"
    )


# ══════════════════════════════════════════════════════════════════════════════
# /delchar
# ══════════════════════════════════════════════════════════════════════════════
@_admin_only
async def delete_character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    USAGE = _usage("delchar","Delete a character","/delchar <id>","/delchar 5",
                   "⚠️ Removes the character from ALL player collections!")
    if not context.args:
        await update.message.reply_text(USAGE, parse_mode="Markdown"); return
    try:
        char_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(f"❌ ID must be a number.\n\n{USAGE}", parse_mode="Markdown"); return

    char = db.get_character(char_id)
    if not char:
        await update.message.reply_text("❌ Character not found."); return

    db.delete_character(char_id)
    await update.message.reply_text(
        f"🗑 Deleted *{char['name']}* (`#{char_id}`) and removed from all collections.",
        parse_mode="Markdown"
    )


# ══════════════════════════════════════════════════════════════════════════════
# /listchars
# ══════════════════════════════════════════════════════════════════════════════
@_admin_only
async def list_characters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chars = db.get_all_characters()
    if not chars:
        await update.message.reply_text("📭 No characters yet. Use /addchar to add some."); return

    lines = ["📋 *All Characters:*\n"]
    for c in chars:
        img = "🖼" if c["image_url"] else "❌"
        lines.append(f"`#{c['id']}` {img} *{c['name']}* — _{c['anime']}_ [{c['rarity'].split()[-1]}]")

    text = "\n".join(lines)
    for i in range(0, len(text), 4000):
        await update.message.reply_text(text[i:i+4000], parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# /customwaifu  —  Manually award a custom waifu to a user
# ══════════════════════════════════════════════════════════════════════════════
@_admin_only
async def custom_waifu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    USAGE = _usage(
        "customwaifu", "Award a custom exclusive waifu to a user",
        "/customwaifu <user_id> <Name> | <Anime> | <reason>",
        "/customwaifu 123456789 Sakura Miyamoto | Eternal Chronicles | special award",
        "• The character is marked Legendary + Custom\n"
        "• Only that user can own it\n"
        "• Use /customimage <char_id> to attach an image after"
    )
    if len(context.args) < 2:
        await update.message.reply_text(USAGE, parse_mode="Markdown"); return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(f"❌ user_id must be a number.\n\n{USAGE}", parse_mode="Markdown"); return

    rest  = " ".join(context.args[1:])
    parts = [p.strip() for p in rest.split("|")]

    if len(parts) < 2:
        await update.message.reply_text(f"❌ Wrong format.\n\n{USAGE}", parse_mode="Markdown"); return

    name   = parts[0]
    anime  = parts[1]
    reason = parts[2] if len(parts) > 2 else "admin award"

    target = db.get_user(user_id)
    if not target:
        await update.message.reply_text("❌ User not found. They must have used the bot at least once."); return

    char_id = db.add_character(
        name=name, anime=anime, rarity="🌠 Legendary",
        image_url=None, added_by=update.effective_user.id,
        is_custom=1, owner_id=user_id
    )
    db.add_to_collection(user_id, char_id)
    db.record_custom_award(user_id, char_id, reason)

    try:
        await context.bot.send_message(
            user_id,
            f"🎊 *You received an exclusive custom waifu!* 👑\n\n"
            f"🎴 *{name}*\n"
            f"📺 _{anime}_\n"
            f"🌠 Legendary (Custom)\n\n"
            f"_Awarded by admin. This character is exclusively yours!_",
            parse_mode="Markdown"
        )
    except:
        pass

    await update.message.reply_text(
        f"✅ *Custom Waifu Created & Awarded!*\n\n"
        f"🆔 Char ID: `{char_id}`\n"
        f"🎴 *{name}* — _{anime}_\n"
        f"👤 Awarded to: User `{user_id}`\n"
        f"📝 Reason: _{reason}_\n\n"
        f"💡 Add image: send photo with caption `/customimage {char_id}`",
        parse_mode="Markdown"
    )


# ══════════════════════════════════════════════════════════════════════════════
# /customlist  —  List all custom waifus
# ══════════════════════════════════════════════════════════════════════════════
@_admin_only
async def custom_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with db._conn() as con:
        rows = con.execute("""
            SELECT ch.id, ch.name, ch.anime, ch.owner_id, u.first_name,
                   ch.image_url, cwa.reason, cwa.awarded_at
            FROM characters ch
            LEFT JOIN custom_waifu_awards cwa ON cwa.char_id=ch.id
            LEFT JOIN users u ON u.user_id=ch.owner_id
            WHERE ch.is_custom=1
            ORDER BY cwa.awarded_at DESC
        """).fetchall()

    if not rows:
        await update.message.reply_text("📭 No custom waifus awarded yet."); return

    lines = [f"👑 *All Custom Waifus ({len(rows)}):*\n"]
    for r in rows:
        img    = "🖼" if r["image_url"] else "❌"
        owner  = r["first_name"] or f"User#{r['owner_id']}"
        reason = r["reason"] or "—"
        lines.append(f"`#{r['id']}` {img} *{r['name']}* — _{r['anime']}_\n   👤 {owner} | 📝 {reason}")

    text = "\n".join(lines)
    for i in range(0, len(text), 4000):
        await update.message.reply_text(text[i:i+4000], parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# /givecoins  —  Give coins to a user
# ══════════════════════════════════════════════════════════════════════════════
@_admin_only
async def give_coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    USAGE = _usage(
        "givecoins", "Give coins to a user",
        "/givecoins <user_id> <amount>",
        "/givecoins 123456789 1000",
        "Use negative amount to deduct coins"
    )
    if len(context.args) < 2:
        await update.message.reply_text(USAGE, parse_mode="Markdown"); return
    try:
        user_id = int(context.args[0])
        amount  = int(context.args[1])
    except ValueError:
        await update.message.reply_text(f"❌ Both values must be numbers.\n\n{USAGE}", parse_mode="Markdown"); return

    target = db.get_user(user_id)
    if not target:
        await update.message.reply_text("❌ User not found."); return

    db.update_coins(user_id, amount)
    new_bal = db.get_user(user_id)["coins"]
    sign    = "+" if amount >= 0 else ""
    await update.message.reply_text(
        f"✅ *Coins Updated!*\n"
        f"👤 User: `{user_id}` ({target['first_name']})\n"
        f"💰 Change: *{sign}{amount:,}*\n"
        f"💳 New balance: *{new_bal:,}*",
        parse_mode="Markdown"
    )
    try:
        msg = f"💰 An admin {'gave you' if amount >= 0 else 'deducted'} *{abs(amount):,} coins*!\nBalance: *{new_bal:,}*"
        await context.bot.send_message(user_id, msg, parse_mode="Markdown")
    except: pass


# ══════════════════════════════════════════════════════════════════════════════
# /givechar  —  Give a character to a user
# ══════════════════════════════════════════════════════════════════════════════
@_admin_only
async def give_char(update: Update, context: ContextTypes.DEFAULT_TYPE):
    USAGE = _usage(
        "givechar", "Give a character to a user",
        "/givechar <user_id> <char_id>",
        "/givechar 123456789 5"
    )
    if len(context.args) < 2:
        await update.message.reply_text(USAGE, parse_mode="Markdown"); return
    try:
        user_id = int(context.args[0])
        char_id = int(context.args[1])
    except ValueError:
        await update.message.reply_text(f"❌ Both values must be numbers.\n\n{USAGE}", parse_mode="Markdown"); return

    target = db.get_user(user_id)
    if not target:
        await update.message.reply_text("❌ User not found."); return
    char = db.get_character(char_id)
    if not char:
        await update.message.reply_text("❌ Character not found."); return

    db.add_to_collection(user_id, char_id)
    await update.message.reply_text(
        f"✅ Gave *{char['name']}* (`#{char_id}`) to user `{user_id}` ({target['first_name']}).",
        parse_mode="Markdown"
    )
    try:
        await context.bot.send_message(
            user_id,
            f"🎁 An admin gave you *{char['name']}*!\n{char['rarity']}\n"
            f"Check /collection to see it!",
            parse_mode="Markdown"
        )
    except: pass


# ══════════════════════════════════════════════════════════════════════════════
# /spawn  —  force-spawn in group
# ══════════════════════════════════════════════════════════════════════════════
@_admin_only
async def force_spawn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ Use this command inside a group chat."); return
    from handlers.catch_handlers import _do_spawn
    await _do_spawn(update, context)


# ══════════════════════════════════════════════════════════════════════════════
# /gencode
# ══════════════════════════════════════════════════════════════════════════════
@_admin_only
async def gen_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    USAGE = _usage(
        "gencode", "Generate a redeem code",
        "/gencode <coins> [uses] [Xd] [char:<id>]",
        "/gencode 500 10 7d",
        "• `coins` — how many coins the code gives\n"
        "• `uses` — how many times it can be used (default: 1)\n"
        "• `Xd` — expiry in X days, e.g. `7d` (optional)\n"
        "• `char:<id>` — also give a character, e.g. `char:5`\n\n"
        "More examples:\n"
        "`/gencode 0 1 0d char:3` — gives character only\n"
        "`/gencode 200 5` — 200 coins, 5 uses"
    )
    if not context.args:
        await update.message.reply_text(USAGE, parse_mode="Markdown"); return

    coins, max_uses, expires_at, char_id = 0, 1, None, None
    args = list(context.args)

    try:
        coins = int(args.pop(0))
    except ValueError:
        await update.message.reply_text(f"❌ First argument must be coin amount.\n\n{USAGE}", parse_mode="Markdown"); return

    for arg in args:
        if arg.isdigit():
            max_uses = int(arg)
        elif arg.endswith("d") and arg[:-1].isdigit():
            days = int(arg[:-1])
            if days > 0:
                expires_at = (datetime.utcnow() + timedelta(days=days)).isoformat()
        elif arg.lower().startswith("char:"):
            try:
                char_id = int(arg.split(":")[1])
                if not db.get_character(char_id):
                    await update.message.reply_text(f"❌ Character #{char_id} not found."); return
            except:
                await update.message.reply_text(f"❌ Invalid char format. Use `char:<id>`", parse_mode="Markdown"); return

    if coins == 0 and not char_id:
        await update.message.reply_text(f"❌ Code must give coins or a character.\n\n{USAGE}", parse_mode="Markdown"); return

    code = next(c for _ in range(10) if not db.get_redeem_code(c := _gen_code()))
    db.create_redeem_code(code, coins, char_id, max_uses, update.effective_user.id, expires_at)

    rewards = []
    if coins > 0: rewards.append(f"💰 {coins:,} coins")
    if char_id:
        char = db.get_character(char_id)
        rewards.append(f"🎴 {char['name']} ({char['rarity']})")

    exp = f"📅 Expires: {expires_at[:10]}" if expires_at else "📅 No expiry"
    await update.message.reply_text(
        f"🎟 *Code Generated!*\n\n"
        f"Code: `{code}`\n"
        f"Rewards: {' + '.join(rewards)}\n"
        f"Uses: {max_uses}\n{exp}\n\n"
        f"Share with users:\n`/redeem {code}`",
        parse_mode="Markdown"
    )


# ══════════════════════════════════════════════════════════════════════════════
# /codes
# ══════════════════════════════════════════════════════════════════════════════
@_admin_only
async def list_codes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    codes = db.get_all_redeem_codes()
    if not codes:
        await update.message.reply_text("📭 No codes yet. Use /gencode to create one."); return

    lines = [f"🎟 *All Redeem Codes ({len(codes)}):*\n"]
    for c in codes:
        status = "✅" if c["used_count"] < c["max_uses"] else "❌"
        char_text = ""
        if c["char_id"]:
            ch = db.get_character(c["char_id"])
            char_text = f" +🎴{ch['name']}" if ch else ""
        exp = f" exp:{c['expires_at'][:10]}" if c["expires_at"] else ""
        lines.append(
            f"{status} `{c['code']}` — 💰{c['coins']:,}{char_text} ({c['used_count']}/{c['max_uses']}){exp}"
        )
    text = "\n".join(lines)
    for i in range(0, len(text), 4000):
        await update.message.reply_text(text[i:i+4000], parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# /delcode
# ══════════════════════════════════════════════════════════════════════════════
@_admin_only
async def del_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    USAGE = _usage("delcode","Delete a redeem code","/delcode <CODE>","/delcode ABC12345")
    if not context.args:
        await update.message.reply_text(USAGE, parse_mode="Markdown"); return
    code = context.args[0].upper()
    if not db.get_redeem_code(code):
        await update.message.reply_text("❌ Code not found."); return
    db.delete_redeem_code(code)
    await update.message.reply_text(f"🗑 Code `{code}` deleted.", parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# /ban  /unban
# ══════════════════════════════════════════════════════════════════════════════
@_admin_only
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    USAGE = _usage("ban","Ban a user","/ban <user_id>","/ban 123456789")
    if not context.args:
        await update.message.reply_text(USAGE, parse_mode="Markdown"); return
    try: uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text(f"❌ user_id must be a number.\n\n{USAGE}", parse_mode="Markdown"); return
    db.ban_user(uid)
    await update.message.reply_text(f"🚫 User `{uid}` banned.", parse_mode="Markdown")


@_admin_only
async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    USAGE = _usage("unban","Unban a user","/unban <user_id>","/unban 123456789")
    if not context.args:
        await update.message.reply_text(USAGE, parse_mode="Markdown"); return
    try: uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text(f"❌ user_id must be a number.\n\n{USAGE}", parse_mode="Markdown"); return
    db.unban_user(uid)
    await update.message.reply_text(f"✅ User `{uid}` unbanned.", parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# /broadcast
# ══════════════════════════════════════════════════════════════════════════════
@_admin_only
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    USAGE = _usage("broadcast","Send a message to all users","/broadcast <message>","/broadcast Server maintenance at 10PM!")
    if not context.args:
        await update.message.reply_text(USAGE, parse_mode="Markdown"); return
    text     = " ".join(context.args)
    user_ids = db.get_all_user_ids()
    sent = failed = 0
    for uid in user_ids:
        try:
            await context.bot.send_message(uid, f"📢 *Announcement:*\n\n{text}", parse_mode="Markdown")
            sent += 1
        except:
            failed += 1
    await update.message.reply_text(f"📢 Done! ✅ {sent} sent · ❌ {failed} failed")


# ══════════════════════════════════════════════════════════════════════════════
# /stats
# ══════════════════════════════════════════════════════════════════════════════
@_admin_only
async def bot_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = db.get_stats()
    await update.message.reply_text(
        f"📊 *Bot Statistics*\n"
        f"━━━━━━━━━━━━\n"
        f"👥 Users: *{s['total_users']}*\n"
        f"🎴 Characters: *{s['total_characters']}*\n"
        f"👑 Custom Waifus: *{s['custom_waifus']}*\n"
        f"🎯 Total Catches: *{s['total_catches']}*\n"
        f"🤝 Completed Trades: *{s['total_trades']}*\n"
        f"🎟 Active Codes: *{s['active_codes']}*",
        parse_mode="Markdown"
    )