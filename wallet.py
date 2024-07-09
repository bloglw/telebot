import telegram
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply, ReplyKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler
from config import TOKEN, FEE, SMALLEST_AMOUNT, xPub, V2_API, HOST, ADMIN_ID
from func import cny_to_btc, selectone_one_from_db, selectall_one_from_db, btc_to_cny, update_one_from_db
from func import get_now_time, get_random_num, struct_time, btc_dis
import sqlite3
from blockchain.v2.receive import receive


ROUTE, WALLET_FUNC = range(2)

bot = telegram.Bot(token=TOKEN)

keyboard = [
        [InlineKeyboardButton("充币", callback_data=str('充币')),
         InlineKeyboardButton("提币", callback_data=str('提币')),
         InlineKeyboardButton("转账", callback_data=str('转账'))],
    ]


def wallet_start(update, context):
    print('进入 seller_start 函数')
    user_id = update.effective_user.id
    balance = selectone_one_from_db('balance', 'user', 'tg_id', user_id)
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        '💰你的余额: *{}* BTC (*{}*元)\n'
        '👉快速充币请联系BTC代购:@pdddg'.format(btc_dis(balance), btc_to_cny(balance)),
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return WALLET_FUNC


def wallet_cancel(update, context):
    print('进入 seller_cancel')
    update.message.reply_text('期待再次见到你～')
    return ConversationHandler.END


def recharge(update, context):
    try:
        print('进入 recharge')
        query = update.callback_query
        query.answer()
        user_id = update.effective_user.id
        wallet_status = selectone_one_from_db('wallet_status', 'user', 'tg_id', user_id)
        if wallet_status == '激活':
            conn = sqlite3.connect('data.sqlite3')
            cursor = conn.cursor()
            cursor.execute("select * from invoice where type=? and status=? and user_tgid=?", ('充币', '待转账', user_id))
            rst = cursor.fetchone()
            conn.close()
            if rst is not None:
                address = rst[6]
                end_time = int(rst[2]) + 43200
            else:
                conn = sqlite3.connect('data.sqlite3')
                cursor = conn.cursor()
                cursor.execute("select address from invoice where type=? and status=?", ('充币', '未使用'))
                rst = cursor.fetchone()
                conn.close()
                # print(rst)
                if rst is None:
                    invoice_id = get_random_num()
                    print(invoice_id)
                    callback_url = 'http://{}/callback/?invoice_id={}'.format(HOST, invoice_id)
                    recv = receive(xPub, callback_url, V2_API)
                    # print(str(recv))
                    address = recv.address
                    print(address)
                    conn = sqlite3.connect('data.sqlite3')
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO invoice VALUES (?,?,?,?,NULL,?,?)",
                                   (invoice_id, user_id, get_now_time(), '充币', '待转账', address))
                    conn.commit()
                    conn.close()
                    end_time = int(get_now_time()) + int(43200)
                else:
                    address = rst[0]
                    update_one_from_db('invoice', 'user_tgid', user_id, 'address', address)
                    update_one_from_db('invoice', 'status', '待转账', 'address', address)
                    update_one_from_db('invoice', 'creat_time', get_now_time(), 'address', address)
                    end_time = int(get_now_time()) + int(43200)
            print(address)
            bot.send_message(
                chat_id=user_id,
                text='充值地址：`{}`\n'
                     '地址有效期：{}\n'
                     '务必在24小时内转账，超时会导致到账失败！\n'
                     '充值没有金额限制，资金需1个区块确认后才会到账'.format(address, struct_time(end_time)),
                parse_mode='Markdown'
            )
            return WALLET_FUNC
        else:
            bot.send_message(
                chat_id=user_id,
                text='您的钱包已被锁定，如为误封，请联系管理解封！',
            )
    except Exception as e:
        print(e)


