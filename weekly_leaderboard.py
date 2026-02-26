"""
jobs/weekly_leaderboard.py
Runs every Monday at midnight UTC.
• Records each top-10 user's rank for the week
• Awards custom waifu to anyone who has been top-3 for 1+ consecutive week
"""

import logging
from datetime import datetime, timedelta
from telegram.ext import ContextTypes

import database as db
from handlers.custom_waifu import generate_custom_waifu

logger = logging.getLogger(__name__)

# How many consecutive weeks in top-3 before earning the custom waifu
WEEKS_REQUIRED = 1


async def run_weekly_snapshot(context: ContextTypes.DEFAULT_TYPE):
    """Called every Monday at 00:00 UTC by the job queue."""
    now      = datetime.utcnow()
    # Use ISO week: e.g. "2024-W03"
    week_str = now.strftime("%Y-W%W")

    logger.info(f"[WeeklyLB] Running snapshot for week {week_str}")

    rows = db.get_leaderboard()  # returns top-10
    if not rows:
        return

    # Record ranks
    for rank, row in enumerate(rows, start=1):
        db.record_weekly_rank(row["user_id"], week_str, rank, row["catches"])

    # Check top-3 for consecutive weeks
    for rank, row in enumerate(rows[:3], start=1):
        uid    = row["user_id"]
        consec = db.get_consecutive_top_weeks(uid, top_n=3)

        if consec >= WEEKS_REQUIRED:
            # Check if we already awarded them recently (avoid duplicates)
            awards = db.get_custom_awards(uid)
            recent_lb = [a for a in awards if "leaderboard" in (a["reason"] or "")]

            # Only award if they don't already have a leaderboard waifu from this week
            already_this_week = any(
                week_str in (a["awarded_at"] or "")
                for a in recent_lb
            )
            if already_this_week:
                continue

            u    = db.get_user(uid)
            name = u["first_name"] if u else f"User#{uid}"
            logger.info(f"[WeeklyLB] Awarding custom waifu to {name} (rank #{rank}, {consec} weeks)")

            char_id = generate_custom_waifu(uid, name, f"leaderboard_week_{week_str}")
            if not char_id:
                continue

            db.add_to_collection(uid, char_id)
            db.record_custom_award(uid, char_id, f"leaderboard_week_{week_str}")

            char = db.get_character(char_id)
            try:
                await context.bot.send_message(
                    uid,
                    f"🏆 *Congratulations, {name}!*\n\n"
                    f"You've been in the *Top 3 leaderboard* for *{consec} week(s)* in a row!\n\n"
                    f"As a reward, you've earned an *exclusive custom waifu:* 👑\n\n"
                    f"🎴 *{char['name']}*\n"
                    f"📺 _{char['anime']}_\n"
                    f"🌠 Legendary (Custom)\n\n"
                    f"Check it with /collection — this character is *only yours!*",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.warning(f"[WeeklyLB] Could not notify {uid}: {e}")

    logger.info(f"[WeeklyLB] Snapshot complete for week {week_str}")