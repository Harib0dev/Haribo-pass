import asyncio
from io import BytesIO
import regex as re
import requests
from telethon import TelegramClient, events
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.functions.channels import JoinChannelRequest
from concurrent.futures import ThreadPoolExecutor
from config import *

# Инициализация клиента
client = TelegramClient(session='session', api_id=int(api_id), api_hash=api_hash)

# Регулярные выражения для поиска ключевых слов
code_regex = re.compile(r"t\.me/(CryptoBot|send|tonRocketBot|CryptoTestnetBot|wallet|xrocket|xJetSwapBot)\?start=(CQ[A-Za-z0-9]{10}|C-[A-Za-z0-9]{10}|t_[A-Za-z0-9]{15}|mci_[A-Za-z0-9]{15}|c_[a-z0-9]{24})", re.IGNORECASE)
url_regex = re.compile(r"https:\/\/t\.me\/\+(\w{12,})")
public_regex = re.compile(r"https:\/\/t\.me\/(\w{4,})")

# Символы для удаления из текста
replace_chars = ''' @#&+()*"'…;,!№•—–·±<{>}†★‡„“”«»‚‘’‹›¡¿‽~`|√π÷×§∆\\°^%©®™✓₤$₼€₸₾₶฿₳₥₦₫₿¤₲₩₮¥₽₻₷₱₧£₨¢₠₣₢₺₵₡₹₴₯₰₪'''
translation = str.maketrans('', '', replace_chars)

# Исполнитель потоков для OCR
executor = ThreadPoolExecutor(max_workers=5)

# Черный список каналов для чека
crypto_black_list = [1622808649, 1559501630, 1985737506, 5014831088, 6014729293, 5794061503]

# Глобальные переменные
global checks
global checks_count
global wallet
checks = []
wallet = []
channels = []
captches = []
checks_count = 0

# Функция для OCR
def ocr_space_sync(file: bytes, overlay=False, language='eng', scale=True, OCREngine=2):
    payload = {
        'isOverlayRequired': overlay,
        'apikey': ocr_api_key,
        'language': language,
        'scale': scale,
        'OCREngine': OCREngine
    }
    response = requests.post(
        'https://api.ocr.space/parse/image',
        data=payload,
        files={'filename': ('image.png', file, 'image/png')}
    )
    result = response.json()
    return result.get('ParsedResults')[0].get('ParsedText').replace(" ", "")

# Асинхронная версия OCR
async def ocr_space(file: bytes, overlay=False, language='eng'):
    loop = asyncio.get_running_loop()
    recognized_text = await loop.run_in_executor(
        executor, ocr_space_sync, file, overlay, language
    )
    return recognized_text

# Функция для автоматической оплаты
async def pay_out():
    await asyncio.sleep(86400)
    await client.send_message('CryptoBot', message=f'/wallet')
    await asyncio.sleep(0.1)
    messages = await client.get_messages('CryptoBot', limit=1)
    message = messages[0].message
    lines = message.split('\n\n')
    for line in lines:
        if ':' in line:
            if 'Доступно' in line:
                data = line.split('\n')[2].split('Доступно: ')[1].split(' (')[0].split(' ')
                summ = data[0]
                curency = data[1]
            else:
                data = line.split(': ')[1].split(' (')[0].split(' ')
                summ = data[0]
                curency = data[1]
            try:
                if summ == '0':
                    continue
                result = (await client.inline_query('send', f'{summ} {curency}'))[0]
                if 'Создать чек' in result.title:
                    await result.click(avto_vivod_tag)
            except:
                pass

# Обработчик нового сообщения с ключевыми словами (pass, Pass, пароль, Пароль)
@client.on(events.NewMessage(pattern=r"(pass|Pass|Пароль|пароль): (.+)"))
async def handle_password_message(event):
    password = event.pattern_match.group(2)
    await client.send_message('CryptoBot', message=password)
    print(f'Отправлен пароль: {password}')

# Обработчик сообщений из списка чатов с определенными кнопками
@client.on(events.NewMessage(chats=[1985737506], pattern="⚠️ Вы не можете активировать этот чек"))
async def handle_new_message(event):
    global wallet
    code = None
    try:
        for row in event.message.reply_markup.rows:
            for button in row.buttons:
                try:
                    check = code_regex.search(button.url)
                    if check:
                        code = check.group(2)
                    channel = url_regex.search(button.url)
                    public_channel = public_regex.search(button.url)
                    if channel:
                        await client(ImportChatInviteRequest(channel.group(1)))
                    if public_channel:
                        await client(JoinChannelRequest(public_channel.group(1)))
                except:
                    pass
    except AttributeError:
        pass
    if code and code not in wallet:
        await client.send_message('wallet', message=f'/start {code}')
        wallet.append(code)

# Дополнительные обработчики для других чатов
@client.on(events.NewMessage(chats=[1559501630], pattern="Чтобы"))
async def handle_new_message(event):
    try:
        for row in event.message.reply_markup.rows:
            for button in row.buttons:
                try:
                    channel = url_regex.search(button.url)
                    if channel:
                        await client(ImportChatInviteRequest(channel.group(1)))
                except:
                    pass
    except AttributeError:
        pass
    await event.message.click(data=b'check-subscribe')

# Обработчик сообщений для активации чеков
@client.on(events.NewMessage(chats=[5014831088], pattern="Для активации чека"))
async def handle_new_message(event):
    try:
        for row in event.message.reply_markup.rows:
            for button in row.buttons:
                try:
                    channel = url_regex.search(button.url)
                    public_channel = public_regex.search(button.url)
                    if channel:
                        await client(ImportChatInviteRequest(channel.group(1)))
                    if public_channel:
                        await client(JoinChannelRequest(public_channel.group(1)))
                except:
                    pass
    except AttributeError:
        pass
    await event.message.click(data=b'Check')

# Обработчик фото для OCR
@client.on(events.NewMessage(chats=[1559501630], func=lambda e: e.photo))
async def handle_photo_message(event):
    photo = await event.download_media(bytes)
    recognized_text = await ocr_space(file=photo)
    if recognized_text and recognized_text not in captches:
        await client.send_message('CryptoBot', message=recognized_text)
        await asyncio.sleep(0.1)
        message = (await client.get_messages('CryptoBot', limit=1))[0].message
        if 'Incorrect answer.' in message or 'Неверный ответ.' in message:
            await client.send_message(channel, message=f'<b>❌ Не удалось разгадать каптчу, решите ее сами.</b>', parse_mode='HTML') 
            print(f'[!] Ошибка антикаптчи > Не удалось разгадать каптчу.')
            captches.append(recognized_text)

# Запуск бота
async def main():
    await client.start()
    print('Бот запущен и готов к работе...')
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())