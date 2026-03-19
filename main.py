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

# 初始化
bot = telebot.TeleBot(TELEGRAM_TOKEN)
exchange = ccxt.okx({
    'apiKey': OKX_API_KEY,
    'secret': OKX_SECRET_KEY,
    'password': OKX_PASSPHRASE,
    'enableRateLimit': True,
})

# 用戶暫存
user_data = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 
        "🔥 TRX/USDT 兌換機器人\n\n"
        f"📤 充值地址：`{DEPOSIT_ADDRESS}`\n\n"
        "1️⃣ 輸入 TRX 數量（例如 100）\n"
        "2️⃣ 轉帳後回覆：交易哈希 你的地址",
        parse_mode='Markdown')

@bot.message_handler(commands=['rate'])
def rate(message):
    try:
        ticker = exchange.fetch_ticker('TRX/USDT')
        price = ticker['last']
        bot.reply_to(message, f"📈 1 TRX = {price:.6f} USDT")
    except:
        bot.reply_to(message, "❌ 獲取匯率失敗")

@bot.message_handler(func=lambda m: True)
def handle(message):
    text = message.text.strip()
    
    # 報價
    if text.replace('.', '').isdigit():
        try:
            amount = float(text)
            ticker = exchange.fetch_ticker('TRX/USDT')
            price = ticker['last']
            final = amount * price * (1 - FEE_RATE)
            user_data[message.chat.id] = final
            bot.reply_to(message, 
                f"💰 獲得：{final:.2f} USDT\n"
                f"📤 轉到：{DEPOSIT_ADDRESS}\n"
                f"✅ 完成後回覆：交易哈希 地址")
        except:
            bot.reply_to(message, "❌ 錯誤")
        return
    
    # 兌換
    parts = text.split()
    if len(parts) == 2 and len(parts[0]) == 64:
        if message.chat.id in user_data:
            final = user_data[message.chat.id]
            bot.reply_to(message, f"✅ 成功！獲得 {final:.2f} USDT")
            del user_data[message.chat.id]
        else:
            bot.reply_to(message, "❌ 請先輸入數量")
        return
    
    bot.reply_to(message, "❓ 輸入 /start")

if __name__ == '__main__':
    print("🤖 機器人啟動中...")
    bot.infinity_polling()
