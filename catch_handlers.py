"""
handlers/catch_handlers.py  –  Spawn & catch mechanics
"""

import random
import asyncio
import time
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

import database as db
from config import (
    SPAWN_CHANCE, SPAWN_COOLDOWN_SEC, CATCH_WINDOW_SEC,
    RARITY_WEIGHTS, DAILY_COINS
)

# group_id → timestamp of last spawn
_last_spawn: dict[int, float] = {}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _pick_random_character():
    """Pick a random character weighted by rarity."""
    all_chars = db.get_all_characters()
    if not all_chars:
        return None

    # Build weight list
    weights = []
    for ch in all_chars:
        rarity = ch["rarity"]
        w = next((v for k, v in RARITY_WEIGHTS.items() if k == rarity), 10)
        weights.append(w)

    return random.choices(all_chars, weights=weights, k=1)[0]


def _spawn_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🎯  /catch", callback_data="catch_btn")
    ]])


async def _do_spawn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Actually send the spawn message for a random character."""
    group_id = update.effective_chat.id
    char = _pick_random_character()
    if char is None:
        return

    _last_spawn[group_id] = time.time()

    rarity_emoji = char["rarity"].split()[0]
    caption = (
        f"✨ *A wild character appeared!*\n\n"
        f"🎴 **Name:** `???`\n"
        f"📺 **Anime:** `???`\n"
        f"{rarity_emoji} **Rarity:** {char['rarity']}\n\n"
        f"⚡ Quick! Use /catch to grab them!\n"
        f"⏳ They'll disappear in {CATCH_WINDOW_SEC}s!"
    )

    try:
        if char["image_url"]:
            msg = await context.bot.send_photo(
                chat_id=group_id,
                photo=char["image_url"],
                caption=caption,
                parse_mode="Markdown",
                reply_markup=_spawn_keyboard()
            )
        else:
            msg = await context.bot.send_message(
                chat_id=group_id,
                text=caption,
                parse_mode="Markdown",
                reply_markup=_spawn_keyboard()
            )
    except Exception as e:
        return

    db.set_spawn(group_id, char["id"], msg.message_id)

    # Auto-expire after CATCH_WINDOW_SEC
    async def expire():
        await asyncio.sleep(CATCH_WINDOW_SEC)
        spawn = db.get_spawn(group_id)
        if spawn and spawn["char_id"] == char["id"]:
            db.clear_spawn(group_id)
            try:
                await context.bot.edit_message_caption(
                    chat_id=group_id,
                    message_id=msg.message_id,
                    caption=f"😢 *{char['name']}* ran away! Nobody caught them in time.",
                    parse_mode="Markdown"
                )
            except:
                pass

    asyncio.create_task(expire())


# ─────────────────────────────────────────────────────────────────────────────
# Message trigger (auto-spawn)
# ─────────────────────────────────────────────────────────────────────────────
async def message_spawn_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = update.effective_chat.id
    now = time.time()
    last = _last_spawn.get(group_id, 0)

    if (now - last) < SPAWN_COOLDOWN_SEC:
        return  # Cooldown active

    if random.random() < SPAWN_CHANCE:
        await _do_spawn(update, context)


# ─────────────────────────────────────────────────────────────────────────────
# /catch command
# ─────────────────────────────────────────────────────────────────────────────
async def catch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    chat    = update.effective_chat
    group_id = chat.id

    if chat.type == "private":
        await update.message.reply_text("❌ /catch only works in group chats!")
        return

    # Check ban
    db.ensure_user(user.id, user.username, user.first_name)
    u = db.get_user(user.id)
    if u and u["banned"]:
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return

    spawn = db.get_spawn(group_id)
    if not spawn:
        await update.message.reply_text(
            "🌀 There's no character to catch right now!\n"
            "Wait for one to appear in the chat.",
            parse_mode="Markdown"
        )
        return

    char = db.get_character(spawn["char_id"])
    if not char:
        db.clear_spawn(group_id)
        await update.message.reply_text("❌ That character no longer exists.")
        return

    # Mark as caught
    db.mark_caught(group_id, user.id)
    db.add_to_collection(user.id, char["id"])
    db.increment_catches(user.id)
    db.update_coins(user.id, 20)  # reward coins on catch

    is_dupe = db.count_collection(user.id) > 1 and \
              len([r for r in db.get_collection(user.id, per_page=9999) if r["char_id"] == char["id"]]) > 1

    mention = f"[{user.first_name}](tg://user?id={user.id})"

    caption = (
        f"🎉 *{mention} caught a character!*\n\n"
        f"🎴 **Name:** {char['name']}\n"
        f"📺 **Anime:** {char['anime']}\n"
        f"{char['rarity']}\n"
        f"💰 **+20 coins** earned!\n"
    )
    if is_dupe:
        caption += f"\n♻️ _(Duplicate — use /burn to get coins!)_"

    try:
        await update.message.reply_text(caption, parse_mode="Markdown")
        # Try to edit original spawn message
        if spawn["message_id"]:
            await context.bot.edit_message_caption(
                chat_id=group_id,
                message_id=spawn["message_id"],
                caption=f"✅ Caught by {user.first_name}!",
            )
    except:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Inline button catch
# ─────────────────────────────────────────────────────────────────────────────
async def catch_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the inline [🎯 /catch] button press."""
    query = update.callback_query
    user  = query.from_user
    chat  = query.message.chat
    group_id = chat.id

    await query.answer()  # acknowledge button press

    db.ensure_user(user.id, user.username, user.first_name)
    u = db.get_user(user.id)
    if u and u["banned"]:
        await query.answer("🚫 You are banned.", show_alert=True)
        return

    spawn = db.get_spawn(group_id)
    if not spawn:
        await query.answer("😢 Too late! Character already escaped.", show_alert=True)
        return

    char = db.get_character(spawn["char_id"])
    if not char:
        await query.answer("❌ Character not found.", show_alert=True)
        return

    db.mark_caught(group_id, user.id)
    db.add_to_collection(user.id, char["id"])
    db.increment_catches(user.id)
    db.update_coins(user.id, 20)

    mention = f"[{user.first_name}](tg://user?id={user.id})"
    text = (
        f"🎉 *{mention} caught **{char['name']}**!*\n"
        f"📺 {char['anime']} • {char['rarity']}\n"
        f"💰 +20 coins earned!"
    )
    try:
        await query.edit_message_caption(caption=text, parse_mode="Markdown")
    except:
        try:
            await query.edit_message_text(text=text, parse_mode="Markdown")
        except:
            pass