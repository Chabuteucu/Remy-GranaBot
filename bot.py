    import os
    import sqlite3
    import telebot
    import google.generativeai as genai
    from dotenv import load_dotenv
    from datetime import datetime, timedelta

    # Load .env (for local testing). In production (Render) use Environment Variables.
    load_dotenv()

    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    DB_FILE = os.getenv("SQLITE_DB", "finance_bot.db")

    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN não definido. Coloque no .env ou nas Environment Variables do servidor.")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY não definido. Coloque no .env ou nas Environment Variables do servidor.")

    # Configure Gemini
    genai.configure(api_key=GEMINI_API_KEY)
    try:
        model = genai.GenerativeModel("gemini-pro")
    except Exception:
        # fallback to a generic model name if 'gemini-pro' isn't available in the environment
        model = genai.GenerativeModel("gemini-1.5-flash")

    bot = telebot.TeleBot(TELEGRAM_TOKEN)

    # --- Database (SQLite) helpers ---
    def get_conn():
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        return conn

    def init_db():
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            first_seen TEXT
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            type TEXT,
            amount REAL,
            description TEXT,
            date TEXT
        )""")
        conn.commit()
        conn.close()

    init_db()

    def register_user(telegram_id, username):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT telegram_id FROM users WHERE telegram_id=?", (telegram_id,))
        if cur.fetchone() is None:
            cur.execute("INSERT INTO users (telegram_id, username, first_seen) VALUES (?, ?, ?)",
                        (telegram_id, username, datetime.now().isoformat()))
            conn.commit()
        conn.close()

    def add_transaction(telegram_id, t_type, amount, description):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO transactions (telegram_id, type, amount, description, date) VALUES (?, ?, ?, ?, ?)",
                    (telegram_id, t_type, amount, description, datetime.now().isoformat()))
        conn.commit()
        tx_id = cur.lastrowid
        conn.close()
        return tx_id

    def delete_transaction(telegram_id, tx_id):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM transactions WHERE id=? AND telegram_id=?", (tx_id, telegram_id))
        affected = cur.rowcount
        conn.commit()
        conn.close()
        return affected > 0

    def list_transactions(telegram_id, limit=100):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, type, amount, description, date FROM transactions WHERE telegram_id=? ORDER BY date DESC LIMIT ?",
                    (telegram_id, limit))
        rows = cur.fetchall()
        conn.close()
        return rows

    def get_balance(telegram_id):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE telegram_id=? AND type='receita'", (telegram_id,))
        receitas = cur.fetchone()[0] or 0
        cur.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE telegram_id=? AND type='gasto'", (telegram_id,))
        gastos = cur.fetchone()[0] or 0
        conn.close()
        return float(receitas) - float(gastos)

    def get_transactions_since(telegram_id, since_dt):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, type, amount, description, date FROM transactions WHERE telegram_id=? AND date>=? ORDER BY date DESC",
                    (telegram_id, since_dt.isoformat()))
        rows = cur.fetchall()
        conn.close()
        return rows

    def format_transactions(rows):
        if not rows:
            return "Nenhuma transação encontrada."
        lines = []
        for r in rows:
            tx_id, t_type, amount, desc, date_str = r
            try:
                dt = datetime.fromisoformat(date_str)
                date_fmt = dt.strftime("%d/%m %H:%M")
            except Exception:
                date_fmt = date_str
            tipo = "📈 Receita" if t_type == "receita" else "📉 Gasto"
            lines.append(f"{tx_id}. {date_fmt} — {tipo}: R${amount:.2f} — {desc}")
        return "\n".join(lines)

    # Prompt template for Gemini when user sends open questions
    FIN_PROMPT = (
        "Você é um assistente de finanças pessoais. Responda de forma clara, prática e amigável. "
        "Dê ações possíveis para o dia a dia. Não forneça aconselhamento financeiro profissional; explique simples passos."
    )

    # --- Bot commands ---
    @bot.message_handler(commands=['start'])
    def cmd_start(message):
        register_user(message.from_user.id, message.from_user.first_name or message.from_user.username)
        reply = ("Olá! 👋 Eu sou seu assistente de finanças pessoais.
"
                 "Use /ajuda para ver os comandos disponíveis.")
        bot.reply_to(message, reply)

    @bot.message_handler(commands=['ajuda'])
    def cmd_ajuda(message):
        texto = (
            "📘 *Ajuda — Bot de Finanças Pessoais*\n\n"
            "/receita <valor> [descrição] — registrar uma receita. Ex: /receita 2000 Salário\n"
            "/gasto <valor> [descrição] — registrar um gasto. Ex: /gasto 50 Mercado\n"
            "/saldo — mostra seu saldo atual\n"
            "/listar — lista suas últimas transações (com IDs)\n"
            "/apagar <id> — apaga a transação de ID indicado (veja /listar)\n"
            "/extrato_dia — extrato do dia\n"
            "/extrato_semana — extrato últimos 7 dias\n"
            "/extrato_mes — extrato mês atual\n"
            "Você também pode enviar perguntas livres sobre finanças e eu responderei com dicas práticas."
        )
        bot.reply_to(message, texto, parse_mode='Markdown')

    @bot.message_handler(commands=['receita'])
    def cmd_receita(message):
        parts = message.text.split(maxsplit=2)
        if len(parts) < 2:
            bot.reply_to(message, "Uso: /receita <valor> [descrição]")
            return
        try:
            valor = float(parts[1])
        except:
            bot.reply_to(message, "Valor inválido. Ex: /receita 1500 Salário")
            return
        desc = parts[2] if len(parts) > 2 else "Receita"
        tx_id = add_transaction(message.from_user.id, 'receita', valor, desc)
        bot.reply_to(message, f"✅ Receita registrada (id: {tx_id}) — R${valor:.2f}")

    @bot.message_handler(commands=['gasto'])
    def cmd_gasto(message):
        parts = message.text.split(maxsplit=2)
        if len(parts) < 2:
            bot.reply_to(message, "Uso: /gasto <valor> [descrição]")
            return
        try:
            valor = float(parts[1])
        except:
            bot.reply_to(message, "Valor inválido. Ex: /gasto 12.50 Café")
            return
        desc = parts[2] if len(parts) > 2 else "Gasto"
        tx_id = add_transaction(message.from_user.id, 'gasto', valor, desc)
        bot.reply_to(message, f"✅ Gasto registrado (id: {tx_id}) — R${valor:.2f}")

    @bot.message_handler(commands=['saldo'])
    def cmd_saldo(message):
        bal = get_balance(message.from_user.id)
        bot.reply_to(message, f"💰 Seu saldo atual: R${bal:.2f}")

    @bot.message_handler(commands=['listar'])
    def cmd_listar(message):
        rows = list_transactions(message.from_user.id)
        texto = format_transactions(rows)
        bot.reply_to(message, texto)

    @bot.message_handler(commands=['apagar'])
    def cmd_apagar(message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, "Uso: /apagar <id> (veja /listar para obter o id)")
            return
        try:
            tx_id = int(parts[1])
        except:
            bot.reply_to(message, "ID inválido.")
            return
        ok = delete_transaction(message.from_user.id, tx_id)
        if ok:
            bot.reply_to(message, f"✅ Transação {tx_id} removida.")
        else:
            bot.reply_to(message, "Transação não encontrada ou não pertence a você.")

    @bot.message_handler(commands=['extrato_dia'])
    def cmd_extrato_dia(message):
        hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        rows = get_transactions_since(message.from_user.id, hoje)
        bot.reply_to(message, format_transactions(rows))

    @bot.message_handler(commands=['extrato_semana'])
    def cmd_extrato_semana(message):
        semana = datetime.now() - timedelta(days=7)
        rows = get_transactions_since(message.from_user.id, semana)
        bot.reply_to(message, format_transactions(rows))

    @bot.message_handler(commands=['extrato_mes'])
    def cmd_extrato_mes(message):
        inicio_mes = datetime(datetime.now().year, datetime.now().month, 1)
        rows = get_transactions_since(message.from_user.id, inicio_mes)
        bot.reply_to(message, format_transactions(rows))

    # Non-command messages: use Gemini to provide personalized advice (with short context)
    @bot.message_handler(func=lambda m: True, content_types=['text'])
    def handle_text(message):
        try:
            register_user(message.from_user.id, message.from_user.first_name or message.from_user.username)
            bal = get_balance(message.from_user.id)
            last_rows = list_transactions(message.from_user.id, limit=5)
            recent = "\n".join([f"{r[0]}. {r[1]} R${r[2]:.2f} - {r[3]}" for r in last_rows]) or "Nenhuma"
            prompt = (FIN_PROMPT +
                      f"\n\nSaldo atual do usuário: R${bal:.2f}\nÚltimas transações:\n{recent}\n\nPergunta: {message.text}")
            resp = model.generate_content(prompt)
            text = getattr(resp, 'text', None) or str(resp)
            bot.reply_to(message, text)
        except Exception as e:
            bot.reply_to(message, f"Erro ao gerar resposta: {e}")

    if __name__ == '__main__':
        print('Bot de finanças (SQLite) rodando...')
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
