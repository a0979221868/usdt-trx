import os
import logging
from flask import Flask, request
import telebot
import ccxt
import threading
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

# ========== Telegram 指令 ==========
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, 
        "🔥 TRX/USDT 兌換機器人\n\n"
        "1. 輸入 TRX 數量（例如 100）報價\n"
        f"2. 轉帳到：{DEPOSIT_ADDRESS}\n"
        "3. 轉完回傳：交易哈希 你的USDT地址")

@bot.message_handler(commands=['rate'])
def send_rate(message):
    try:
        ticker = exchange.fetch_ticker('TRX/USDT')
        price = ticker['last']
        bot.reply_to(message, f"📈 1 TRX = {price:.6f} USDT")
    except:
        bot.reply_to(message, "❌ 獲取匯率失敗")

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    text = message.text.strip()
    chat_id = message.chat.id
    
    # 處理數字報價
    if text.replace('.', '').isdigit():
        try:
            amount = float(text)
            ticker = exchange.fetch_ticker('TRX/USDT')
            price = ticker['last']
            final = amount * price * (1 - FEE_RATE)
            
            user_data[chat_id] = {'amount': amount, 'price': price}
            
            bot.reply_to(message, 
                f"📊 報價：{final:.2f} USDT\n"
                f"轉帳到：{DEPOSIT_ADDRESS}\n"
                "完成後回傳：交易哈希 你的地址")
        except:
            bot.reply_to(message, "❌ 錯誤")
        return
    
    # 處理交易哈希+地址
    parts = text.split()
    if len(parts) == 2 and len(parts[0]) == 64:
        bot.reply_to(message, "✅ 收到，處理中（此為示範版，實際交易需串接OKX API）")
        return
    
    bot.reply_to(message, "❓ 請輸入 /start 查看說明")

# ========== Webhook 設定 ==========
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

# ========== 啟動 ==========
if __name__ == '__main__':
    # 移除舊 webhook
    bot.remove_webhook()
    time.sleep(1)
    
    # 啟動 Flask
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
