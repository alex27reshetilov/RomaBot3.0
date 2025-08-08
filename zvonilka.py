import os
import requests
import hashlib
import hmac
import base64
from urllib.parse import urlencode
from collections import OrderedDict
import asyncio

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Зчитування токенів із змінних середовища (Replit Secrets)
ZADARMA_API_KEY = os.environ.get('ZADARMA_API_KEY')
ZADARMA_API_SECRET = os.environ.get('ZADARMA_API_SECRET')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')

# Номери
ENTRY_NUMBER = '101'
EXIT_NUMBER = '102'
INTERNAL_NUMBER = '+380635154798'

# Клас API Zadarma
class ZadarmaAPI:
    def __init__(self, key, secret, is_sandbox=False):
        self.key = key
        self.secret = secret
        self.__url_api = 'https://api.zadarma.com'
        if is_sandbox:
            self.__url_api = 'https://api-sandbox.zadarma.com'

    def call(self, method, params={}, request_type='GET', format='json', is_auth=True):
        request_type = request_type.upper()
        if request_type not in ['GET', 'POST', 'PUT', 'DELETE']:
            request_type = 'GET'
        params['format'] = format

        # Підготовка параметрів
        params_string = urlencode(OrderedDict(sorted(params.items())))
        auth_str = self.__get_auth_string_for_header(method, params_string) if is_auth else None

        url = self.__url_api + method
        headers = {'Authorization': auth_str} if auth_str else {}

        if request_type == 'GET':
            response = requests.get(url + '?' + params_string, headers=headers)
        elif request_type == 'POST':
            response = requests.post(url, headers=headers, data=params)
        elif request_type == 'PUT':
            response = requests.put(url, headers=headers, data=params)
        elif request_type == 'DELETE':
            response = requests.delete(url, headers=headers, data=params)

        return response

    def __get_auth_string_for_header(self, method, params_string):
        data = method + params_string + hashlib.md5(params_string.encode('utf8')).hexdigest()
        hmac_h = hmac.new(self.secret.encode('utf8'), data.encode('utf8'), hashlib.sha1)
        return self.key + ':' + base64.b64encode(hmac_h.hexdigest().encode('utf8')).decode()

# Ініціалізація API
zadarma_api = ZadarmaAPI(ZADARMA_API_KEY, ZADARMA_API_SECRET)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📥 Въезд", callback_data='entry')],
        [InlineKeyboardButton("📤 Выезд", callback_data='exit')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('👋 Выберите действие:', reply_markup=reply_markup)

# Обробка натискання кнопок
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    destination = ENTRY_NUMBER if query.data == 'entry' else EXIT_NUMBER
    params = {'from': INTERNAL_NUMBER, 'to': destination}

    response = zadarma_api.call('/v1/request/callback/', params=params, request_type='GET')

    if response.status_code == 200:
        await query.edit_message_text(text=f"✅ Звонок на {destination} инициирован.")
    else:
        await query.edit_message_text(
            text=f"❌ Ошибка при инициировании звонка.\nКод: {response.status_code}\nОтвет: {response.text}"
        )

# Запуск бота
async def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_click))
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
