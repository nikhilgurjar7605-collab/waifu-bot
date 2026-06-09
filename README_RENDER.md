# Waifu/Husbando Telegram Bot - Render Deployment Guide

## 🚀 Deploy to Render

This bot is configured to run on Render using webhooks. Follow these steps:

### Prerequisites
- A Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- A GitHub account with this repository pushed

### Step-by-Step Deployment

#### 1. Push your code to GitHub
```bash
git add .
git commit -m "Ready for Render deployment"
git push origin main
```

#### 2. Create a new Web Service on Render
1. Go to [render.com](https://render.com) and sign in
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure the service:
   - **Name**: `waifu-bot` (or your preferred name)
   - **Region**: Choose closest to your users
   - **Branch**: `main` (or your default branch)
   - **Root Directory**: Leave blank
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn waifu_bot:app`
   - **Instance Type**: Free tier is fine for testing

#### 3. Add Environment Variables
In the Render dashboard, go to **Environment** tab and add:
- `BOT_TOKEN`: Your Telegram bot token (from @BotFather)

Render automatically provides `RENDER_EXTERNAL_URL` and `PORT`.

#### 4. Deploy
Click **"Create Web Service"** and wait for deployment to complete.

#### 5. Set the Webhook
Once deployed, you need to set the webhook URL with Telegram:

**Option A: Using the browser**
Open this URL in your browser (replace with your actual Render URL):
```
https://YOUR-BOT-NAME.onrender.com/webhook
```

**Option B: Using curl**
```bash
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=https://YOUR-BOT-NAME.onrender.com/webhook"
```

Replace `<BOT_TOKEN>` and `YOUR-BOT-NAME.onrender.com` with your actual values.

#### 6. Test Your Bot
1. Open Telegram and find your bot
2. Send `/start` to begin
3. Try `/sfw` or `/nsfw` commands

### 📝 Notes

- **Free Tier Limitations**: Render's free tier spins down after 15 minutes of inactivity. The first request after spin-down may take 30-50 seconds to respond.
- **Webhook vs Polling**: This bot uses webhooks (recommended for Render) instead of long polling.
- **Logs**: Check logs in the Render dashboard under the **"Logs"** tab for debugging.

### 🔧 Troubleshooting

**Bot not responding?**
1. Check Render logs for errors
2. Verify `BOT_TOKEN` is correct
3. Ensure webhook URL is set correctly
4. Check if the service is running (not spun down)

**Webhook failed?**
```bash
# Check webhook info
curl "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"

# Remove webhook and try again
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/deleteWebhook"
```

### 🛑 Important Security Notes

- Never commit your `BOT_TOKEN` to GitHub
- Keep your bot token private
- The NSFW content requires age confirmation (18+)

### 📚 Bot Commands

- `/start` - Welcome message
- `/sfw` - Browse safe-for-work images
- `/nsfw` - Browse adult content (18+ only)
- `/help` - Show help message

### 🎨 Features

- 30+ SFW categories (Waifu, Husbando, Neko, actions, emotions)
- 9 NSFW categories (with age gate)
- Artist credits and image tags
- Inline navigation buttons
- Powered by [waifu.im API](https://waifu.im/)

---

**Enjoy your Waifu/Husbando bot!** 🎨✨
