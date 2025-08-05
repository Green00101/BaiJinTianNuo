import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import pywmapi as wm

class BaiJinTianNuoApp:
    def __init__(self, root):
        self.root = root
        self.root.title('白金天诺 实验品')
        self.root.geometry('800x500')

        tk.Label(root, text='为了信息安全，你不应该在任何地方输入你的账号密码', fg='red', font=(None, 12, 'bold')).place(x=80, y=0)

        tk.Label(root, text='market 账号:').place(x=20, y=20)
        self.username_entry = tk.Entry(root, width=30)
        self.username_entry.place(x=120, y=20)

        tk.Label(root, text='market 密码:').place(x=370, y=20)
        self.password_entry = tk.Entry(root, width=30, show='*')
        self.password_entry.place(x=470, y=20)

        self.show_btn = tk.Button(root, text='显示所有物品', command=self.show_orders_thread)
        self.show_btn.place(x=150, y=60)
        self.update_btn = tk.Button(root, text='更新所有物品', command=self.update_orders_thread)
        self.update_btn.place(x=300, y=60)

        # 自动更新按钮
        self.auto_update_btn = tk.Button(root, text='每20分钟自动更新', command=self.start_auto_update)
        self.auto_update_btn.place(x=470, y=60)
        self.stop_auto_update_btn = tk.Button(root, text='停止自动更新', command=self.stop_auto_update, state='disabled')
        self.stop_auto_update_btn.place(x=630, y=60)

        # 倒计时标签
        self.countdown_label = tk.Label(root, text='')
        self.countdown_label.place(x=470, y=90)

        self.output = scrolledtext.ScrolledText(root, width=90, height=22, state='normal')
        self.output.place(x=20, y=110)

        # 底部灰色说明文字
        self.footer_label = tk.Label(root, text='软件由Green00101开发 本软件开源免费', fg='gray', font=(None, 10))
        self.footer_label.place(x=20, y=480)

        self.sess = None
        self.sell_orders = []
        self.buy_orders = []

        self.auto_update_running = False
        self.auto_update_timer = None
        self.countdown_seconds = 0
    def set_buttons_state(self, auto_running):
        # auto_running: True 表示自动计时器正在运行
        if auto_running:
            self.show_btn.config(state='disabled')
            self.update_btn.config(state='disabled')
            self.auto_update_btn.config(state='disabled')
            # 只有在自动计时器真正运行时才可用
            if self.auto_update_running and self.auto_update_timer:
                self.stop_auto_update_btn.config(state='normal')
            else:
                self.stop_auto_update_btn.config(state='disabled')
        else:
            self.show_btn.config(state='normal')
            self.update_btn.config(state='normal')
            self.auto_update_btn.config(state='normal')
            self.stop_auto_update_btn.config(state='disabled')

    def start_auto_update(self):
        if self.auto_update_running:
            return
        self.auto_update_running = True
        self.countdown_seconds = 1200  # 10分钟
        self.auto_update_timer = None
        self.set_buttons_state(True)
        self.auto_update_loop()

    def stop_auto_update(self):
        self.auto_update_running = False
        if self.auto_update_timer:
            self.root.after_cancel(self.auto_update_timer)
            self.auto_update_timer = None
        self.set_buttons_state(False)
        self.countdown_label.config(text='')

    def auto_update_loop(self):
        if not self.auto_update_running:
            self.set_buttons_state(False)
            return
        if self.countdown_seconds == 0:
            self.output.delete(1.0, tk.END)
            try:
                self.login()
                self.sell_orders, self.buy_orders = wm.orders.get_current_orders(self.sess)
                self.log('开始更新所有卖单:')
                for order in self.sell_orders:
                    item_name = getattr(order.item.zh_hans, 'item_name', order.item.url_name)
                    self.log(f"物品: {item_name} | 价格: {order.platinum} | 数量: {order.quantity}")
                    try:
                        updated_item = wm.orders.OrderNewItem(
                            item_id=order.item.id,
                            order_type=order.order_type,
                            platinum=order.platinum,
                            quantity=order.quantity,
                            rank=getattr(order, 'mod_rank', None),
                            visible=order.visible
                        )
                        wm.orders.update_order(self.sess, order.id, updated_item)
                        self.log('  -> 已更新')
                    except Exception as e:
                        self.log(f'  -> 更新失败: {e}')
                self.log('\n开始更新所有买单:')
                for order in self.buy_orders:
                    item_name = getattr(order.item.zh_hans, 'item_name', order.item.url_name)
                    self.log(f"物品: {item_name} | 价格: {order.platinum} | 数量: {order.quantity}")
                    try:
                        updated_item = wm.orders.OrderNewItem(
                            item_id=order.item.id,
                            order_type=order.order_type,
                            platinum=order.platinum,
                            quantity=order.quantity,
                            rank=getattr(order, 'mod_rank', None),
                            visible=order.visible
                        )
                        wm.orders.update_order(self.sess, order.id, updated_item)
                        self.log('  -> 已更新')
                    except Exception as e:
                        self.log(f'  -> 更新失败: {e}')
            except Exception as e:
                self.log(f"更新订单失败: {e}")
            self.countdown_seconds = 1200
        mins, secs = divmod(self.countdown_seconds, 60)
        self.countdown_label.config(text=f'下次刷新倒计时: {mins:02d}:{secs:02d}')
        self.countdown_seconds -= 1
        self.auto_update_timer = self.root.after(1000, self.auto_update_loop)
        self.set_buttons_state(True)

    def log(self, msg):
        self.output.insert(tk.END, msg + '\n')
        self.output.see(tk.END)
        self.output.update()

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if not username or not password:
            raise Exception('账号和密码不能为空')
        self.sess = wm.auth.signin(username, password)
        self.log('登录成功！')

    def show_orders(self):
        self.set_buttons_state(True)
        self.output.delete(1.0, tk.END)
        try:
            self.login()
            self.sell_orders, self.buy_orders = wm.orders.get_current_orders(self.sess)
            self.log('该用户所有卖单:')
            for order in self.sell_orders:
                item_name = getattr(order.item.zh_hans, 'item_name', order.item.url_name)
                self.log(f"物品: {item_name} | 价格: {order.platinum} | 数量: {order.quantity} | 类型: {order.order_type.value} | 最后更新时间: {order.last_update}")
            self.log('\n该用户所有买单:')
            for order in self.buy_orders:
                item_name = getattr(order.item.zh_hans, 'item_name', order.item.url_name)
                self.log(f"物品: {item_name} | 价格: {order.platinum} | 数量: {order.quantity} | 类型: {order.order_type.value} | 最后更新时间: {order.last_update}")
        except Exception as e:
            self.log(f"获取订单失败: {e}")
        self.set_buttons_state(False)

    def update_orders(self):
        self.set_buttons_state(True)
        self.output.delete(1.0, tk.END)
        try:
            self.login()
            self.sell_orders, self.buy_orders = wm.orders.get_current_orders(self.sess)
            self.log('开始更新所有卖单:')
            for order in self.sell_orders:
                item_name = getattr(order.item.zh_hans, 'item_name', order.item.url_name)
                self.log(f"物品: {item_name} | 价格: {order.platinum} | 数量: {order.quantity}")
                try:
                    updated_item = wm.orders.OrderNewItem(
                        item_id=order.item.id,
                        order_type=order.order_type,
                        platinum=order.platinum,
                        quantity=order.quantity,
                        rank=getattr(order, 'mod_rank', None),
                        visible=order.visible
                    )
                    wm.orders.update_order(self.sess, order.id, updated_item)
                    self.log('  -> 已更新')
                except Exception as e:
                    self.log(f'  -> 更新失败: {e}')
            self.log('\n开始更新所有买单:')
            for order in self.buy_orders:
                item_name = getattr(order.item.zh_hans, 'item_name', order.item.url_name)
                self.log(f"物品: {item_name} | 价格: {order.platinum} | 数量: {order.quantity}")
                try:
                    updated_item = wm.orders.OrderNewItem(
                        item_id=order.item.id,
                        order_type=order.order_type,
                        platinum=order.platinum,
                        quantity=order.quantity,
                        rank=getattr(order, 'mod_rank', None),
                        visible=order.visible
                    )
                    wm.orders.update_order(self.sess, order.id, updated_item)
                    self.log('  -> 已更新')
                except Exception as e:
                    self.log(f'  -> 更新失败: {e}')
        except Exception as e:
            self.log(f"更新订单失败: {e}")
        self.set_buttons_state(False)

    def show_orders_thread(self):
        if self.auto_update_running:
            return
        threading.Thread(target=self.show_orders, daemon=True).start()

    def update_orders_thread(self):
        if self.auto_update_running:
            return
        threading.Thread(target=self.update_orders, daemon=True).start()

if __name__ == '__main__':
    root = tk.Tk()
    app = BaiJinTianNuoApp(root)
    root.mainloop()
