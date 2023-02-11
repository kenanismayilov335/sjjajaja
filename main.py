import os
import asyncio
import aiohttp
from json import loads, dumps
from pyrogram import Client, filters, idle
from pyrogram.types import (Message, CallbackQuery, InlineQuery,
                            InlineKeyboardMarkup, InlineKeyboardButton,
                            InlineQueryResultArticle, InputTextMessageContent)
from databases import Database

API_ID = '5767154208'
API_HASH = '37f4a3bfee76addb4d2e0a5916f9e71e'
BOT_TOKEN = '5767154208:AAEcjjovrfUWvFEoJeRaedgT-KvE-lrB-0I'
COUNTRY_LIST_URL = 'https://telegra.ph/Country-List-11-25'
SERVICE_LIST_URL = 'https://telegra.ph/Service-List-11-25'

if not os.path.isfile('./fivesimnet.db'):
    with open('./fivesimnet.db', 'w') as f:
        pass

db = Database('sqlite:///fivesimnet.db')
app = Client('fivesimnet', API_ID, API_HASH, bot_token=BOT_TOKEN)
me = None


async def run():
    global me
    await app.start()
    me = await app.get_me()
    await db.connect()
    await db.execute('''CREATE TABLE IF NOT EXISTS users
                    (userid INTEGER PRIMARY KEY,
                    lastid VARCHAR(255),
                    apikey VARCHAR(255))''')
    await idle()
    await app.stop()


@app.on_message(filters.command(['start', 'help']))
async def start(client: Client, message: Message):
    await message.reply('Botu kullanmak için öncelikle 5sim.net hesabınız ile giriş yapmanız gereklidir.\n'
                        '`/connect 5sim_api_key` şeklinde 5sim hesabınıza giriş yapabilirsiniz.\n'
                        '5sim.net hesabınızın API keyini https://5sim.net/settings/security adresinden alabilirsiniz.\n'
                        '(**API key 5sim protocol** yazan api key gereklidir.)\n\n'
                        'Botun Özellikleri:\n'
                        '/buy - Numara satın alma\n'
                        '/balance - Bakiye sorgulama\n')


@app.on_message(filters.command('connect'))
async def connect(client: Client, message: Message):
    try:
        key = message.text.split(' ')[1]
    except:
        return await message.reply('`/connect 5sim_api_key` şeklinde 5sim hesabınıza giriş yapabilirsiniz.')
    session = aiohttp.ClientSession(
        headers={'Authorization': f'Bearer {key}', 'Accept': 'application/json'})
    resp = await session.get('https://5sim.net/v1/user/profile')
    if resp.status == 200:
        json = await resp.json()
        await db.execute('INSERT INTO users (userid, lastid, apikey) VALUES (:userid, :lastid, :apikey)',
                         {'userid': message.from_user.id,
                          'lastid': '0',
                          'apikey': key})
        await message.reply(f'`{json["email"]}` hesabına başarıyla giriş yapıldı.\n'
                            f'Bakiye: `{json["balance"]}`'
                            'Çıkış yapmak için **Çıkış Yap** butonuna tıklayın veya /disconnect yazın',
                            reply_markup=InlineKeyboardMarkup(
                                [[
                                    InlineKeyboardButton(
                                        'Çıkış Yap', callback_data='disconnect')
                                ]]))
    elif resp.status == 401:
        await message.reply('API key hatalı.')
    await session.close()


@app.on_message(filters.command('disconnect'))
async def disconnect(client: Client, message: Message):
    user = await db.fetch_one('SELECT * FROM users WHERE userid = :userid', {'userid': message.from_user.id})
    if user:
        await message.reply('Çıkış yapmak istediğinize emin misiniz?',
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton(
                                    'Evet', callback_data='disconnect')
                            ]]))
    else:
        await message.reply('5sim hesabınızla giriş yapılmamış.')


@app.on_callback_query(filters.regex('^disconnect$'))
async def disconnect_cb(client: Client, query: CallbackQuery):
    user = await db.fetch_one('SELECT * FROM users WHERE userid = :userid', {'userid': query.from_user.id})
    if user:
        await db.execute('DELETE FROM users WHERE userid = :userid', {'userid': query.from_user.id})
        await query.edit_message_text('5sim hesabınızdan çıkış yapıldı.')
    else:
        await query.edit_message_text('5sim hesabınızla giriş yapılmamış.')


