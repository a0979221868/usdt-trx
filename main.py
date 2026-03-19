import os
import logging
from flask import Flask, request
import telebot
import ccxt
import time

# 設定
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
OKX_API_KEY = os.environ.get('OKX_API_KEY')
OKX_SECRET_KEY = os.environ.get('OKX_SECRET_KEY')
OKX_PASSPHRASE = os.environ.get('OKX_PASSPHRASE')
DEPOSIT_ADDRESS = os.environ.get('OKX_DEPOSIT_ADDRESS')
FEE_RATE = float(os.environ.get('FEE_RATE', 0.01))

# 初始化
bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)

# 初始化 OKX
exchange = ccxt.okx({
    'apiKey': OKX_API_KEY,
    'secret': OKX_SECRET_KEY,
    'password': OKX_PASSPHRASE,
    'enableRateLimit': True,
})

# 用戶狀態
user_data = {}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, 
        "🔥 TRX/USDT 兌換機器人\n\n"
        f"充值地址：{DEPOSIT_ADDRESS}\n\n"
        "1. 輸入數量報價（例如 100）\n"
        "2. 轉帳後回覆：交易哈希 你的地址")

@bot.message_handler(commands=['rate'])
def send_rate(message):
    try:
        ticker = exchange.fetch_ticker('TRX/USDT')
        price = ticker['last']
        bot.reply_to(message, f"1 TRX = {price:.6f} USDT")
    except:
        bot.reply_to(message, "獲取匯率失敗")

@bot.message_handler(func=lambda m: True)
def handle_all(message):
    text = message.text.strip()
    
    # 處理數字
    if text.isdigit() or (text.replace('.', '').isdigit() and '.' in text):
        try:
            amount = float(text)
            ticker = exchange.fetch_ticker('TRX/USDT')
            price = ticker['last']
            final = amount * price * (1 - FEE_RATE)
            
            user_data[message.chat.id] = final
            
            bot.reply_to(message, 
                f"您將獲得：{final:.2f} USDT\n"
                f"請轉帳到：{DEPOSIT_ADDRESS}\n"
                "完成後回覆：交易哈希 你的地址")
        except:
            bot.reply_to(message, "錯誤，請稍後再試")
        return
    
    # 處理交易哈希+地址
    if len(text.split()) == 2 and len(text.split()[0]) == 64:
        if message.chat.id in user_data:
            final = user_data[message.chat.id]
            bot.reply_to(message, f"✅ 兌換成功！獲得 {final:.2f} USDT")
            del user_data[message.chat.id]
        else:
            bot.reply_to(message, "請先輸入數量報價")
        return
    
    bot.reply_to(message, "請輸入 /start 查看說明")

@app.route('/' + TELEGRAM_TOKEN, methods=['POST'])
def webhook():
    update = request.get_data(as_text=True)
    if update:
        bot.process_new_updates([telebot.types.Update.de_json(update)])
    return 'OK', 200

@app.route('/setwebhook', methods=['GET'])
def set_webhook():
    webhook_url = f"https://{os.environ.get('RAILWAY_PUBLIC_DOMAIN', '')}/{TELEGRAM_TOKEN}"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    return "Webhook set", 200

@app.route('/', methods=['GET'])
def index():
    return "Bot is running", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
