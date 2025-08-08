import os
import telebot
import google.generativeai as genai

# Variáveis de ambiente
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Configuração do Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-pro")

# Bot do Telegram
bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(func=lambda message: True)
def responder(message):
    try:
        prompt = message.text
        resposta = model.generate_content(prompt)
        bot.reply_to(message, resposta.text)
    except Exception as e:
        bot.reply_to(message, f"Erro: {str(e)}")

print("Bot rodando...")
bot.polling()
