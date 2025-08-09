import os
import sqlite3
import telebot
from dotenv import load_dotenv
import google.generativeai as genai
from datetime import datetime

# 🔹 Carrega variáveis do .env
if os.path.exists(".env"):
    load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise ValueError("⚠️ Falta definir TELEGRAM_TOKEN ou GEMINI_API_KEY.")

# 🔹 Configura Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-pro")

# 🔹 Configura o bot
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# 📌 Prompt fixo
FINANCAS_PROMPT = """
Você é um assistente de finanças pessoais que ajuda diariamente o usuário a:
- Organizar o orçamento
- Controlar gastos
- Definir metas financeiras
- Dar dicas de economia
- Orientar sobre investimentos básicos

Responda de forma clara, prática e amigável.
"""

# 🗄️ Configuração do banco de dados SQLite
DB_FILE = "usuarios.db"

def inicializar_banco():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    # Tabela de usuários
    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        nome TEXT,
        data_registro TEXT
    )
    """)
    # Tabela de histórico
    cur.execute("""
    CREATE TABLE IF NOT EXISTS historico (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER,
        mensagem TEXT,
        resposta TEXT,
        data_hora TEXT
    )
    """)
    conn.commit()
    conn.close()

def registrar_usuario(telegram_id, nome):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT * FROM usuarios WHERE telegram_id=?", (telegram_id,))
    if cur.fetchone() is None:
        cur.execute("INSERT INTO usuarios (telegram_id, nome, data_registro) VALUES (?, ?, ?)",
                    (telegram_id, nome, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    conn.close()

def salvar_historico(telegram_id, mensagem, resposta):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT INTO historico (telegram_id, mensagem, resposta, data_hora) VALUES (?, ?, ?, ?)",
                (telegram_id, mensagem, resposta, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

# 📩 Responde mensagens
@bot.message_handler(func=lambda message: True)
def responder(message):
    try:
        # Registra usuário
        registrar_usuario(message.from_user.id, message.from_user.first_name)

        prompt_usuario = message.text
        prompt_final = f"{FINANCAS_PROMPT}\n\nPergunta do usuário: {prompt_usuario}"

        resposta = model.generate_content(prompt_final)
        texto_resposta = resposta.text if resposta and hasattr(resposta, 'text') else "Não consegui gerar resposta agora."

        # Salva no histórico
        salvar_historico(message.from_user.id, prompt_usuario, texto_resposta)

        bot.reply_to(message, texto_resposta)
    except Exception as e:
        bot.reply_to(message, f"❌ Ocorreu um erro: {e}")

# ▶️ Inicia o bot
if __name__ == "__main__":
    inicializar_banco()
    print("💰 Bot de Finanças Pessoais com registro de usuários online...")
    bot.polling(none_stop=True)
