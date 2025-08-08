import telebot
import openai
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
openai.api_key = OPENAI_KEY

@bot.message_handler(func=lambda message: True)
def responder(message):
    try:
        resposta = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": message.text}]
        )
        texto = resposta.choices[0].message["content"]
        bot.reply_to(message, texto)
    except Exception as e:
        bot.reply_to(message, f"Erro: {str(e)}")

print("🤖 Bot rodando no Railway...")
bot.polling()