def withdraw(update, context):
    print('进入 withdraw')
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id
    wallet_status = selectone_one_from_db('wallet_status', 'user', 'tg_id', user_id)
    if wallet_status == '激活':
        bot.send_message(
            chat_id=user_id,
            text='提币需要扣除 *{}* BTC 矿工手续费，按照目前实时换算汇率，折合人民币：*{}* 元\n'
                 '最小提现数量为：*{}* BTC\n'
                 '请确保您的余额大于 *{}* BTC\n'
                 '提币数量小于10，提取单位为BTC\n'
                 '提币数量大于10，提取单位为人民币'.format
            (btc_dis(FEE), btc_to_cny(FEE), btc_dis(SMALLEST_AMOUNT), btc_dis(FEE + SMALLEST_AMOUNT)),
            parse_mode='Markdown'
        )
        bot.send_message(
            chat_id=user_id,
            text='请按照格式回复\n\n'
                 '⚠️格式：TB:比特币地址,需要提取的数量\n\n'
                 '例 (BTC)：TB:19jJyiC6DnKyKvPg38eBE8R6yCSXLLEjqw,0.001\n\n'
                 '例 (人民币)：TB:19jJyiC6DnKyKvPg38eBE8R6yCSXLLEjqw,200\n',
            parse_mode='Markdown'
        )
        return WALLET_FUNC
    else:
        bot.send_message(
            chat_id=user_id,
            text='您的钱包已被锁定，如为误封，请联系管理解封！',
        )


def transfer(update, context):
    print('进入 transfer')
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id
    wallet_status = selectone_one_from_db('wallet_status', 'user', 'tg_id', user_id)
    if wallet_status == '激活':
        bot.send_message(
            chat_id=user_id,
            text='提币数量小于10，提取单位为BTC\n'
                 '提币数量大于10，提取单位为人民币\n\n'
                 '️请发送“ ZZ:对方UID,转账金额 ”进行转账\n'
                 '️对方UID可让对方在买家中心 - 个人详情查看。\n'
                 '最小转账金额：*{}* BTC，转账不能转给自己。\n\n'
                 '️例 (BTC)：ZZ:15172946231976,0.01\n\n'
                 '️例 (人民币)：ZZ:15172946231976,200'.format(btc_dis(SMALLEST_AMOUNT)),
            parse_mode='Markdown'
        )
        return WALLET_FUNC
    else:
        bot.send_message(
            chat_id=user_id,
            text='您的钱包已被锁定，如为误封，请联系管理解封！',
        )