@app.on_message(filters.command('balance'))
async def balance(client: Client, message: Message):
    user = await db.fetch_one('SELECT * FROM users WHERE userid = :userid', {'userid': message.from_user.id})
    if user:
        session = aiohttp.ClientSession(
            headers={'Authorization': f'Bearer {user["apikey"]}', 'Accept': 'application/json'})
        resp = await session.get('https://5sim.net/v1/user/profile')
        if resp.status == 200:
            json = await resp.json()
            await message.reply(f'**Bakiye:** `{json["balance"]}`')
        elif resp.status == 401:
            await message.reply('API key hatalı.')
        await session.close()
    else:
        await message.reply('5sim hesabınızla giriş yapılmamış.')


@app.on_message(filters.command('buy'))
async def buy(client: Client, message: Message):
    user = await db.fetch_one('SELECT * FROM users WHERE userid = :userid', {'userid': message.from_user.id})
    if user:
        try:
            country = message.text.split(' ')[1]
            service = message.text.split(' ')[2]
        except:
            return await message.reply('`/buy country service` şeklinde komutu kullanabilirsiniz.\n'
                                       'Örnek: `/buy russia telegram`\n'
                                       f'Ülke listesi: {COUNTRY_LIST_URL}\n'
                                       f'Servis listesi: {SERVICE_LIST_URL}',
                                       disable_web_page_preview=True)
        session = aiohttp.ClientSession(
            headers={'Authorization': f'Bearer {user["apikey"]}', 'Accept': 'application/json'})
        resp = await session.get(f'https://5sim.net/v1/user/buy/activation/{country}/any/{service}')
        if resp.status == 200:
            try:
                json = await resp.json()
            except:
                await session.close()
                return await message.reply('Kullanılabilir numara yok.')
            await db.execute('UPDATE users SET lastid = :lastid WHERE userid = :userid',
                             {'lastid': json['id'],
                              'userid': message.from_user.id})
            await message.reply(f'**Numara:** `{json["phone"]}` ({json["price"]} RUB)\n'
                                f'({json["country"]} - {json["product"]})\n\n'
                                'Kodu almak için **Kodu Al** butonuna tıklayın veya /code yazın.\n'
                                'İptal etmek için **İptal** butonuna tıklayın veya /cancel yazın.',
                                reply_markup=InlineKeyboardMarkup(
                                    [[
                                        InlineKeyboardButton(
                                            'Kodu Al', callback_data=f'getcode {dumps(dict(for_user=message.from_user.id))}'),
                                        InlineKeyboardButton(
                                            'İptal', callback_data=f'cancel {dumps(dict(for_user=message.from_user.id))}')
                                    ]]))
        elif resp.status == 401:
            await message.reply('API key hatalı.')
        elif resp.status == 400:
            text = await resp.text()
            await message.reply({'not enough user balance': 'Bakiye yetersiz.',
                                 'not enough rating': 'Puan yetersiz.',
                                 'bad country': 'Ülke geçersiz.',
                                 'no product': f'`{country}/{service}` için numara bulunamadı.',
                                 'server offline': '5sim.net yanıt vermedi.'}.get(text, 'Bilinmeyen bir hata oluştu.'),
                                disable_web_page_preview=True)
        else:
            await message.reply('Bilinmeyen bir hata oluştu.')
        await session.close()
    else:
        await message.reply('Önce giriş yapmalısınız.\n'
                            '`/connect 5sim_api_key` şeklinde 5sim hesabınıza giriş yapabilirsiniz.')


