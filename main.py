import os
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)

# === Variáveis ===
TOKEN = os.getenv("TOKEN")
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = f"https://bot-fiscalizacao.onrender.com{WEBHOOK_PATH}"

# === Flask App ===
app = Flask(__name__)

# === Telegram Bot ===
telegram_app = ApplicationBuilder().token(TOKEN).build()

# === Comandos ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Olá! O bot está rodando com webhook.")

# === Handlers ===
telegram_app.add_handler(CommandHandler("start", start))

# === Webhook Endpoint ===
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    telegram_app.update_queue.put_nowait(update)
    return "OK", 200

# === Configurar Webhook uma vez ===
@app.before_first_request
def init_webhook():
    telegram_app.bot.set_webhook(WEBHOOK_URL)

# === Iniciar servidor Flask ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Render define automaticamente a porta
    app.run(host="0.0.0.0", port=port)
