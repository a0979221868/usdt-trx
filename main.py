import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import ccxt
from datetime import datetime
import hmac
import hashlib
import base64
import time
import requests

# 設定日誌
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== 假設的金鑰（請換成你自己的）====================
# 這些是假設值，實際使用時請從環境變數讀取
TELEGRAM_TOKEN = "8661859171:AAFo-MwBZaEDa97gFq1u_jdCLRxI6XFxnAI"
OKX_API_KEY = "0b306702-8c9f-4589-80ea-1b498d55f9c3"
OKX_SECRET_KEY = "9AFF61E29B9FA44D25CFF0950AB004A4"
OKX_PASSPHRASE = "Abc00134799@"
DEPOSIT_ADDRESS = "TEDpqGumpGxqvaD3XUajjy9SP6cKmxtafh"
FEE_RATE = 0.01  # 1% 手續費
USDT_WITHDRAW_FEE = 0.8  # 提現手續費

# 初始化 OKX 交易所
exchange = ccxt.okx({
    'apiKey': OKX_API_KEY,
    'secret': OKX_SECRET_KEY,
    'password': OKX_PASSPHRASE,
    'enableRateLimit': True,
})

# 用戶狀態儲存
user_state = {}

# ==================== OKX API 輔助函數 ====================

def okx_sign(timestamp, method, request_path, body):
    """OKX 簽名函數"""
    message = timestamp + method + request_path + body
    mac = hmac.new(bytes(OKX_SECRET_KEY, encoding='utf8'), 
                   bytes(message, encoding='utf-8'), 
                   digestmod=hashlib.sha256)
    d = mac.digest()
    return base64.b64encode(d).decode()

def check_deposit(txid):
    """查詢充值記錄"""
    timestamp = str(int(time.time()))
    method = 'GET'
    request_path = '/api/v5/asset/deposit-history'
    query = f'?txId={txid}'
    body = ''
    
    sign = okx_sign(timestamp, method, request_path + query, body)
    
    url = f'https://www.okx.com{request_path}{query}'
    headers = {
        'OK-ACCESS-KEY': OKX_API_KEY,
        'OK-ACCESS-SIGN': sign,
        'OK-ACCESS-TIMESTAMP': timestamp,
        'OK-ACCESS-PASSPHRASE': OKX_PASSPHRASE,
    }
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        if data['code'] == '0' and data['data']:
            return data['data'][0]
    except Exception as e:
        logger.error(f"查詢充值失敗: {e}")
    return None