@app.on_callback_query(filters.regex('^getcode (.*)'))
async def getcode_cb(client: Client, query: CallbackQuery):
    if not loads(query.data.split(' ', 1)[1])['for_user'] == query.from_user.id:
        return await query.answer('Bu mesaj sizin için değil!')
    user = await db.fetch_one('SELECT * FROM users WHERE userid = :userid', {'userid': query.from_user.id})
    if user:
        session = aiohttp.ClientSession(
            headers={'Authorization': f'Bearer {user["apikey"]}', 'Accept': 'application/json'})
        resp = await session.get(f'https://5sim.net/v1/user/check/{user["lastid"]}')
        if resp.status == 200:
            json = await resp.json()
            if json['status'] == 'RECEIVED' and len(json['sms']) > 0:
                await query.edit_message_text(f'**Kod:** `{json["sms"][0]["code"]}`\n'
                                              f'**Full SMS:**\n`"{json["sms"][0]["text"]}"`',
                                              reply_markup=InlineKeyboardMarkup(
                                                  [[
                                                      InlineKeyboardButton(
                                                          'Kodu Yeniden Al', callback_data=f'getcode {dumps(dict(for_user=query.from_user.id))}'),
                                                      InlineKeyboardButton(
                                                          'Bitir', callback_data=f'finish {dumps(dict(for_user=query.from_user.id))}')
                                                  ]]),
                                              disable_web_page_preview=True)
            elif json['status'] == 'PENDING' or (json['status'] == 'RECEIVED' and len(json['sms']) == 0):
                await query.edit_message_text(f'`{json["phone"]}`\n'
                                              'Bekleniyor...',
                                              reply_markup=InlineKeyboardMarkup(
                                                  [[
                                                      InlineKeyboardButton(
                                                          'Kodu Al', callback_data=f'getcode {dumps(dict(for_user=query.from_user.id))}'),
                                                      InlineKeyboardButton(
                                                          'İptal', callback_data=f'cancel {dumps(dict(for_user=query.from_user.id))}')
                                                  ]]))
            elif json['status'] == 'CANCELLED' or json['status'] == 'BANNED':
                await query.edit_message_text('Satın alım iptal edilmiş.')

            elif json['status'] == 'FINISHED':
                await query.edit_message_text('Satın alım bitirilmiş.')

        elif resp.status == 401:
            await query.edit_message_text('API key hatalı.')
        elif resp.status == 404:
            await query.edit_message_text('Satın alım bulunamadı.')
        else:
            await query.edit_message_text('Bilinmeyen bir hata oluştu.')
        await session.close()
    else:
        await query.edit_message_text('Önce giriş yapmalısınız.\n'
                                      '`/connect 5sim_api_key` şeklinde 5sim hesabınıza giriş yapabilirsiniz.')


@app.on_callback_query(filters.regex('^cancel (.*)'))
async def cancel_cb(client: Client, query: CallbackQuery):
    if not loads(query.data.split(' ', 1)[1])['for_user'] == query.from_user.id:
        return await query.answer('Bu mesaj sizin için değil!')
    user = await db.fetch_one('SELECT * FROM users WHERE userid = :userid', {'userid': query.from_user.id})
    if user:
        session = aiohttp.ClientSession(
            headers={'Authorization': f'Bearer {user["apikey"]}', 'Accept': 'application/json'})
        resp = await session.get(f'https://5sim.net/v1/user/cancel/{user["lastid"]}')
        if resp.status == 200:
            await query.edit_message_text('İptal edildi.')
        elif resp.status == 401:
            await query.edit_message_text('API key hatalı.')
        elif resp.status == 400:
            text = await resp.text()
            await query.edit_message_text({'order not found': 'Satın alım bulunamadı.',
                                           'order expired': 'Satın alım zaman aşımına uğradı.',
                                           'order has sms': 'SMS alındığı için iptal edilemiyor.'}.get(text, 'Bilinmeyen bir hata oluştu.'))
        else:
            await query.edit_message_text('Bilinmeyen bir hata oluştu.')
        await session.close()
    else:
        await query.edit_message_text('Önce giriş yapmalısınız.\n'
                                      '`/connect 5sim_api_key` şeklinde 5sim hesabınıza giriş yapabilirsiniz.')


@app.on_message(filters.command('cancel'))
async def cancel(client: Client, message: Message):
    user = await db.fetch_one('SELECT * FROM users WHERE userid = :userid', {'userid': message.from_user.id})
    if user:
        session = aiohttp.ClientSession(
            headers={'Authorization': f'Bearer {user["apikey"]}', 'Accept': 'application/json'})
        resp = await session.get(f'https://5sim.net/v1/user/cancel/{user["lastid"]}')
        if resp.status == 200:
            await message.reply('İptal edildi.')
        elif resp.status == 401:
            await message.reply('API key hatalı.')
        elif resp.status == 400:
            text = await resp.text()
            await message.reply({'order not found': 'Satın alım bulunamadı.',
                                 'order expired': 'Satın alım zaman aşımına uğradı.',
                                 'order has sms': 'SMS alındığı için iptal edilemiyor.'}.get(text, 'Bilinmeyen bir hata oluştu.'))
        else:
            await message.reply('Bilinmeyen bir hata oluştu.')
        await session.close()
    else:
        await message.reply('Önce giriş yapmalısınız.\n'
                            '`/connect 5sim_api_key` şeklinde 5sim hesabınıza giriş yapabilirsiniz.')


