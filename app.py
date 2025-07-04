import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, CallbackContext, 
    CallbackQueryHandler, ConversationHandler
)
from datetime import datetime, timedelta
import sqlite3
import pytz  # Nova biblioteca para fusos horários

# Configurações
TOKEN = os.environ.get('TELEGRAM_TOKEN')
PORT = int(os.environ.get('PORT', 8443))

# Fuso horário de Manaus (UTC-4)
MANAUS_TZ = pytz.timezone('America/Manaus')

# Dados dos corredores
CORREDORES = {
    "Corredor A Térreo": list(range(1, 20)),
    "Corredor B Térreo": list(range(41, 52)),
    "Corredor C Térreo": list(range(80, 89)),
    "Corredor A 1º Piso": list(range(20, 41)),
    "Corredor B 1º Piso": list(range(53, 69)),
    "Corredor C 1º Piso": list(range(89, 100)),
}

# Estados da conversa
ESCOLHER_CORREDOR, ESCOLHER_SALA, ESCOLHER_TIPO, VER_CORREDOR, VER_SALA, VER_DATA = range(6)

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

# Função para obter data/hora em Manaus
def get_manaus_time():
    utc_now = datetime.now(pytz.utc)
    return utc_now.astimezone(MANAUS_TZ)

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

# Handler de escolha de corredor (registro)
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

# Handler de escolha de sala (registro)
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

# Handler de escolha de tipo (registro)
def escolher_tipo(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    tipo = query.data.split("_", 1)[1]
    
    user = query.from_user
    now_manaus = get_manaus_time()  # Usando horário de Manaus
    data_str = now_manaus.strftime("%Y-%m-%d")
    hora_str = now_manaus.strftime("%H:%M")
    
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
        f"📆 {data_str} {hora_str} (Horário de Manaus)"
    )
    context.user_data.clear()
    return ConversationHandler.END

