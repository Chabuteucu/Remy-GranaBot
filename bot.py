import os
from dotenv import load_dotenv
import telebot
import google.generativeai as genai

# Carrega as variáveis do arquivo .env
load_dotenv()

# Lê os tokens do ambiente
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Validação simples
if TELEGRAM_TOKEN is None or GEMINI_API_KEY is None:
    raise ValueError("As variáveis TELEGRAM_TOKEN e GEMINI_API_KEY precisam estar definidas no .env")

# Inicializa o bot do Telegram
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Configura o Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# Responde quando o usuário envia /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Olá! Sou seu bot com IA Gemini. Envie uma mensagem e eu responderei.")

# Responde qualquer mensagem com IA
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        response = model.generate_content(message.text)
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"Ocorreu um erro: {e}")

print("🤖 Bot está rodando... Pressione CTRL+C para parar.")
bot.polling()
