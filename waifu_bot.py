"""
Waifu/Husbando Telegram Bot for Render
=====================================
- Fetch anime-style images from waifu.im API
- Support multiple image categories (waifu, husbando, neko, etc.)
- NSFW filter with age-restricted commands
- Simple inline keyboard navigation
- Deployed on Render using webhooks
"""

import logging
import os
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import requests

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Get from Render environment variables
API_BASE = "https://api.waifu.im/search"
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL")  # Render provides this automatically

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set!")

# Available categories from waifu.im
CATEGORIES = {
    "waifu": "Waifu",
    "husbando": "Husbando", 
    "neko": "Neko",
    "shinobu": "Shinobu",
    "megumin": "Megumin",
    "bully": "Bully",
    "cuddle": "Cuddle",
    "cry": "Cry",
    "hug": "Hug",
    "awoo": "Awoo",
    "kiss": "Kiss",
    "lick": "Lick",
    "pat": "Pat",
    "smug": "Smug",
    "bonk": "Bonk",
    "yeet": "Yeet",
    "blush": "Blush",
    "smile": "Smile",
    "wave": "Wave",
    "highfive": "High Five",
    "handhold": "Hand Hold",
    "nom": "Nom",
    "bite": "Bite",
    "glomp": "Glomp",
    "slap": "Slap",
    "kill": "Kill",
    "kick": "Kick",
    "happy": "Happy",
    "wink": "Wink",
    "poke": "Poke",
    "dance": "Dance",
    "cringe": "Cringe",
}

NSFW_CATEGORIES = {
    "waifu_nsfw": "Waifu (NSFW)",
    "neko_nsfw": "Neko (NSFW)",
    "trap": "Trap",
    "ass": "Ass",
    "hentai": "Hentai",
    "milf": "Milf",
    "oral": "Oral",
    "paizuri": "Paizuri",
    "ecchi": "Ecchi",
    "ero": "Ero",
}

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app for webhook
app = Flask(__name__)
application = None


# ─────────────────────────────────────────────
#  API HELPER
# ─────────────────────────────────────────────
def fetch_image(category: str, is_nsfw: bool = False) -> dict | None:
    """Fetch an image from waifu.im API."""
    params = {
        "included_tags": [category],
        "is_nsfw": is_nsfw,
    }
    
    try:
        response = requests.get(API_BASE, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("images"):
            return data["images"][0]
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"API request error: {e}")
        return None
    except Exception as e:
        logger.error(f"Parse error: {e}")
        return None


# ─────────────────────────────────────────────
#  BOT COMMANDS
# ─────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message with category selection."""
    user = update.effective_user
    await update.message.reply_html(
        f"👋 Welcome {user.mention_html()}!\n\n"
        "I'm a Waifu/Husbando bot! I can fetch anime-style images for you.\n\n"
        "Use /sfw for safe-for-work images or /nsfw for adult content (18+ only).\n\n"
        "Enjoy! 🎨"
    )