@app.on_callback_query(filters.regex('^finish (.*)'))
async def finish_cb(client: Client, query: CallbackQuery):
    if not loads(query.data.split(' ', 1)[1])['for_user'] == query.from_user.id:
        return await query.answer('Bu mesaj sizin için değil!')
    user = await db.fetch_one('SELECT * FROM users WHERE userid = :userid', {'userid': query.from_user.id})
    if user:
        session = aiohttp.ClientSession(
            headers={'Authorization': f'Bearer {user["apikey"]}', 'Accept': 'application/json'})
        resp = await session.get(f'https://5sim.net/v1/user/finish/{user["lastid"]}')
        if resp.status == 200:
            await query.edit_message_text('Bitirildi.')
        elif resp.status == 401:
            await query.edit_message_text('API key hatalı.')
        elif resp.status == 400:
            text = await resp.text()
            await query.edit_message_text({'order not found': 'Satın alım bulunamadı.',
                                           'order expired': 'Satın alım zaman aşımına uğradı.',
                                           'order has sms': 'SMS alındığı için bitirilemiyor.'}.get(text, 'Bilinmeyen bir hata oluştu.'))
        else:
            await query.edit_message_text('Bilinmeyen bir hata oluştu.')
        await session.close()


@app.on_message(filters.command('log'))
async def log(client: Client, message: Message):
    user = await db.fetch_one('SELECT * FROM users WHERE userid = :userid', {'userid': message.from_user.id})
    if user:
        limit = '10'
        session = aiohttp.ClientSession(
            headers={'Authorization': f'Bearer {user["apikey"]}', 'Accept': 'application/json'})
        resp = await session.get(f'https://5sim.net/v1/user/orders?category=activation&limit={limit}')
        if resp.status == 200:
            json = await resp.json()
            if len(json['Data']) > 0:
                msg = f'<b>Son {limit} Satın Alım:</b>\n\n'
                for i, order in enumerate(json['Data'], 1):
                    msg += f'<b>|</b><b>{i}.................................</b>\n'
                    msg += f'<b>|</b><code>{order["phone"]}</code> <i>({order["country"]}-{order["product"]})</i> {order["price"]} RUB\n'
                    msg += f'<b>|</b><b>Durum:</b> <code>{order["status"]}</code>\n'
                    msg += f'<b>|</b><b>Tarih/Saat:</b> <code>{order["created_at"]}</code>\n\n'
            else:
                msg = 'Hiçbir satın alım bulunamadı.'
            await message.reply(msg, parse_mode='html')

        elif resp.status == 401:
            await message.reply('API key hatalı.')
        else:
            await message.reply('Bilinmeyen bir hata oluştu.')
        await session.close()
    else:
        await message.reply('Önce giriş yapmalısınız.\n'
                            '`/connect 5sim_api_key` şeklinde 5sim hesabınıza giriş yapabilirsiniz.')


@app.on_inline_query(filters.regex('^balance$'))
async def balance_iq(client: Client, query: InlineQuery):
    user = await db.fetch_one('SELECT * FROM users WHERE userid = :userid', {'userid': query.from_user.id})
    if user:
        session = aiohttp.ClientSession(
            headers={'Authorization': f'Bearer {user["apikey"]}', 'Accept': 'application/json'})
        resp = await session.get('https://5sim.net/v1/user/profile')
        if resp.status == 200:
            json = await resp.json()
            await query.answer(
                [
                    InlineQueryResultArticle(
                        'Bakiye',
                        InputTextMessageContent(
                            f'<b>Bakiye:</b> <code>{json["balance"]}</code> RUB',
                            parse_mode='html'
                        ),
                        description=f'Bakiye: {json["balance"]} RUB',
                    )
                ],
                cache_time=0
            )
        elif resp.status == 401:
            await query.answer(
                [
                    InlineQueryResultArticle(
                        'Hata!',
                        InputTextMessageContent(
                            f'<b>API key hatalı.</b>',
                            parse_mode='html'
                        ),
                        description=f'API key hatalı.',
                    )
                ],
                cache_time=0
            )
        await session.close()
    else:
        await query.answer(
            [
                InlineQueryResultArticle(
                    'Giriş Yapın!',
                    InputTextMessageContent(
                        f'Botu kullanmak için önce giriş yapmalısınız.\n'
                        'Detaylar için /help yazabilirsiniz.',
                        parse_mode='html'
                    ),
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    'Giriş Yap',
                                    url=f'https://t.me/{me.username}'
                                )
                            ]
                        ]
                    )
                )
            ],
            cache_time=0
        )


