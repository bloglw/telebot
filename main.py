from bot_starter import run_bot
import threading
from func import update_exchange_rate, delete_invoice, trade_monitor, del_complete_trade


thread = threading.Thread(target=update_exchange_rate)
thread2 = threading.Thread(target=trade_monitor)
thread3 = threading.Thread(target=delete_invoice)
thread4 = threading.Thread(target=del_complete_trade)
thread.start()
thread2.start()
thread3.start()
thread4.start()

run_bot()


