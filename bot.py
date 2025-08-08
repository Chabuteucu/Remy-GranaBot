import telebot
import openai
import os

# === Pegando tokens das variáveis de ambiente ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise ValueError("Faltam as variáveis TELEGRAM_TOKEN ou OPENAI_API_KEY.")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
openai.api_key = OPENAI_API_KEY

# Função para gerar resposta da IA
def gerar_resposta(pergunta):
    try:
        resposta = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": pergunta}]
        )
        return resposta.choices[0].message["content"].strip()
    except Exception as e:
        return f"Erro ao gerar resposta: {e}"

# Quando receber mensagem no Telegram
@bot.message_handler(func=lambda message: True)
def responder(message):
    pergunta = message.text
    resposta = gerar_resposta(pergunta)
    bot.reply_to(message, resposta)

print("🤖 Bot IA rodando...")
bot.polling()