def place_order(instId, side, sz):
    """下單"""
    timestamp = str(int(time.time()))
    method = 'POST'
    request_path = '/api/v5/trade/order'
    body = {
        'instId': instId,
        'tdMode': 'cash',
        'side': side,
        'ordType': 'market',
        'sz': str(sz)
    }
    body_json = json.dumps(body)
    
    sign = okx_sign(timestamp, method, request_path, body_json)
    
    url = f'https://www.okx.com{request_path}'
    headers = {
        'OK-ACCESS-KEY': OKX_API_KEY,
        'OK-ACCESS-SIGN': sign,
        'OK-ACCESS-TIMESTAMP': timestamp,
        'OK-ACCESS-PASSPHRASE': OKX_PASSPHRASE,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(url, headers=headers, json=body)
        return response.json()
    except Exception as e:
        logger.error(f"下單失敗: {e}")
    return None

def withdraw(to_addr, amount):
    """提現 USDT"""
    timestamp = str(int(time.time()))
    method = 'POST'
    request_path = '/api/v5/asset/withdrawal'
    body = {
        'ccy': 'USDT',
        'amt': str(amount),
        'dest': '4',
        'toAddr': to_addr,
        'chain': 'USDT-TRC20',
        'fee': str(USDT_WITHDRAW_FEE)
    }
    body_json = json.dumps(body)
    
    sign = okx_sign(timestamp, method, request_path, body_json)
    
    url = f'https://www.okx.com{request_path}'
    headers = {
        'OK-ACCESS-KEY': OKX_API_KEY,
        'OK-ACCESS-SIGN': sign,
        'OK-ACCESS-TIMESTAMP': timestamp,
        'OK-ACCESS-PASSPHRASE': OKX_PASSPHRASE,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(url, headers=headers, json=body)
        return response.json()
    except Exception as e:
        logger.error(f"提現失敗: {e}")
    return None

# ==================== Telegram 指令處理 ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '🔥 *TRX/USDT 自動兌換機器人* 🔥\n\n'
        '1️⃣ 輸入 TRX 數量（例如 `500`）取得報價\n'
        '2️⃣ 將 TRX 轉到：\n'
        f'`{DEPOSIT_ADDRESS}`\n'
        '3️⃣ 轉帳後回覆：\n'
        '`交易哈希 您的USDT地址`\n'
        '（例如：`0xabc... TXYZ...`）\n'
        '4️⃣ 系統確認後自動發 USDT',
        parse_mode='Markdown'
    )

async def rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ticker = exchange.fetch_ticker('TRX/USDT')
        price = ticker['last']
        await update.message.reply_text(
            f'📈 1 TRX = *{price:.6f} USDT*',
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text('❌ 獲取匯率失敗')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '📖 *使用說明*\n\n'
        '• 輸入數字查詢報價\n'
        '• 轉帳後回覆：`交易哈希 地址`\n'
        '• `/rate` 查看匯率',
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    chat_id = update.effective_chat.id

    # === 報價 ===
    if text.replace('.', '').isdigit():
        try:
            amount = float(text)
            if amount <= 0:
                await update.message.reply_text('❌ 數量必須大於 0')
                return

            ticker = exchange.fetch_ticker('TRX/USDT')
            price = ticker['last']
            final = amount * price * (1 - FEE_RATE) - USDT_WITHDRAW_FEE

            if final <= 0:
                await update.message.reply_text('❌ 金額過低，無法兌換')
                return

            user_state[chat_id] = {
                'amount': amount,
                'price': price,
                'final': final
            }

            await update.message.reply_text(
                f'📊 您將獲得 *{final:.2f} USDT*\n\n'
                f'✅ 請轉 TRX 到：\n`{DEPOSIT_ADDRESS}`\n'
                f'轉帳後回覆：\n`交易哈希 您的USDT地址`',
                parse_mode='Markdown'
            )
        except Exception as e:
            await update.message.reply_text('❌ 獲取價格失敗')
        return

    # === 處理交易哈希+地址 ===
    parts = text.split()
    if len(parts) == 2 and len(parts[0]) == 64 and parts[1].startswith('T') and len(parts[1]) == 34:
        txid, address = parts
        await update.message.reply_text('🔍 驗證中...')

        if chat_id not in user_state:
            await update.message.reply_text('❌ 請先輸入數量報價')
            return

        try:
            # 查詢充值
            deposit = check_deposit(txid)
            if not deposit:
                await update.message.reply_text('❌ 找不到該筆充值記錄')
                return

            state = user_state[chat_id]
            
            # 下單賣出
            order = place_order('TRX-USDT', 'sell', state['amount'])
            if not order or order.get('code') != '0':
                await update.message.reply_text('❌ 賣出失敗')
                return

            # 提現
            withdraw_result = withdraw(address, state['final'])
            if withdraw_result and withdraw_result.get('code') == '0':
                await update.message.reply_text(
                    f'✅ *兌換成功！*\n獲得 *{state["final"]:.2f} USDT*',
                    parse_mode='Markdown'
                )
                del user_state[chat_id]
            else:
                await update.message.reply_text('❌ 提現失敗')

        except Exception as e:
            await update.message.reply_text('❌ 處理失敗')
        return

    await update.message.reply_text('❓ 看不懂，請輸入 /start')

# ==================== 主程式 ====================

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('rate', rate))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Webhook 模式
    port = int(os.environ.get('PORT', 8080))
    webhook_url = f"https://{os.environ.get('RAILWAY_PUBLIC_DOMAIN', 'localhost')}/{TELEGRAM_TOKEN}"
    
    app.run_webhook(
        listen='0.0.0.0',
        port=port,
        url_path=TELEGRAM_TOKEN,
        webhook_url=webhook_url
    )

if __name__ == '__main__':
    main()
