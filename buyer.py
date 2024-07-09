import telegram
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler
from config import TOKEN
import sqlite3
from func import cny_to_btc, selectone_one_from_db, btc_to_cny, btc_dis
from config import BOT_USERNAME

ROUTE, SELLER_FUNC = range(2)

bot = telegram.Bot(token=TOKEN)


def user_start(update, context):
    try:
        print('进入 user_start 函数')
        user_id = update.effective_user.id
        balance = selectone_one_from_db('balance', 'user', 'tg_id', user_id)
        keyboard = [
            [InlineKeyboardButton("个人详情", callback_data=str('个人详情')),
             InlineKeyboardButton("我买到的商品", callback_data=str('我买到的商品'))]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            '欢迎！你的余额: *{}* BTC (*{}*元)\n\n'
            '👇️点击 我买到的 可以查看 ✅已完成 和 ⏸未完成 的订单'.format(btc_dis(balance), btc_to_cny(balance)),
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return SELLER_FUNC
    except Exception as e:
        print(e)


def user_cancel(update, context):
    update.message.reply_text('期待再次见到你～')
    return ConversationHandler.END


def user_detail(update, context):
    print('进入 user_detail 函数')
    user_id = update.effective_user.id
    uuid = selectone_one_from_db('uuid', 'user', 'tg_id', user_id)
    balance = selectone_one_from_db('balance', 'user', 'tg_id', user_id)
    query = update.callback_query
    query.answer()
    keyboard = [
        [InlineKeyboardButton("个人详情", callback_data=str('个人详情')),
         InlineKeyboardButton("我买到的商品", callback_data=str('我买到的商品'))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        text="UID: {}\n"
             "💸可用余额: *{}* BTC (*{}*元)\n"
             "⚠️接受转账请点击复制，将UID发给对方".format(uuid, str(btc_dis(balance)), str(btc_to_cny(balance))),
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return SELLER_FUNC


def user_bought_goods(update, context):
    try:
        user_id = update.effective_user.id
        query = update.callback_query
        query.answer()
        keyboard = [
            [InlineKeyboardButton("个人详情", callback_data=str('个人详情')),
             InlineKeyboardButton("我买到的商品", callback_data=str('我买到的商品'))]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        conn = sqlite3.connect('data.sqlite3')
        cursor = conn.cursor()
        cursor.execute("select * from trade where buyer_tgid=? and trade_status!='交易取消' order by creat_time", (user_id,))
        rst = cursor.fetchall()
        conn.close()
        print(rst)
        ret_text = ''
        for i in rst:
            # print(i)
            trade_uid, goods_uid, price, trade_status = i[0], i[1], i[4], i[7]
            goods_name = selectone_one_from_db('title', 'goods', 'uid', goods_uid)
            ret_text += '{} \t [{}](https://t.me/{}?start=trade{}) \t *{}* BTC (*{}*元) \n'\
                .format(trade_status, goods_name, BOT_USERNAME, trade_uid, btc_dis(cny_to_btc(price)), price)
        query.edit_message_text(
            text="我买到的：\n" + ret_text[:-2],
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return SELLER_FUNC
    except Exception as e:
        print(e)


buyer_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^' + '👤买家中心' + '$'), user_start)],

        states={
            SELLER_FUNC: [
                MessageHandler(Filters.regex('^' + '👤买家中心' + '$'), user_start),
                CallbackQueryHandler(user_detail, pattern='^' + str('个人详情') + '$'),
                CallbackQueryHandler(user_bought_goods, pattern='^' + str('我买到的商品') + '$')
            ],
        },
        fallbacks=[CommandHandler('cancel', user_cancel)]
    )
