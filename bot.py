import os
import telebot
from openai import OpenAI

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)

@bot.message_handler(func=lambda message: True)
def responder(message):
    try:
        resposta = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": message.text}]
        )
        texto_resposta = resposta.choices[0].message.content
        bot.reply_to(message, texto_resposta)
    except Exception as e:
        bot.reply_to(message, f"Ocorreu um erro: {str(e)}")

if __name__ == "__main__":
    print("Bot rodando...")
    bot.polling()
