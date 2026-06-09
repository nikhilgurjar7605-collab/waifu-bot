# Waifu/Husbando Telegram Bot

A Telegram bot that fetches anime-style images from the [waifu.im](https://waifu.im) API.

## Features

- 🌸 **SFW Categories**: Waifu, Husbando, Neko, and 30+ action/emotion tags
- 🔞 **NSFW Categories**: Adult content with age verification gate
- 🎨 **Artist Credits**: Shows artist name and image tags
- 🔄 **Easy Navigation**: Inline keyboard buttons for browsing
- ⚡ **Fast Response**: Direct API integration with waifu.im

## Setup

### 1. Get Your Bot Token

1. Talk to [@BotFather](https://t.me/BotFather) on Telegram
2. Create a new bot with `/newbot`
3. Copy your bot token

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the Bot

Edit `waifu_bot.py` and replace the token:

```python
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Paste your token here
```

### 4. Run the Bot

```bash
python waifu_bot.py
```

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and introduction |
| `/sfw` | Browse safe-for-work images |
| `/nsfw` | Browse adult content (18+ only) |
| `/help` | Show help message |

## Available Categories

### SFW
Waifu, Husbando, Neko, Shinobu, Megumin, Bully, Cuddle, Cry, Hug, Awoo, Kiss, Lick, Pat, Smug, Bonk, Yeet, Blush, Smile, Wave, High Five, Hand Hold, Nom, Bite, Glomp, Slap, Kill, Kick, Happy, Wink, Poke, Dance, Cringe

### NSFW (18+)
Waifu, Neko, Trap, Ass, Hentai, Milf, Oral, Paizuri, Ecchi, Ero

## API

This bot uses the [waifu.im API](https://github.com/Waifu-im/waifu-api). Check their documentation for more details.

## License

MIT License

## Disclaimer

This bot contains NSFW content. Users must be 18+ to access adult categories. The bot includes an age verification gate before showing NSFW content.