@app.on_inline_query(filters.regex('^buy (.*)'))
async def buy_iq(client: Client, query: InlineQuery):
    user = await db.fetch_one('SELECT * FROM users WHERE userid = :userid', {'userid': query.from_user.id})
    if user:
        try:
            country = query.query.split(' ')[1]
            service = query.query.split(' ')[2]
        except:
            return await query.answer(
                [
                    InlineQueryResultArticle(
                        'Hatalı Kullanım!',
                        InputTextMessageContent(
                            f'`@{me.username} buy country service` şeklinde kullanabilirsiniz.\n'
                            f'Örnek: `@{me.username} buy russia telegram`\n'
                            f'Ülke listesi: {COUNTRY_LIST_URL}\n'
                            f'Servis listesi: {SERVICE_LIST_URL}',
                            disable_web_page_preview=True
                        )
                    )
                ],
                cache_time=0
            )
        await query.answer(
            [
                InlineQueryResultArticle(
                    'Satın Al',
                    InputTextMessageContent(
                        f'{country}/{service} alınıyor. Onaylıyor musunuz?'
                    ),
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    'Onayla',
                                    f'buy|{query.from_user.id}|{country}|{service}'
                                ),
                                InlineKeyboardButton(
                                    'İptal',
                                    f'buy|{query.from_user.id}|cancel'
                                ),
                            ]
                        ]
                    )

                )
            ],
            cache_time=0
        )


@app.on_callback_query(filters.regex('^buy(.*)'))
async def buy_cb(client: Client, query: CallbackQuery):
    if not int(query.data.split('|')[1]) == query.from_user.id:
        return await query.answer('Bu mesaj sizin için değil')
    user = await db.fetch_one('SELECT * FROM users WHERE userid = :userid', {'userid': query.from_user.id})
    if user:
        try:
            if query.data.split('|')[2] == 'cancel':
                return await query.edit_message_text('İptal edildi.')
            else:
                country = query.data.split('|')[2]
                service = query.data.split('|')[3]
        except:
            return await query.edit_message_text('Bilinmeyen bir hata oluştu.')
        session = aiohttp.ClientSession(
            headers={'Authorization': f'Bearer {user["apikey"]}', 'Accept': 'application/json'})
        resp = await session.get(f'https://5sim.net/v1/user/buy/activation/{country}/any/{service}')
        if resp.status == 200:
            try:
                json = await resp.json()
            except:
                await session.close()
                return await query.edit_message_text('Kullanılabilir numara yok.')
            await db.execute('UPDATE users SET lastid = :lastid WHERE userid = :userid',
                             {'lastid': json['id'],
                              'userid': query.from_user.id})
            await query.edit_message_text(f'**Numara:** `{json["phone"]}` ({json["price"]} RUB)\n'
                                          f'({json["country"]} - {json["product"]})\n\n'
                                          'Kodu almak için **Kodu Al** butonuna tıklayın veya /code yazın.\n'
                                          'İptal etmek için **İptal** butonuna tıklayın veya /cancel yazın.',
                                          reply_markup=InlineKeyboardMarkup(
                                              [[
                                                  InlineKeyboardButton(
                                                      'Kodu Al', callback_data=f'getcode {dumps(dict(for_user=query.from_user.id))}'),
                                                  InlineKeyboardButton(
                                                      'İptal', callback_data=f'cancel {dumps(dict(for_user=query.from_user.id))}')
                                              ]]))
        elif resp.status == 401:
            await query.edit_message_text('API key hatalı.')
        elif resp.status == 400:
            text = await resp.text()
            await query.edit_message_text({'not enough user balance': 'Bakiye yetersiz.',
                                           'not enough rating': 'Puan yetersiz.',
                                           'bad country': 'Ülke geçersiz.',
                                           'no product': f'`{country}/{service}` için numara bulunamadı.',
                                           'server offline': '5sim.net yanıt vermedi.'}.get(text, 'Bilinmeyen bir hata oluştu.'),
                                          disable_web_page_preview=True)
        else:
            await query.edit_message_text('Bilinmeyen bir hata oluştu.')
        await session.close()
    else:
        await query.edit_message_text('Önce giriş yapmalısınız.')

loop = asyncio.get_event_loop()
loop.run_until_complete(run())