# /ver - Consulta registros do dia atual em Manaus
def ver(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton(corredor, callback_data=f"vercorredor_{corredor}")]
        for corredor in CORREDORES.keys()
    ]
    update.message.reply_text(
        "📍 Escolha o Corredor para ver registros de hoje:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return VER_CORREDOR

# Handler para escolher corredor (ver)
def ver_corredor(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    corredor = query.data.split("_", 1)[1]
    context.user_data['ver_corredor'] = corredor
    
    salas = CORREDORES[corredor]
    keyboard = [
        [InlineKeyboardButton(str(sala), callback_data=f"versala_{sala}")]
        for sala in salas
    ]
    query.edit_message_text(
        f"📍 Corredor: {corredor}\n🔢 Escolha a Sala:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return VER_SALA

# Handler para escolher sala (ver)
def ver_sala(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    sala = query.data.split("_", 1)[1]
    corredor = context.user_data['ver_corredor']
    data_hoje = get_manaus_time().strftime("%Y-%m-%d")  # Data atual em Manaus
    
    conn = sqlite3.connect('registros.db')
    c = conn.cursor()
    c.execute('''SELECT tipo, file_id FROM registros 
                 WHERE corredor=? AND sala=? AND data=?''',
              (corredor, sala, data_hoje))
    registros = c.fetchall()
    conn.close()

    chegada = next((r for r in registros if r[0] == "Chegada"), None)
    saida = next((r for r in registros if r[0] == "Saída"), None)

    resposta = (
        f"📅 Hoje ({data_hoje}) - {corredor} - Sala {sala}\n"
        f"⏰ Horário de Manaus (UTC-4)\n\n"
        f"🖼️ Chegada:\n"
        f"{'✅ Registrada' if chegada else '❌ Não registrada'}\n\n"
        f"🖼️ Saída:\n"
        f"{'✅ Registrada' if saida else '❌ Não registrada'}"
    )
    
    query.edit_message_text(resposta)
    
    if chegada:
        context.bot.send_photo(chat_id=update.effective_chat.id, photo=chegada[1])
    if saida:
        context.bot.send_photo(chat_id=update.effective_chat.id, photo=saida[1])
    
    context.user_data.clear()
    return ConversationHandler.END

# /registros - Consulta histórica
def registros(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton(corredor, callback_data=f"rgs_corredor_{corredor}")]
        for corredor in CORREDORES.keys()
    ]
    update.message.reply_text(
        "📍 Escolha o Corredor para consulta histórica:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return VER_CORREDOR

# Handler para escolher sala (registros históricos)
def registros_sala(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    corredor = query.data.split("_", 2)[2]
    context.user_data['rgs_corredor'] = corredor
    
    salas = CORREDORES[corredor]
    keyboard = [
        [InlineKeyboardButton(str(sala), callback_data=f"rgs_sala_{sala}")]
        for sala in salas
    ]
    query.edit_message_text(
        f"📍 Corredor: {corredor}\n🔢 Escolha a Sala:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return VER_SALA

# Handler para escolher data (registros históricos)
def registros_data(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    sala = query.data.split("_", 2)[2]
    corredor = context.user_data['rgs_corredor']
    context.user_data['rgs_sala'] = sala
    
    # Gerar botões para os últimos 7 dias em Manaus
    hoje_manaus = get_manaus_time()
    keyboard = []
    for i in range(7):
        data = hoje_manaus - timedelta(days=i)
        data_str = data.strftime("%Y-%m-%d")
        keyboard.append([InlineKeyboardButton(data_str, callback_data=f"rgs_data_{data_str}")])
    
    query.edit_message_text(
        f"📍 Corredor: {corredor}\n"
        f"🔢 Sala: {sala}\n"
        "📅 Escolha a Data:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return VER_DATA

# Handler para mostrar registros históricos
def mostrar_registros(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    data = query.data.split("_", 2)[2]
    corredor = context.user_data['rgs_corredor']
    sala = context.user_data['rgs_sala']
    
    conn = sqlite3.connect('registros.db')
    c = conn.cursor()
    c.execute('''SELECT tipo, file_id, hora FROM registros 
                 WHERE corredor=? AND sala=? AND data=?''',
              (corredor, sala, data))
    registros = c.fetchall()
    conn.close()

    # Organizar registros por tipo
    registros_por_tipo = {"Chegada": None, "Saída": None}
    for r in registros:
        registros_por_tipo[r[0]] = (r[1], r[2])  # (file_id, hora)

    resposta = (
        f"📅 {data} - {corredor} - Sala {sala}\n"
        f"⏰ Horário de Manaus (UTC-4)\n\n"
        f"🖼️ Chegada:\n"
    )
    
    if registros_por_tipo["Chegada"]:
        resposta += f"🕒 Hora: {registros_por_tipo['Chegada'][1]}\n"
    else:
        resposta += "❌ Não registrada\n"
        
    resposta += f"\n🖼️ Saída:\n"
    if registros_por_tipo["Saída"]:
        resposta += f"🕒 Hora: {registros_por_tipo['Saída'][1]}"
    else:
        resposta += "❌ Não registrada"
    
    query.edit_message_text(resposta)
    
    # Enviar fotos se existirem
    if registros_por_tipo["Chegada"]:
        context.bot.send_photo(
            chat_id=update.effective_chat.id, 
            photo=registros_por_tipo["Chegada"][0],
            caption=f"Chegada - {data} - {registros_por_tipo['Chegada'][1]}"
        )
    if registros_por_tipo["Saída"]:
        context.bot.send_photo(
            chat_id=update.effective_chat.id, 
            photo=registros_por_tipo["Saída"][0],
            caption=f"Saída - {data} - {registros_por_tipo['Saída'][1]}"
        )
    
    context.user_data.clear()
    return ConversationHandler.END

def main():
    # Inicializa o Updater
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    # Handlers básicos
    dp.add_handler(CommandHandler("start", start))
    
    # Conversation Handler para registro
    conv_handler_registrar = ConversationHandler(
        entry_points=[CommandHandler("registrar", registrar)],
        states={
            ESCOLHER_CORREDOR: [CallbackQueryHandler(escolher_corredor, pattern="^corredor_")],
            ESCOLHER_SALA: [CallbackQueryHandler(escolher_sala, pattern="^sala_")],
            ESCOLHER_TIPO: [CallbackQueryHandler(escolher_tipo, pattern="^tipo_")],
        },
        fallbacks=[]
    )
    dp.add_handler(conv_handler_registrar)
    
    # Conversation Handler para ver registros do dia
    conv_handler_ver = ConversationHandler(
        entry_points=[CommandHandler('ver', ver)],
        states={
            VER_CORREDOR: [CallbackQueryHandler(ver_corredor, pattern='^vercorredor_')],
            VER_SALA: [CallbackQueryHandler(ver_sala, pattern='^versala_')],
        },
        fallbacks=[],
    )
    dp.add_handler(conv_handler_ver)
    
    # Conversation Handler para registros históricos
    conv_handler_registros = ConversationHandler(
        entry_points=[CommandHandler('registros', registros)],
        states={
            VER_CORREDOR: [CallbackQueryHandler(registros_sala, pattern='^rgs_corredor_')],
            VER_SALA: [CallbackQueryHandler(registros_data, pattern='^rgs_sala_')],
            VER_DATA: [CallbackQueryHandler(mostrar_registros, pattern='^rgs_data_')],
        },
        fallbacks=[],
    )
    dp.add_handler(conv_handler_registros)

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
