import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, CallbackContext, 
    CallbackQueryHandler, ConversationHandler
)
from datetime import datetime
import sqlite3

# Configurações
TOKEN = os.environ.get('TELEGRAM_TOKEN')
PORT = int(os.environ.get('PORT', 8443))

# Dados dos corredores
CORREDORES = {
    "Corredor A Térreo": list(range(1, 19)),
    "Corredor B Térreo": list(range(41, 51)),
    "Corredor C Térreo": list(range(80, 88)),
    "Corredor A 1º Piso": list(range(20, 40)),
    "Corredor B 1º Piso": list(range(53, 68)),
    "Corredor C 1º Piso": list(range(89, 99)),
}

# Estados da conversa
ESCOLHER_CORREDOR, ESCOLHER_SALA, ESCOLHER_TIPO = range(3)

# Inicialização do banco de dados
def init_db():
    conn = sqlite3.connect('registros.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS registros
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  username TEXT,
                  corredor TEXT,
                  sala INTEGER,
                  tipo TEXT,
                  data TEXT,
                  hora TEXT,
                  file_id TEXT)''')
    conn.commit()
    conn.close()

init_db()

# /start - Inicia o bot
def start(update: Update, context: CallbackContext):
    update.message.reply_text("📸 Envie uma foto e use /registrar para iniciar!")

# /registrar - Inicia o processo de registro
def registrar(update: Update, context: CallbackContext):
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        update.message.reply_text("⚠️ Responda a uma foto com este comando!")
        return

    file_id = update.message.reply_to_message.photo[-1].file_id
    context.user_data['file_id'] = file_id
    
    keyboard = [
        [InlineKeyboardButton(corredor, callback_data=f"corredor_{corredor}")]
        for corredor in CORREDORES.keys()
    ]
    update.message.reply_text(
        "📍 Escolha o Corredor:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ESCOLHER_CORREDOR

# Handler de escolha de corredor
def escolher_corredor(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    corredor = query.data.split("_", 1)[1]
    context.user_data['corredor'] = corredor
    
    salas = CORREDORES[corredor]
    keyboard = [
        [InlineKeyboardButton(str(sala), callback_data=f"sala_{sala}")]
        for sala in salas
    ]
    query.edit_message_text(
        f"📍 Corredor: {corredor}\n🔢 Escolha a Sala:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ESCOLHER_SALA

# Handler de escolha de sala
def escolher_sala(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    sala = query.data.split("_", 1)[1]
    context.user_data['sala'] = sala
    
    keyboard = [
        [
            InlineKeyboardButton("Chegada", callback_data="tipo_Chegada"),
            InlineKeyboardButton("Saída", callback_data="tipo_Saída")
        ]
    ]
    query.edit_message_text(
        f"📍 Corredor: {context.user_data['corredor']}\n"
        f"🔢 Sala: {sala}\n"
        "🕒 Escolha o Tipo:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ESCOLHER_TIPO

# Handler de escolha de tipo
def escolher_tipo(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    tipo = query.data.split("_", 1)[1]
    
    user = query.from_user
    now = datetime.now()
    data_str = now.strftime("%Y-%m-%d")
    hora_str = now.strftime("%H:%M")
    
    conn = sqlite3.connect('registros.db')
    c = conn.cursor()
    c.execute('''INSERT INTO registros 
                 (user_id, username, corredor, sala, tipo, data, hora, file_id) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (user.id, user.username, 
               context.user_data['corredor'], 
               context.user_data['sala'],
               tipo,
               data_str,
               hora_str,
               context.user_data['file_id']))
    conn.commit()
    conn.close()
    
    query.edit_message_text(
        f"✅ Foto registrada!\n"
        f"📍 {context.user_data['corredor']}\n"
        f"🔢 Sala {context.user_data['sala']}\n"
        f"🕒 {tipo}\n"
        f"📆 {data_str} {hora_str}"
    )
    context.user_data.clear()
    return ConversationHandler.END

def ver_registro(update: Update, context: CallbackContext):
    args = context.args
    if len(args) < 3:
        update.message.reply_text("⚠️ Use: /ver \"Corredor\" Sala Data\nEx: /ver \"Corredor A Térreo\" 07 2025-07-02")
        return

    try:
        # Corredor tem duas palavras
        corredor = args[0] + " " + args[1]
        sala = args[2]
        data = args[3]
    except:
        update.message.reply_text("⚠️ Formato inválido! Use: /ver \"Corredor\" Sala Data")
        return

    conn = sqlite3.connect('registros.db')
    c = conn.cursor()
    
    c.execute('''SELECT tipo, file_id FROM registros 
                 WHERE corredor=? AND sala=? AND data=?''',
              (corredor, sala, data))
    registros = c.fetchall()
    conn.close()

    chegada = next((r for r in registros if r[0] == "Chegada"), None)
    saida = next((r for r in registros if r[0] == "Saída"), None)

    resposta = (
        f"📅 {data} - {corredor} - Sala {sala}\n\n"
        f"🖼️ Chegada:\n"
        f"{'📎 [Foto]' if chegada else '❌ Não registrada'}\n\n"
        f"🖼️ Saída:\n"
        f"{'📎 [Foto]' if saida else '❌ Não registrada'}"
    )
    
    update.message.reply_text(resposta)
    
    if chegada:
        context.bot.send_photo(update.effective_chat.id, chegada[1])
    if saida:
        context.bot.send_photo(update.effective_chat.id, saida[1])

def main():
    # Correção crucial: forma correta de inicializar o Updater
    updater = Updater(TOKEN)
    
    dp = updater.dispatcher

    # Handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("ver", ver_registro))
    
    # Conversation Handler para registro
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("registrar", registrar)],
        states={
            ESCOLHER_CORREDOR: [CallbackQueryHandler(escolher_corredor, pattern="^corredor_")],
            ESCOLHER_SALA: [CallbackQueryHandler(escolher_sala, pattern="^sala_")],
            ESCOLHER_TIPO: [CallbackQueryHandler(escolher_tipo, pattern="^tipo_")],
        },
        fallbacks=[]
    )
    dp.add_handler(conv_handler)

    # Configuração para Render
    updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"https://bot-fiscalizacao.onrender.com/{TOKEN}"
    )
    updater.idle()

if __name__ == "__main__":
    main()