async def sfw_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show SFW category selection."""
    keyboard = []
    row = []
    for i, (cat_id, cat_name) in enumerate(CATEGORIES.items()):
        row.append(InlineKeyboardButton(cat_name, callback_data=f"sfw_{cat_id}"))
        if len(row) >= 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🌸 Choose a SFW category:", reply_markup=reply_markup
    )


async def nsfw_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show NSFW category selection (age gate)."""
    # Check if user is in allowed chats or implement age verification
    keyboard = [
        [InlineKeyboardButton("⚠️ I confirm I am 18+", callback_data="nsfw_confirm")],
        [InlineKeyboardButton("❌ Cancel", callback_data="nsfw_cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔞 **NSFW Content Warning**\n\n"
        "This section contains adult content. You must be 18+ to proceed.\n\n"
        "By proceeding, you confirm you are of legal age.",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    # Age confirmation for NSFW
    if data == "nsfw_confirm":
        # Show NSFW categories after confirmation
        keyboard = []
        row = []
        for i, (cat_id, cat_name) in enumerate(NSFW_CATEGORIES.items()):
            row.append(InlineKeyboardButton(cat_name, callback_data=f"nsfw_{cat_id}"))
            if len(row) >= 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🔞 Choose a category:", reply_markup=reply_markup
        )
        return
    
    if data == "nsfw_cancel":
        await query.edit_message_text("Operation cancelled.")
        return
    
    # Parse category selection
    if data.startswith("sfw_") or data.startswith("nsfw_"):
        mode, category = data.split("_", 1)
        is_nsfw = mode == "nsfw"
        
        await query.edit_message_text("🔄 Fetching image...")
        
        image_data = fetch_image(category, is_nsfw)
        
        if not image_data:
            await query.edit_message_text(
                "❌ Failed to fetch image. Please try again."
            )
            return
        
        image_url = image_data.get("url")
        source = image_data.get("source", "Unknown")
        tags = [t.get("text", "") for t in image_data.get("tags", [])]
        
        caption = (
            f"🎨 **Category:** {category.replace('_', ' ').title()}\n"
            f"📊 **Artist:** {image_data.get('artist', {}).get('name', 'Unknown')}\n"
            f"🏷️ **Tags:** {', '.join(tags[:5])}"
        )
        
        # Create navigation buttons
        keyboard = [
            [
                InlineKeyboardButton("🔄 Next", callback_data=data),
                InlineKeyboardButton("🔙 Back", callback_data=f"back_{mode}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send photo
        try:
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=image_url,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode="Markdown",
            )
            await query.delete_message()
        except Exception as e:
            logger.error(f"Failed to send photo: {e}")
            await query.edit_message_text(f"❌ Error sending image: {str(e)}")


async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to main menu."""
    query = update.callback_query
    await query.answer()
    
    mode = query.data.split("_")[1]
    
    if mode == "sfw":
        await sfw_menu_from_callback(query)
    elif mode == "nsfw":
        await nsfw_menu_from_callback(query)


async def sfw_menu_from_callback(query):
    """Show SFW menu from callback."""
    keyboard = []
    row = []
    for i, (cat_id, cat_name) in enumerate(CATEGORIES.items()):
        row.append(InlineKeyboardButton(cat_name, callback_data=f"sfw_{cat_id}"))
        if len(row) >= 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("🌸 Choose a SFW category:", reply_markup=reply_markup)


async def nsfw_menu_from_callback(query):
    """Show NSFW warning from callback."""
    keyboard = [
        [InlineKeyboardButton("⚠️ I confirm I am 18+", callback_data="nsfw_confirm")],
        [InlineKeyboardButton("❌ Cancel", callback_data="nsfw_cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "🔞 **NSFW Content Warning**\n\n"
        "This section contains adult content. You must be 18+ to proceed.\n\n"
        "By proceeding, you confirm you are of legal age.",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message."""
    help_text = """
📖 **Bot Commands:**

/start - Start the bot and see welcome message
/sfw - Browse safe-for-work images
/nsfw - Browse adult content (18+ only)
/help - Show this help message

**Features:**
- Multiple anime-style image categories
- Waifu, Husbando, Neko, and many more
- Easy navigation with inline buttons
- Artist credits and tags included

Powered by waifu.im API 🎨
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")


# ─────────────────────────────────────────────
#  MAIN & WEBHOOK SETUP FOR RENDER
# ─────────────────────────────────────────────
def setup_bot():
    """Initialize the bot application."""
    global application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("sfw", sfw_menu))
    application.add_handler(CommandHandler("nsfw", nsfw_menu))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("Waifu Bot initialized successfully")
    return application


async def webhook_handler(request):
    """Handle incoming webhook requests from Telegram."""
    if request.method == "POST":
        update_data = await request.get_json()
        update = Update.de_json(update_data, application.bot)
        await application.process_update(update)
        return "", 200
    return "", 200


@app.route("/", methods=["GET"])
def health_check():
    """Health check endpoint for Render."""
    return "Waifu Bot is running! 🎨", 200


@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    """Telegram webhook endpoint."""
    update_data = request.get_json()
    if update_data:
        update = Update.de_json(update_data, application.bot)
        # Run the async process in a sync context
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(application.process_update(update))
        finally:
            loop.close()
    return "", 200


def set_webhook():
    """Set the webhook URL with Telegram."""
    if WEBHOOK_URL:
        webhook_url = f"{WEBHOOK_URL}/webhook"
        application.bot.set_webhook(webhook_url)
        logger.info(f"Webhook set to: {webhook_url}")
    else:
        logger.warning("RENDER_EXTERNAL_URL not set. Webhook won't be configured.")


if __name__ == "__main__":
    # Initialize the bot
    setup_bot()
    
    # Set webhook (only if running locally for testing, 
    # on Render this happens automatically when the app starts)
    port = int(os.environ.get("PORT", 8080))
    
    logger.info(f"Starting Flask server on port {port}...")
    app.run(host="0.0.0.0", port=port)
