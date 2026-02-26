import logging
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, CallbackQueryHandler
)
from config import BOT_TOKEN
from handlers import user_handlers, admin_handlers, catch_handlers
from jobs import weekly_leaderboard

# ── 1. IMPORT KEEP ALIVE ──
from keep_alive import keep_alive

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


def main():
    # ── 2. START THE WEB SERVER ──
    # This runs the Flask server in a background thread before the bot starts.
    keep_alive()

    app = Application.builder().token(BOT_TOKEN).build()

    # ── User Commands ──────────────────────────────────────────────
    app.add_handler(CommandHandler("start",       user_handlers.start))
    app.add_handler(CommandHandler("help",        user_handlers.help_cmd))
    app.add_handler(CommandHandler("catch",       catch_handlers.catch))
    app.add_handler(CommandHandler("collection",  user_handlers.collection))
    app.add_handler(CommandHandler("characters",  user_handlers.browse_characters))
    app.add_handler(CommandHandler("profile",     user_handlers.profile))
    app.add_handler(CommandHandler("badges",      user_handlers.badges))
    app.add_handler(CommandHandler("top",         user_handlers.leaderboard))
    app.add_handler(CommandHandler("gift",        user_handlers.gift))
    app.add_handler(CommandHandler("daily",       user_handlers.daily))
    app.add_handler(CommandHandler("burn",        user_handlers.burn))
    app.add_handler(CommandHandler("search",      user_handlers.search))
    app.add_handler(CommandHandler("view",        user_handlers.view_character))
    app.add_handler(CommandHandler("trade",       user_handlers.trade))
    app.add_handler(CommandHandler("accept",      user_handlers.accept_trade))
    app.add_handler(CommandHandler("cancel",      user_handlers.cancel_trade))
    app.add_handler(CommandHandler("coinflip",    user_handlers.coinflip))
    app.add_handler(CommandHandler("duel",        user_handlers.duel))
    app.add_handler(CommandHandler("redeem",      user_handlers.redeem))

    # ── Admin Commands ─────────────────────────────────────────────
    app.add_handler(CommandHandler("adminhelp",   admin_handlers.admin_help))
    app.add_handler(CommandHandler("addchar",     admin_handlers.add_character))
    app.add_handler(CommandHandler("delchar",     admin_handlers.delete_character))
    app.add_handler(CommandHandler("editchar",    admin_handlers.edit_character))
    app.add_handler(CommandHandler("listchars",   admin_handlers.list_characters))
    app.add_handler(CommandHandler("customwaifu", admin_handlers.custom_waifu_cmd))
    app.add_handler(CommandHandler("customlist",  admin_handlers.custom_list))
    app.add_handler(CommandHandler("givecoins",   admin_handlers.give_coins))
    app.add_handler(CommandHandler("givechar",    admin_handlers.give_char))
    app.add_handler(CommandHandler("spawn",       admin_handlers.force_spawn))
    app.add_handler(CommandHandler("broadcast",   admin_handlers.broadcast))
    app.add_handler(CommandHandler("stats",       admin_handlers.bot_stats))
    app.add_handler(CommandHandler("ban",         admin_handlers.ban_user))
    app.add_handler(CommandHandler("unban",       admin_handlers.unban_user))
    app.add_handler(CommandHandler("gencode",     admin_handlers.gen_code))
    app.add_handler(CommandHandler("codes",       admin_handlers.list_codes))
    app.add_handler(CommandHandler("delcode",     admin_handlers.del_code))

    # ── Inline Callbacks ───────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(catch_handlers.catch_button,   pattern="^catch_"))
    app.add_handler(CallbackQueryHandler(user_handlers.collection_nav,  pattern="^col_"))
    app.add_handler(CallbackQueryHandler(user_handlers.browse_nav,      pattern="^brw_"))
    app.add_handler(CallbackQueryHandler(user_handlers.trade_callback,  pattern="^trd"))
    app.add_handler(CallbackQueryHandler(user_handlers.duel_callback,   pattern="^duel"))

    # ── Auto-spawn on group text ───────────────────────────────────
    app.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.GROUPS & ~filters.COMMAND,
        catch_handlers.message_spawn_trigger
    ))

    # ── Photo → /addimage or /customimage handler ──────────────────
    app.add_handler(MessageHandler(filters.PHOTO, admin_handlers.add_image_reply))

    # ── Weekly leaderboard job (every Monday 00:00 UTC) ────────────
    jq = app.job_queue
    if jq:
        from datetime import time as dtime
        jq.run_daily(
            weekly_leaderboard.run_weekly_snapshot,
            time=dtime(0, 0, 0),
            days=(0,),   # Monday
            name="weekly_leaderboard"
        )

    print("✅ WaifuBot is running!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
