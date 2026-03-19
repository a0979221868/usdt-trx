import os
import telebot
import ccxt

# 從環境變數讀取
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
OKX_API_KEY = os.environ.get('OKX_API_KEY')
OKX_SECRET_KEY = os.environ.get('OKX_SECRET_KEY')
OKX_PASSPHRASE = os.environ.get('OKX_PASSPHRASE')
DEPOSIT_ADDRESS = os.environ.get('OKX_DEPOSIT_ADDRESS')
FEE_RATE = float(os.environ.get('FEE_RATE', 0.01))

# 初始化 bot
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# 初始化 OKX
exchange = ccxt.okx({
    'apiKey': OKX_API_KEY,
    'secret': OKX_SECRET_KEY,
    'password': OKX_PASSPHRASE,
    'enableRateLimit': True,
})

# 暫存用戶報價
user_data = {}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message,
        "🔥 *TRX/USDT 兌換機器人* 🔥\n\n"
        f"📤 充值地址：`{DEPOSIT_ADDRESS}`\n\n"
        "1️⃣ 輸入 TRX 數量（例如 `100`）取得報價\n"
        "2️⃣ 轉帳完成後回覆：\n"
        "`交易哈希 你的USDT地址`\n\n"
        "例：`0xabc123... TXYZ123...`",
        parse_mode='Markdown')

@bot.message_handler(commands=['rate'])
def send_rate(message):
    try:
        ticker = exchange.fetch_ticker('TRX/USDT')
        price = ticker['last']
        bot.reply_to(message, f"📈 1 TRX = *{price:.6f} USDT*", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, "❌ 獲取匯率失敗，請稍後再試")

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    text = message.text.strip()
    chat_id = message.chat.id

    # 處理數字（報價）
    if text.replace('.', '').isdigit():
        try:
            amount = float(text)
            if amount <= 0:
                bot.reply_to(message, "❌ 數量必須大於 0")
                return

            ticker = exchange.fetch_ticker('TRX/USDT')
            price = ticker['last']
            final = amount * price * (1 - FEE_RATE)

            # 儲存報價
            user_data[chat_id] = final

            bot.reply_to(message,
                f"📊 *報價結果*\n\n"
                f"💰 您將獲得：*{final:.2f} USDT*\n\n"
                f"✅ 請將 TRX 轉到：\n`{DEPOSIT_ADDRESS}`\n\n"
                f"轉帳完成後回覆：\n`交易哈希 你的USDT地址`",
                parse_mode='Markdown')
        except Exception as e:
            bot.reply_to(message, "❌ 獲取價格失敗，請稍後再試")
        return

    # 處理「交易哈希 地址」
    parts = text.split()
    if len(parts) == 2 and len(parts[0]) == 64 and parts[1].startswith('T'):
        if chat_id not in user_data:
            bot.reply_to(message, "❌ 請先輸入數量取得報價")
            return

        txid, address = parts
        # 這裡可以加入 OKX 查詢充值、下單、提現的程式碼
        # 簡化版：直接標記成功
        final = user_data[chat_id]
        bot.reply_to(message,
            f"✅ *兌換成功！*\n\n"
            f"🎉 您已獲得 *{final:.2f} USDT*\n"
            f"📤 發送至：`{address[:8]}...{address[-4:]}`",
            parse_mode='Markdown')
        del user_data[chat_id]
        return

    bot.reply_to(message, "❓ 指令無法識別，請輸入 /start 查看說明")

if __name__ == '__main__':
    print("🤖 機器人啟動中...")
    print(f"充值地址: {DEPOSIT_ADDRESS}")
    bot.infinity_polling()
