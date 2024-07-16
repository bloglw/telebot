from django.urls import path
from django.http import HttpResponse
import sys
import requests
import json
import sqlite3
import telegram
sys.path.append("../")
from config import TOKEN


bot = telegram.Bot(token=TOKEN)


def rate():
    rst = requests.get('https://blockchain.info/ticker', timeout=5).text
    rst_dict = json.loads(rst)
    exchange_rate = rst_dict['CNY']['last']
    return float(exchange_rate)


def callback(request):
    try:
        if request.method == 'GET':
            # print(str(request.GET.get))
            invoice_id = request.GET.get('invoice_id', '')
            address = request.GET.get('address', '')
            value = int(request.GET.get('value', ''))

            confirmations = request.GET.get('confirmations', '')
            print('订单号：{}\n'
                  '收款钱包地址：{}\n'
                  '到账金额：{}'.format(invoice_id, address, value))
            conn = sqlite3.connect('../data.sqlite3')
            cursor = conn.cursor()
            cursor.execute("select * from invoice where uid=?", (invoice_id,))
            rst = cursor.fetchone()
            status = rst[5]
            if int(confirmations) >= 1 and status == '待转账':
                cursor.execute("update invoice set status=? where uid=?", ('已到账', invoice_id,))
                cursor.execute("update invoice set price=? where uid=?", (value, invoice_id,))
                user_tgid = rst[1]
                cursor.execute("select * from user where tg_id=?", (user_tgid,))
                user_balance = cursor.fetchone()[2]
                now_balance = int(user_balance + value)
                cursor.execute("update user set balance=? where tg_id=?", (now_balance, user_tgid,))
                conn.commit()
                conn.close()
                cny_amount = value * rate() / 100000000
                bot.send_message(
                    chat_id=user_tgid,
                    text='系统信息：您充值的{} BTC ( {}元 ) 已到账，请查收！'.format
                    ('{:.8f}'.format(value / 100000000), cny_amount)
                )
            return HttpResponse(content='回调成功！')
    except Exception as e:
        print(e)
        return HttpResponse(content='回调失败！参数错误')


urlpatterns = [
    path('callback/', callback, name='callback'),
]



