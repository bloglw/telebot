import telegram
from telegram import ReplyKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from config import TOKEN, BOT_USERNAME
import sqlite3
import time
from func import get_random_num, selectall_one_from_db
from func import btc_to_cny, update_one_from_db, btc_dis, cny_to_btc
import re
from goods import goods_display
from trade import trade_display
import random

ROUTE = range(1)

bot = telegram.Bot(token=TOKEN)


def start(update, context):
    try:
        user_id = update.effective_user.id
        print('进入start函数 | ' + str(user_id))
        generate_user_info(user_id)
        text = update.message.text
        if text == '/start':
            reply_keyboard = [
                ['👤买家中心', '🤵卖家中心'],
                ['🏧充币/提币/转账', '🙋🏻‍️联系客服']
            ]
            update.message.reply_text(
                '选择您的功能：',
                reply_markup=ReplyKeyboardMarkup(reply_keyboard)
                # reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
            )
        else:
            rst = re.search(r"/start\s(goods|shop|trade)(\d+)", text)
            print(rst.group(1))
            print(rst.group(2))
            if rst.group(1) == 'goods':
                print('用户从商品链接进入')
                goods_display(update, context)
            elif rst.group(1) == 'shop':
                print('用户从店铺链接进入')
                shop_display(update, context)
            elif rst.group(1) == 'trade':
                print('用户从订单链接进入')
                trade_display(update, context)
    except Exception as e:
        print(e)


def service(update, context):
    chat_id = update.effective_chat.id
    bot.send_message(
        chat_id=chat_id,
        text='👨‍👩‍👧‍👦拼多多交流群：@pinduoduo_group\n'
             '👋拼多多官方频道:@pddchannel\n'
             '🤦‍♀️拼多多【唯一客服】:@pddkf\n'
             '💰拼多多BTC代购:@pdddg\n'
    )


def generate_user_info(user_id):
    conn = sqlite3.connect('data.sqlite3')
    cursor = conn.cursor()
    cursor.execute('select * from user where tg_id=?', (user_id,))
    rst = cursor.fetchone()
    uuid = get_random_num()
    time.sleep(0.1)
    if rst is None:
        print('用户第一次进入，自动生成用户数据并保存至数据库')
        cursor.execute("INSERT INTO user VALUES (?,?,?,?,?, NULL, NULL, ?)",
                       (user_id, int(user_id), int(0), '开张', int(get_random_num()), '激活'))
    conn.commit()
    conn.close()


def shop_display(update, context):
    user_id = update.effective_user.id
    print('进入 shop_display 函数 | ' + str(user_id))
    text = update.message.text
    rst = re.search(r"/start\s(goods|shop|trade)(\d+)", text)
    shop_uid = rst.group(2)
    seller_info = selectall_one_from_db('user', 'shop_address', shop_uid)
    if seller_info[3] == '打烊':
        bot.send_message(
            chat_id=user_id,
            text='该店铺目前关门打烊啦～'
        )
    elif seller_info[3] == '锁定':
        bot.send_message(
            chat_id=user_id,
            text='该店铺目前已被管理锁定，暂时无法访问！'
        )
    elif seller_info[3] == '开张':
        seller_id = seller_info[0]
        conn = sqlite3.connect('data.sqlite3')
        cursor = conn.cursor()
        cursor.execute("select * from goods where user_tgid=? and status=?", (seller_id, '上架'))
        all_goods = cursor.fetchall()
        conn.close()
        print(all_goods)
        ret_text = ''
        for i in all_goods:
            ret_text += '📦 [{}](https://t.me/{}?start=goods{}) \t\t {}元\n'.format(i[2], BOT_USERNAME, i[0], i[4])
        bot.send_message(
            chat_id=user_id,
            text='🌈[{}](tg://user?id={})的店铺: \n'.format(seller_id, seller_id) + ret_text[:-1],
            parse_mode='Markdown',
        )


def search_goods(update, context):
    try:
        user_id = update.effective_user.id
        print('进入 search_goods 函数 | ' + str(user_id))
        # print(update.message.text)
        text = update.message.text
        conn = sqlite3.connect('data.sqlite3')
        cursor = conn.cursor()
        cursor.execute("select * from goods where title like '%{}%' and status=?".format(text), ('上架', ))
        rst = cursor.fetchall()
        cursor.execute("select * from goods where desc like '%{}%' and status=?".format(text), ('上架', ))
        rst2 = cursor.fetchall()
        conn.close()
        for i in rst2:
            if i not in rst:
                rst.append(i)
        # print(rst)
        conn = sqlite3.connect('data.sqlite3')
        cursor = conn.cursor()
        final_rst = []
        for j in rst:
            seller_uid = j[1]
            cursor.execute("select * from user where tg_id=? ", (seller_uid,))
            seller_info = cursor.fetchone()
            if seller_info[3] == '开张':
                final_rst.append(j)
        conn.close()
        if len(final_rst) == 0:
            bot.send_message(
                chat_id=user_id,
                text='没有你想要的商品，换个关键词试试吧～'
            )
        else:
            random.shuffle(final_rst)
            if len(final_rst) >= 20:
                final_rst = final_rst[:20]
            ret_str = ''
            for i in final_rst:
                ret_str += "📦 [{}](https://t.me/{}?start=goods{}) \t\t{}元\n".format(
                    i[2], BOT_USERNAME, i[0], i[4])
            bot.send_message(
                chat_id=user_id,
                text="✅点击商品,再点击下方start查看\n" + ret_str[:-1],
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
    except Exception as e:
        print(e)


def admin_withdraw(update, context):
    query = update.callback_query
    query.answer()
    try:
        user_id = update.effective_user.id
        print('进入 admin_withdraw 函数 | ' + str(user_id))
        # print(update.message.text)
        # print(str(query))
        data = query.message.text
        # print(data)
        reg = re.search(r".*账单ID：(\d+)\nTG ID：(\d+).*", data)
        invoice_id = reg.group(1)
        withdrawer_tgid = reg.group(2)
        print(invoice_id, withdrawer_tgid)
        bot.send_message(
            chat_id=user_id,
            text='成功提币信息已发送至用户窗口！'
        )
        bot.send_message(
            chat_id=withdrawer_tgid,
            text='系统提示：您的提币请求已处理，到账可能有少许延迟，请耐心等待！'
        )
        update_one_from_db('invoice', 'status', '已处理', 'uid', invoice_id)
    except Exception as e:
        print(e)


admin_withdraw_handler = CallbackQueryHandler(admin_withdraw, pattern='^' + str('提币成功') + '$')
service_handler = MessageHandler(Filters.regex('^' + '🙋🏻‍️联系客服' + '$'), service)
search_goods_handler = MessageHandler(Filters.regex(r"(?<!标题).*"), search_goods)
start_handler = CommandHandler('start', start)
