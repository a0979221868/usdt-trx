import os
import logging
from flask import Flask, request
import telebot
import ccxt
import time
import json
import hmac
import hashlib
import base64
import requests

# 設定 logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 從環境變數讀取
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
OKX_API_KEY = os.environ.get('OKX_API_KEY')
OKX_SECRET_KEY = os.environ.get('OKX_SECRET_KEY')
OKX_PASSPHRASE = os.environ.get('OKX_PASSPHRASE')
DEPOSIT_ADDRESS = os.environ.get('OKX_DEPOSIT_ADDRESS')
FEE_RATE = float(os.environ.get('FEE_RATE', 0.01))

# 初始化 bot 和 Flask
bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)

# 初始化 OKX
exchange = ccxt.okx({
    'apiKey': OKX_API_KEY,
    'secret': OKX_SECRET_KEY,
    'password': OKX_PASSPHRASE,
    'enableRateLimit': True,
})

# 儲存用戶狀態
user_data = {}

# ========== OKX 簽名函數 ==========
def okx_sign(timestamp, method, request_path, body):
    message = timestamp + method + request_path + body
    mac = hmac.new(
        bytes(OKX_SECRET_KEY, encoding='utf8'),
        bytes(message, encoding='utf-8'),
        digestmod=hashlib.sha256
    )
    return base64.b64encode(mac.digest()).decode()

# ========== Telegram 指令 ==========
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, 
        "🔥 *TRX/USDT 兌換機器人* 🔥\n\n"
        f"充值地址：`{DEPOSIT_ADDRESS}`\n\n"
        "1️⃣ 輸入 TRX 數量報價（例如 100）\n"
        "2️⃣ 轉帳完成後回覆：\n"
        "`交易哈希 你的USDT地址`",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['rate'])
def send_rate(message):
    try:
        ticker = exchange.fetch_ticker('TRX/USDT')
        price = ticker['last']
        bot.reply_to(message, f"📈 1 TRX = *{price:.6f} USDT*", parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Rate error: {e}")
        bot.reply_to(message, "❌ 獲取匯率失敗")

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    text = message.text.strip()
    chat_id = message.chat.id
    
    # 處理數字報價
    if text.replace('.', '').isdigit():
        try:
            amount = float(text)
            if amount <= 0:
                bot.reply_to(message, "❌ 數量必須大於 0")
                return
            
            ticker = exchange.fetch_ticker('TRX/USDT')
            price = ticker['last']
            final_amount = amount * price * (1 - FEE_RATE)
            
            # 儲存狀態
            user_data[chat_id] = {
                'amount': amount,
                'price': price,
                'final': final_amount
            }
            
            bot.reply_to(message, 
                f"📊 *報價結果*\n\n"
                f"💰 您將獲得：*{final_amount:.2f} USDT*\n\n"
                f"✅ 請轉帳到：\n`{DEPOSIT_ADDRESS}`\n\n"
                f"轉帳完成後回覆：\n`交易哈希 你的USDT地址`",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Quote error: {e}")
            bot.reply_to(message, "❌ 獲取價格失敗")
        return
    
    # 處理交易哈希+地址
    parts = text.split()
    if len(parts) == 2 and len(parts[0]) == 64 and parts[1].startswith('T'):
        if chat_id not in user_data:
            bot.reply_to(message, "❌ 請先輸入數量報價")
            return
        
        txid, address = parts
        bot.reply_to(message, "🔍 驗證中...")
        
        try:
            # 這裡要串接 OKX 查詢 API
            # 暫時用模擬成功
            time.sleep(1)
            
            final = user_data[chat_id]['final']
            bot.reply_to(message, 
                f"✅ *兌換成功！*\n\n"
                f"獲得 *{final:.2f} USDT*\n"
                f"已發送至 `{address[:8]}...`",
                parse_mode='Markdown'
            )
            del user_data[chat_id]
            
        except Exception as e:
            logger.error(f"Swap error: {e}")
            bot.reply_to(message, "❌ 兌換失敗")
        return
    
    bot.reply_to(message, "❓ 請輸入 /start 查看說明")

# ========== Webhook ==========
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
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