def withdraw_exec(update, context):
    print('进入 withdraw_exec')
    print(update.message.text)
    user_input = update.message.text
    user_id = update.effective_user.id
    try:
        split_1 = user_input.split(':')
        print(split_1)
        method = split_1[0]
        split_2 = split_1[1].split(',')
        address = split_2[0]
        withdraw_amount = float(split_2[1])
        print(method, address, withdraw_amount)
        if withdraw_amount < 10.00:
            btc_amount = int(withdraw_amount * 100000000)
        else:
            btc_amount = cny_to_btc(withdraw_amount)
        print(btc_amount)
        user_balance = int(selectone_one_from_db('balance', 'user', 'tg_id', user_id))
        if btc_amount < int(SMALLEST_AMOUNT+FEE):
            bot.send_message(
                chat_id=user_id,
                text='您输入的金额不满足最小提现金额！',
            )
            return WALLET_FUNC
        elif int(user_balance) < int(btc_amount):
            bot.send_message(
                chat_id=user_id,
                text='您的余额不足，请确认您输入的提币金额是否正确！',
            )
            return WALLET_FUNC
        else:
            user_uuid = selectone_one_from_db('uuid', 'user', 'tg_id', user_id)
            now_balance = user_balance - btc_amount
            actual_withdraw_btc = int(btc_amount - FEE)
            actual_withdraw_cny = btc_to_cny(actual_withdraw_btc)
            invoice_id = get_random_num()
            conn = sqlite3.connect('data.sqlite3')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO invoice VALUES (?,?,?,?,?,?,?)",
                           (invoice_id, user_id, str(get_now_time()), '提币', btc_amount, '待处理', address))
            conn.commit()
            conn.close()
            update_one_from_db('user', 'balance', now_balance, 'tg_id', user_id)
            keyboard = [[InlineKeyboardButton("提币成功", callback_data=str('提币成功'))]]
            for i in ADMIN_ID:
                bot.send_message(
                    chat_id=i,
                    text='用户提币申请：\n\n'
                         '账单ID：{}\n'
                         'TG ID：[{}](tg://user?id={})\n'
                         '提现总金额：{}BTC（{}元）\n'
                         '扣除手续费后的到账金额：{}（{}元）\n'
                         '提币地址：{}'.format
                    (invoice_id, user_id, user_id, btc_dis(btc_amount), btc_to_cny(btc_amount),
                     btc_dis(actual_withdraw_btc), btc_to_cny(actual_withdraw_btc), address),
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            bot.send_message(
                chat_id=user_id,
                text='您的 *{}* BTC (*{}*元)提币申请已经提交审核，请等待管理确认（扣除提币手续费）'.format(btc_dis(actual_withdraw_btc), actual_withdraw_cny),
                parse_mode='Markdown'
            )
            return ConversationHandler.END
    except Exception as e:
        print(e)
        bot.send_message(
            chat_id=user_id,
            text='格式错误，请重新输入！',
        )
        return WALLET_FUNC


def transfer_exec(update, context):
    print('进入 transfer_exec')
    print(update.message.text)
    user_input = update.message.text
    user_id = update.effective_user.id
    try:
        split_1 = user_input.split(':')
        # print(split_1)
        method = split_1[0]
        split_2 = split_1[1].split(',')
        address = split_2[0]
        withdraw_amount = float(split_2[1])
        print(method, address, withdraw_amount)
        if withdraw_amount < 10.00:
            btc_amount = int(withdraw_amount * 100000000)
        else:
            btc_amount = cny_to_btc(withdraw_amount)
        user_balance = int(selectone_one_from_db('balance', 'user', 'tg_id', user_id))
        user_uuid = selectone_one_from_db('uuid', 'user', 'tg_id', user_id)
        if str(address) == str(user_uuid):
            bot.send_message(
                chat_id=user_id,
                text='转账对象不能是自己！',
            )
            return WALLET_FUNC
        else:
            if int(user_balance) < int(btc_amount):
                bot.send_message(
                    chat_id=user_id,
                    text='您的余额不足，请确认您输入的转账金额是否正确！',
                )
                return WALLET_FUNC
            else:
                user2 = selectall_one_from_db('user', 'uuid', address)
                if user2 is None:
                    bot.send_message(
                        chat_id=user_id,
                        text='转账地址错误，请重新确认对方的UID！',
                    )
                    return WALLET_FUNC
                else:
                    user2_balance = user2[2]
                    now_user2_balance = int(btc_amount + user2_balance)
                    update_one_from_db('user', 'balance', now_user2_balance, 'uuid', address)
                    now_user1_balance = int(user_balance - btc_amount)
                    update_one_from_db('user', 'balance', now_user1_balance, 'tg_id', user_id)
                    bot.send_message(
                        chat_id=user_id,
                        text='您的 *{}* BTC (*{}*元)转账请求已经处理成功，款项已到达[{}](tg://user?id={})账户'.format
                        (btc_dis(btc_amount), btc_to_cny(btc_amount), address, address),
                        parse_mode='Markdown'
                    )
                    bot.send_message(
                        chat_id=user2[0],
                        text='系统提示：您的账户收到来自[{}](tg://user?id={})的转账，金额为 *{}* BTC (*{}*元)'.format(user_id, user_id, btc_dis(btc_amount), btc_to_cny(btc_amount)),
                        parse_mode='Markdown'
                    )
                    invoice_id = get_random_num()
                    conn = sqlite3.connect('data.sqlite3')
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO invoice VALUES (?,?,?,?,?,?,?)",
                                   (invoice_id, user_id, str(get_now_time()), '转账', btc_amount, '已提交', address))
                    conn.commit()
                    conn.close()
                    return ConversationHandler.END
    except Exception as e:
        print(e)
        bot.send_message(
            chat_id=user_id,
            text='格式错误，请重新输入！',
            parse_mode='Markdown'
        )
        return WALLET_FUNC


wallet_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^' + '🏧充币/提币/转账' + '$'), wallet_start)],

        states={
            WALLET_FUNC: [
                MessageHandler(Filters.regex('^' + '🏧充币/提币/转账' + '$'), wallet_start),
                CallbackQueryHandler(recharge, pattern='^' + str('充币') + '$'),
                CallbackQueryHandler(withdraw, pattern='^' + str('提币') + '$'),
                CallbackQueryHandler(transfer, pattern='^' + str('转账') + '$'),
                MessageHandler(Filters.regex(r"^TB:.*\d"), withdraw_exec),
                MessageHandler(Filters.regex(r"^ZZ:.*\d"), transfer_exec)
            ],
        },
        fallbacks=[CommandHandler('cancel', wallet_cancel)]
    )
