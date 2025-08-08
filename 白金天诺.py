import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import threading
import pywmapi as wm
import csv
import os
import requests
import time
import sys

class BaiJinTianNuoApp:
    def __init__(self, root):
        self.root = root
        self.root.title('白金天诺 测试版 1.0')
        self.root.geometry('1000x600')

        tk.Label(root, text='为了信息安全，你不应该在任何地方输入你的账号密码', fg='red', font=(None, 14, 'bold')).place(x=100, y=0)

        tk.Label(root, text='market 账号:', font=(None, 12)).place(x=20, y=30)
        self.username_entry = tk.Entry(root, width=35, font=(None, 12))
        self.username_entry.place(x=140, y=30)

        tk.Label(root, text='market 密码:', font=(None, 12)).place(x=450, y=30)
        self.password_entry = tk.Entry(root, width=35, show='*', font=(None, 12))
        self.password_entry.place(x=570, y=30)

        # 按钮居中布局
        btn_font = (None, 12)
        btn_width_char = 15  # 15个字符宽度
        btn_auto_width_char = 18 # 自动更新按钮宽度
        
        # 估算像素宽度
        btn_px_width = btn_width_char * 8 
        btn_auto_px_width = btn_auto_width_char * 8
        btn_padding = 40 # 增加按钮间距至40px
        
        # 按钮总宽度
        total_button_width = (btn_px_width * 4) + btn_auto_px_width + (btn_padding * 4)
        start_x = (1000 - total_button_width) / 2

        # 放置按钮
        current_x = start_x
        
        self.show_btn = tk.Button(root, text='显示所有物品', font=btn_font, width=btn_width_char, command=self.show_orders_thread)
        self.show_btn.place(x=current_x, y=70)
        current_x += btn_px_width + btn_padding

        self.price_btn = tk.Button(root, text='显示参考售价', font=btn_font, width=btn_width_char, command=self.show_reference_prices_thread)
        self.price_btn.place(x=current_x, y=70)
        current_x += btn_px_width + btn_padding

        self.update_btn = tk.Button(root, text='更新所有物品', font=btn_font, width=btn_width_char, command=self.update_orders_thread)
        self.update_btn.place(x=current_x, y=70)
        current_x += btn_px_width + btn_padding
        
        self.auto_update_btn = tk.Button(root, text='每20分钟自动更新', font=btn_font, width=btn_auto_width_char, command=self.start_auto_update)
        self.auto_update_btn.place(x=current_x, y=70)

        # 倒计时标签（放在按钮下方）
        self.countdown_label = tk.Label(root, text='', font=(None, 11))
        self.countdown_label.place(x=current_x, y=105)
        current_x += btn_auto_px_width + btn_padding
        
        self.stop_auto_update_btn = tk.Button(root, text='停止自动更新', font=btn_font, width=btn_width_char, state='disabled', command=self.stop_auto_update)
        self.stop_auto_update_btn.place(x=current_x, y=70)

        # 创建表格
        self.setup_table()

        # 底部灰色说明文字
        self.footer_label = tk.Label(root, text='软件由Green00101开发 本软件开源免费', fg='gray', font=(None, 12))
        self.footer_label.place(x=20, y=580)

        self.sess = None
        self.sell_orders = []
        self.buy_orders = []

        self.auto_update_running = False
        self.auto_update_timer = None
        self.countdown_seconds = 0
        self.update_in_progress = False  # 新增：更新状态锁
        
        # 行状态跟踪系统
        self.row_states = {}  # 存储每行的状态 {'item_id': {'state': 'new/modified/deleted', 'original_data': {}, 'current_data': {}}}
        self.item_names_data = {}  # 存储CSV中的物品名称数据
        self.next_temp_id = 1  # 为新添加的行分配临时ID
        
        # 加载物品名称数据
        self.load_item_names()

    def setup_table(self):
        # 创建表格框架
        table_frame = tk.Frame(self.root)
        table_frame.place(x=20, y=130, width=960, height=400)
        
        # 定义列 - 添加类型列
        columns = ('name', 'ref_price', 'type', 'price', 'rank', 'quantity')
        
        # 创建Treeview表格
        self.table = ttk.Treeview(table_frame, columns=columns, show='headings', height=18)
        
        # 设置表格字体和行高
        style = ttk.Style()
        style.configure("Treeview", font=('Microsoft YaHei', 12), rowheight=28) # 减小字号和行高
        style.configure("Treeview.Heading", font=('Microsoft YaHei', 12, 'bold'))
        
        # 设置列标题
        self.table.heading('name', text='名称')
        self.table.heading('ref_price', text='参考售价')
        self.table.heading('type', text='类型')
        self.table.heading('price', text='价格')
        self.table.heading('rank', text='等级')
        self.table.heading('quantity', text='数量')
        
        # 调整列宽度
        self.table.column('name', width=160, minwidth=160)        # 名称
        self.table.column('ref_price', width=420, minwidth=360)   # 参考售价
        self.table.column('type', width=60, minwidth=50)          # 类型
        self.table.column('price', width=60, minwidth=50)         # 价格
        self.table.column('rank', width=60, minwidth=50)          # 等级
        self.table.column('quantity', width=60, minwidth=50)      # 数量
        
        # 创建滚动条
        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        self.table.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # 添加表格下方的按钮
        add_btn_width = 12 * 8 # 估算像素宽度
        delete_btn_x = 860
        add_btn_x = delete_btn_x - add_btn_width - 40 # 40px间距

        self.add_btn = tk.Button(self.root, text='添加', font=(None, 12), width=12, command=self.add_row)
        self.add_btn.place(x=add_btn_x, y=540)
        
        self.delete_btn = tk.Button(self.root, text='删除', font=(None, 12), width=12, state='disabled', command=self.delete_row)
        self.delete_btn.place(x=delete_btn_x, y=540)
        
        # 绑定表格选择事件
        self.table.bind('<<TreeviewSelect>>', self.on_table_select)
        # 绑定双击编辑事件
        self.table.bind('<Double-1>', self.on_table_double_click)

    def load_item_names(self):
        """加载CSV文件中的物品名称数据，兼容打包后的EXE环境"""
        try:
            # 确定资源文件的正确路径
            if getattr(sys, 'frozen', False):
                # 如果是打包后的EXE文件（'frozen'属性会被pyinstaller设置）
                base_path = sys._MEIPASS
            else:
                # 如果是直接运行的.py脚本
                base_path = os.path.dirname(os.path.abspath(__file__))
            
            csv_file_path = os.path.join(base_path, 'wfm_item_names_en_zh.csv')
            print(f"尝试从以下路径加载CSV: {csv_file_path}")

            if os.path.exists(csv_file_path):
                with open(csv_file_path, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        chinese_name = row.get('Chinese', '').strip()
                        url_name = row.get('url_name', '').strip()
                        english_name = row.get('English', '').strip()
                        if chinese_name:
                            self.item_names_data[chinese_name] = {
                                'url_name': url_name,
                                'english': english_name,
                                'chinese': chinese_name
                            }
                print(f"成功加载 {len(self.item_names_data)} 个物品名称")
            else:
                print("错误：在指定路径找不到 wfm_item_names_en_zh.csv")
                messagebox.showerror("严重错误", "无法找到核心数据文件 wfm_item_names_en_zh.csv！\n程序无法运行。")
                self.root.destroy()

        except Exception as e:
            print(f"加载物品名称失败: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("严重错误", f"加载核心数据文件时发生致命错误: {e}")
            self.root.destroy()

    def get_item_info(self, name):
        """获取物品信息，支持·转空格查找"""
        name = name.strip()
        # 直接查找
        if name in self.item_names_data:
            return self.item_names_data[name]
        # 如果包含·，转换为空格后再查找
        if '·' in name:
            name_with_space = name.replace('·', ' ')
            if name_with_space in self.item_names_data:
                return self.item_names_data[name_with_space]
        return None

    def validate_item_name(self, name):
        """验证物品名称是否在CSV文件中"""
        return self.get_item_info(name) is not None

    def get_item_id_from_table(self, item):
        """从表格项目获取或生成ID"""
        # 尝试从row_states中查找现有ID
        for row_id, state_data in self.row_states.items():
            if state_data.get('table_item') == item:
                return row_id
        
        # 为新项目生成临时ID
        temp_id = f"temp_{self.next_temp_id}"
        self.next_temp_id += 1
        return temp_id

    def update_row_color(self, item, state):
        """更新行的背景颜色"""
        if state == 'new':
            self.table.item(item, tags=('new',))
        elif state == 'modified':
            self.table.item(item, tags=('modified',))
        elif state == 'deleted':
            self.table.item(item, tags=('deleted',))
        else:  # 包括 'existing' 状态
            self.table.item(item, tags=())
        
        # 配置标签样式
        self.table.tag_configure('new', background='lightgreen')
        self.table.tag_configure('modified', background='lightblue', foreground='blue')
        self.table.tag_configure('deleted', background='lightcoral')

    def show_log_window(self, title="操作日志"):
        """显示日志窗口"""
        log_window = tk.Toplevel(self.root)
        log_window.title(title)
        log_window.geometry('600x400')
        log_window.transient(self.root)
        log_window.grab_set()
        
        log_text = scrolledtext.ScrolledText(log_window, width=70, height=20)
        log_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        return log_window, log_text

    def on_table_select(self, event):
        """表格选择事件处理"""
        # 如果自动更新正在运行，删除按钮保持禁用状态
        if self.auto_update_running:
            self.delete_btn.config(state='disabled')
            return
            
        selection = self.table.selection()
        if selection:
            self.delete_btn.config(state='normal')
        else:
            self.delete_btn.config(state='disabled')

    def on_table_double_click(self, event):
        """表格双击编辑事件"""
        if self.auto_update_running:
            return
            
        item = self.table.selection()[0] if self.table.selection() else None
        if not item:
            return
            
        # 获取点击的列
        column = self.table.identify_column(event.x)
        if not column or column == '':
            return
        
        # 从 '#1', '#2' 等格式中提取数字
        try:
            column_num = int(column.replace('#', ''))
            if column_num < 1 or column_num > len(self.table['columns']):
                return
            column_name = self.table['columns'][column_num - 1]
        except (ValueError, IndexError):
            return
        
        # 只允许编辑特定列
        editable_columns = ['name', 'type', 'price', 'quantity']
        if column_name not in editable_columns:
            return
            
        # 获取当前值
        current_values = self.table.item(item, 'values')
        current_value = current_values[column_num - 1]
        
        # 创建编辑窗口
        self.create_edit_dialog(item, column_name, current_value)

    def create_edit_dialog(self, item, column_name, current_value):
        """创建编辑对话框"""
        edit_window = tk.Toplevel(self.root)
        
        # 定义列名映射
        column_map = {
            'name': '名称',
            'price': '价格',
            'quantity': '数量',
            #'rank': '等级',
            'type': '类型'
        }
        display_name = column_map.get(column_name, column_name.capitalize())
        
        edit_window.title(f'编辑 {display_name}')
        edit_window.geometry('400x200')
        edit_window.transient(self.root)
        edit_window.grab_set()
        
        # 居中显示
        edit_window.geometry("+%d+%d" % (self.root.winfo_rootx() + 200, self.root.winfo_rooty() + 100))
        
        tk.Label(edit_window, text=f'编辑 {display_name}:', font=(None, 12)).pack(pady=10)
        
        # 根据列类型创建不同的输入控件
        if column_name == 'type':
            # 类型选择
            var = tk.StringVar(value=current_value)
            type_frame = tk.Frame(edit_window)
            type_frame.pack(pady=10)
            
            tk.Radiobutton(type_frame, text='买单', variable=var, value='买单', font=(None, 12)).pack(side='left', padx=10)
            tk.Radiobutton(type_frame, text='卖单', variable=var, value='卖单', font=(None, 12)).pack(side='left', padx=10)
            
            entry = var
        else:
            # 文本输入
            entry = tk.Entry(edit_window, font=(None, 12), width=30)
            entry.pack(pady=10)
            entry.insert(0, current_value)
            entry.focus()
        
        # 按钮框架
        btn_frame = tk.Frame(edit_window)
        btn_frame.pack(pady=20)
        
        def save_edit():
            if column_name == 'type':
                new_value = entry.get()
            else:
                new_value = entry.get().strip()
                
            # 验证输入
            if column_name == 'name':
                if not self.validate_item_name(new_value):
                    messagebox.showerror("错误", "无效的物品名称，请确保名称存在于核心数据文件中。")
                    return
            elif column_name in ['price', 'quantity']:
                try:
                    value = float(new_value)
                    if value <= 0:
                        messagebox.showerror("错误", f"{display_name} 必须是大于0的数字。")
                        return
                except ValueError:
                    messagebox.showerror("错误", f"{display_name} 必须是有效的数字。")
                    return
            elif column_name == 'rank':
                if new_value and not new_value.isdigit():
                    messagebox.showerror("错误", f"{display_name} 必须是整数。")
                    return
            
            # 更新表格
            self.update_table_cell(item, column_name, new_value)
            edit_window.destroy()
        
        def cancel_edit():
            edit_window.destroy()
        
        tk.Button(btn_frame, text='保存', command=save_edit, font=(None, 12)).pack(side='left', padx=10)
        tk.Button(btn_frame, text='取消', command=cancel_edit, font=(None, 12)).pack(side='left', padx=10)
        
        # 绑定回车键
        if column_name != 'type':
            entry.bind('<Return>', lambda e: save_edit())
        edit_window.bind('<Escape>', lambda e: cancel_edit())

    def update_table_cell(self, item, column_name, new_value):
        """更新表格单元格并标记状态"""
        # 获取当前值
        current_values = list(self.table.item(item, 'values'))
        
        # 找到列索引
        columns = ['name', 'ref_price', 'type', 'price', 'rank', 'quantity']
        if column_name in columns:
            col_index = columns.index(column_name)
            old_value = current_values[col_index]
            current_values[col_index] = new_value
            
            # 更新表格显示
            self.table.item(item, values=current_values)
            
            # 更新行状态
            item_id = self.get_item_id_from_table(item)
            
            # 如果是新行，保持新状态，并更新其数据
            if item_id in self.row_states and self.row_states[item_id]['state'] == 'new':
                self.row_states[item_id]['current_data'] = dict(zip(columns, current_values))
                self.update_row_color(item, 'new')
            else:
                # 标记为已修改
                if item_id not in self.row_states:
                    self.row_states[item_id] = {
                        'state': 'modified',
                        'table_item': item,
                        'original_data': dict(zip(columns, self.table.item(item, 'values'))),
                        'current_data': dict(zip(columns, current_values))
                    }
                else:
                    self.row_states[item_id]['state'] = 'modified'
                    self.row_states[item_id]['current_data'] = dict(zip(columns, current_values))
                
                self.update_row_color(item, 'modified')

    def add_row(self):
        """添加新行到表格"""
        if self.auto_update_running:
            return
            
        # 创建新行
        new_item = self.table.insert('', 'end', values=(
            '新物品',    # 名称占位
            '',      # 参考售价占位
            '卖单',   # 类型占位
            '0',      # 价格占位
            '',      # 等级占位
            '1'       # 数量占位
        ))
        
        # 标记为新行
        temp_id = f"temp_{self.next_temp_id}"
        self.next_temp_id += 1
        
        columns = ['name', 'ref_price', 'type', 'price', 'rank', 'quantity']
        self.row_states[temp_id] = {
            'state': 'new',
            'table_item': new_item,
            'original_data': None,  # 新行没有原始数据
            'current_data': dict(zip(columns, self.table.item(new_item, 'values')))
        }
        
        # 设置绿色背景
        self.update_row_color(new_item, 'new')
        
        # 自动滚动到表格最下面
        self.table.see(new_item)

    def delete_row(self):
        """删除选中的行"""
        if self.auto_update_running:
            return
            
        selection = self.table.selection()
        if selection:
            for item in selection:
                # 获取行ID
                item_id = self.get_item_id_from_table(item)
                
                # 如果是新添加的行，直接删除
                if item_id in self.row_states and self.row_states[item_id]['state'] == 'new':
                    self.table.delete(item)
                    del self.row_states[item_id]
                else:
                    # 如果是已存在的行，标记为删除（红色背景）
                    if item_id not in self.row_states:
                        columns = ['name', 'ref_price', 'type', 'price', 'rank', 'quantity']
                        self.row_states[item_id] = {
                            'state': 'deleted',
                            'table_item': item,
                            'original_data': dict(zip(columns, self.table.item(item, 'values'))),
                            'current_data': dict(zip(columns, self.table.item(item, 'values')))
                        }
                    else:
                        self.row_states[item_id]['state'] = 'deleted'
                    
                    # 设置红色背景
                    self.update_row_color(item, 'deleted')
            
            # 删除后重新检查选择状态
            self.delete_btn.config(state='disabled')

    def refresh_table_data(self):
        """用当前的订单数据纯粹地刷新表格，会保留现有的row_states"""
        
        # 清空表格
        for item in self.table.get_children():
            self.table.delete(item)
        
        # 备份并清空新的订单ID
        processed_table_items = {}

        all_orders = [('sell', order) for order in self.sell_orders] + \
                     [('buy', order) for order in self.buy_orders]

        # 优先处理并恢复已存在（可能被修改/删除）的订单
        for order_id, state_data in list(self.row_states.items()):
            table_item = state_data.get('table_item')
            if table_item:
                current_values = list(state_data['current_data'].values())
                new_item = self.table.insert('', 'end', values=current_values, iid=table_item)
                self.update_row_color(new_item, state_data['state'])
                processed_table_items[table_item] = True

        # 添加服务器返回的、但不在本地状态中的新订单
        for order_type, order in all_orders:
            order_id = f"{order_type}_{order.id}"
            
            # 查找此订单是否已在UI上
            item_in_ui = None
            for key, state in self.row_states.items():
                if state.get('order_id') == order.id:
                    item_in_ui = state.get('table_item')
                    break
            
            if item_in_ui and item_in_ui in processed_table_items:
                continue

            # 如果不在，则作为新行添加
            item_name = getattr(order.item.zh_hans, 'item_name', order.item.url_name)
            rank = getattr(order, 'mod_rank', '') if hasattr(order, 'mod_rank') and order.mod_rank is not None else ''
            
            # WFM API的逻辑是，sell_orders里是你想买的，所以是买单；buy_orders里是你想卖的，所以是卖单
            display_type = '买单' if order_type == 'sell' else '卖单'

            item = self.table.insert('', 'end', values=(
                item_name, '', display_type, order.platinum, rank, order.quantity
            ))
            
            # 更新状态
            columns = ['name', 'ref_price', 'type', 'price', 'rank', 'quantity']
            self.row_states[order_id] = {
                'state': 'existing',
                'table_item': item,
                'original_data': dict(zip(columns, self.table.item(item, 'values'))),
                'current_data': dict(zip(columns, self.table.item(item, 'values'))),
                'order_id': order.id,
                'order_type': order_type
            }

        # 重新添加临时的新增行
        for item_id, state_data in self.row_states.items():
            if state_data['state'] == 'new':
                new_item = self.table.insert('', 'end', values=list(state_data['current_data'].values()))
                state_data['table_item'] = new_item
                self.update_row_color(new_item, 'new')
    def set_buttons_state(self, auto_running):
        # auto_running: True 表示自动计时器正在运行
        if auto_running:
            self.show_btn.config(state='disabled')
            self.price_btn.config(state='disabled')
            self.update_btn.config(state='disabled')
            self.auto_update_btn.config(state='disabled')
            self.add_btn.config(state='disabled')
            self.delete_btn.config(state='disabled')
            # 只有在自动计时器真正运行时才可用
            if self.auto_update_running and self.auto_update_timer:
                self.stop_auto_update_btn.config(state='normal')
            else:
                self.stop_auto_update_btn.config(state='disabled')
        else:
            self.show_btn.config(state='normal')
            self.price_btn.config(state='normal')
            self.update_btn.config(state='normal')
            self.auto_update_btn.config(state='normal')
            self.add_btn.config(state='normal')
            self.stop_auto_update_btn.config(state='disabled')
            # 删除按钮状态根据表格选择情况决定
            selection = self.table.selection()
            if selection:
                self.delete_btn.config(state='normal')
            else:
                self.delete_btn.config(state='disabled')

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
        # 如果更新正在进行，则暂停此循环
        if self.update_in_progress:
            return

        if not self.auto_update_running:
            self.set_buttons_state(False)
            return
            
        if self.countdown_seconds <= 0:
            # 锁定状态并开始更新
            self.update_in_progress = True
            self.stop_auto_update_btn.config(state='disabled')
            self.countdown_label.config(text='更新中 请稍等...')
            
            def update_in_background():
                print("自动更新所有物品...")
                try:
                    self._update_orders_logic()
                    print("自动更新完成")

                    # 更新成功后，在主线程中调用“显示所有物品”的静默版本
                    print("更新后自动静默刷新...")
                    self.root.after(100, self.show_orders_silently)

                except Exception as e:
                    print(f"自动更新所有物品失败: {e}")
                finally:
                    # 更新完成或失败后，在主线程中解锁并重启循环
                    def resume_loop():
                        self.update_in_progress = False
                        if self.auto_update_running:
                            self.countdown_seconds = 1200
                            self.stop_auto_update_btn.config(state='normal')
                            self.auto_update_loop()  # 重新启动循环
                    
                    # 延迟2秒重启循环，给 show_orders 的弹窗和刷新留出时间
                    self.root.after(2000, resume_loop)

            threading.Thread(target=update_in_background, daemon=True).start()
            return  # 立即返回，等待后台线程重启循环
        
        # 正常的倒计时逻辑
        mins, secs = divmod(self.countdown_seconds, 60)
        self.countdown_label.config(text=f'下次刷新倒计时: {mins:02d}:{secs:02d}')
        self.countdown_seconds -= 1
        self.auto_update_timer = self.root.after(1000, self.auto_update_loop)
        self.set_buttons_state(True)

    def log(self, msg, log_text=None):
        if log_text and log_text.winfo_exists():
            log_text.insert(tk.END, msg + '\n')
            log_text.see(tk.END)
            log_text.update()

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if not username or not password:
            raise Exception('账号和密码不能为空')
        self.sess = wm.auth.signin(username, password)

    def show_orders(self):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.set_buttons_state(True)
                
                self.login()
                self.sell_orders, self.buy_orders = wm.orders.get_current_orders(self.sess)
                
                self.row_states.clear()
                self.next_temp_id = 1

                self.refresh_table_data()
                    
                messagebox.showinfo("成功", f"已加载 {len(self.sell_orders)} 个买单和 {len(self.buy_orders)} 个卖单")
                
                # 成功后退出循环
                return

            except Exception as e:
                # 专门捕获JSON解码错误
                if "Expecting value" in str(e) and attempt < max_retries - 1:
                    print(f"获取订单时收到空响应 (尝试 {attempt + 1}/{max_retries})，1秒后重试...")
                    time.sleep(1)
                    continue
                else:
                    messagebox.showerror("错误", f"获取订单失败: {e}")
                    return # 发生其他错误或重试耗尽时，直接返回
            
            finally:
                self.set_buttons_state(False)

    def show_orders_silently(self):
        """静默版本的show_orders，不弹窗，不管理按钮状态"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.login()
                self.sell_orders, self.buy_orders = wm.orders.get_current_orders(self.sess)
                
                self.row_states.clear()
                self.next_temp_id = 1

                self.refresh_table_data()
                print("静默刷新成功。")
                return
            except Exception as e:
                if "Expecting value" in str(e) and attempt < max_retries - 1:
                    print(f"静默刷新时收到空响应 (尝试 {attempt + 1}/{max_retries})，1秒后重试...")
                    time.sleep(1)
                    continue
                else:
                    print(f"静默刷新失败: {e}")
                    return

    def _update_orders_logic(self, log_text=None):
        """更新所有物品的核心逻辑（无UI窗口）"""
        try:
            self.login()
            if log_text: self.log('登录成功！', log_text)

            # 1. 首先，获取服务器上最新的订单状态
            if log_text: self.log('正在获取最新的订单列表...', log_text)
            self.sell_orders, self.buy_orders = wm.orders.get_current_orders(self.sess)
            all_server_orders = self.sell_orders + self.buy_orders
            if log_text: self.log(f'获取成功，共 {len(all_server_orders)} 个订单。\n', log_text)

            # 2. 处理标记为删除的订单
            if log_text: self.log('处理删除的订单:', log_text)
            deleted_count = 0
            processed_order_ids = set() # 用于跟踪已处理的ID

            for item_id, state_data in list(self.row_states.items()):
                if state_data['state'] == 'deleted' and 'order_id' in state_data:
                    try:
                        order_id = state_data['order_id']
                        item_name = state_data['original_data']['name']
                        if log_text: self.log(f"删除订单: {item_name}", log_text)
                        wm.orders.delete_order(self.sess, order_id)
                        
                        self.table.delete(state_data['table_item'])
                        del self.row_states[item_id]
                        deleted_count += 1
                        processed_order_ids.add(order_id)
                        if log_text: self.log('  -> 已删除', log_text)
                    except Exception as e:
                        if log_text: self.log(f'  -> 删除失败: {e}', log_text)
            
            if deleted_count > 0 and log_text:
                self.log(f'共删除 {deleted_count} 个订单\n', log_text)
            
            # 3. 处理修改的订单
            if log_text: self.log('处理修改的订单:', log_text)
            modified_count = 0
            modified_items_to_reset = []
            
            for item_id, state_data in self.row_states.items():
                if state_data['state'] == 'modified' and 'order_id' in state_data:
                    try:
                        order_id = state_data['order_id']
                        current_data = state_data['current_data']
                        item_name = current_data['name']
                        
                        target_order = next((o for o in all_server_orders if o.id == order_id), None)
                        
                        if target_order:
                            if log_text: self.log(f"更新订单: {item_name} | 价格: {current_data['price']} | 数量: {current_data['quantity']}", log_text)
                            updated_item = wm.orders.OrderNewItem(
                                item_id=target_order.item.id,
                                order_type=target_order.order_type,
                                platinum=int(float(current_data['price'])),
                                quantity=int(float(current_data['quantity'])),
                                rank=getattr(target_order, 'mod_rank', None),
                                visible=target_order.visible
                            )
                            wm.orders.update_order(self.sess, order_id, updated_item)
                            modified_count += 1
                            processed_order_ids.add(order_id)
                            modified_items_to_reset.append((item_id, state_data))
                            if log_text: self.log('  -> 已更新', log_text)
                    except Exception as e:
                        if log_text: self.log(f'  -> 更新失败: {e}', log_text)

            for item_id, state_data in modified_items_to_reset:
                state_data['state'] = 'existing'
                state_data['original_data'] = state_data['current_data'].copy()
                self.update_row_color(state_data['table_item'], 'existing')
            
            if modified_count > 0 and log_text:
                self.log(f'共修改 {modified_count} 个订单\n', log_text)
            
            # 4. 处理新增的订单
            if log_text: self.log('处理新增的订单:', log_text)
            new_count = 0
            for item_id, state_data in list(self.row_states.items()):
                if state_data['state'] == 'new':
                    try:
                        current_data = state_data['current_data']
                        item_name = current_data['name']
                        item_info = self.get_item_info(item_name)
                        if not item_info: raise Exception(f"'{item_name}' 不在CSV中")
                        
                        url_name = item_info['url_name']
                        if not url_name: raise Exception(f"'{item_name}' 的 url_name 为空")
                        
                        item_details_tuple = wm.items.get_item(url_name)
                        wfm_item_id = item_details_tuple[0].id
                        
                        order_type = wm.common.OrderType.sell if current_data['type'] == '卖单' else wm.common.OrderType.buy
                        platinum = int(float(current_data['price']))
                        quantity = int(float(current_data['quantity']))
                        rank = int(r) if (r := str(current_data.get('rank', ''))).isdigit() else None
                        
                        if log_text: self.log(f"新增: {item_name} | {platinum}p x {quantity}", log_text)
                        
                        new_order_item = wm.orders.OrderNewItem(
                            item_id=wfm_item_id, order_type=order_type, platinum=platinum,
                            quantity=quantity, rank=rank, visible=True
                        )
                        wm.orders.add_order(self.sess, new_order_item)
                        new_count += 1
                        if log_text: self.log('  -> 已新增', log_text)
                        
                        self.table.delete(state_data['table_item'])
                        del self.row_states[item_id]
                    except Exception as e:
                        if log_text: self.log(f"  -> 新增订单 '{item_name}' 失败: {e}", log_text)
            
            if new_count > 0 and log_text:
                self.log(f'共新增 {new_count} 个订单\n', log_text)
            
            # 5. 标准更新所有剩余订单（排除已处理的）
            if log_text: self.log('标准更新所有现有订单:', log_text)
            updated_standard_count = 0
            for order in all_server_orders:
                if order.id in processed_order_ids:
                    continue
                
                item_name = getattr(order.item.zh_hans, 'item_name', order.item.url_name)
                if log_text: self.log(f"更新: {item_name}", log_text)
                try:
                    updated_item = wm.orders.OrderNewItem(
                        item_id=order.item.id, order_type=order.order_type, platinum=order.platinum,
                        quantity=order.quantity, rank=getattr(order, 'mod_rank', None), visible=order.visible
                    )
                    wm.orders.update_order(self.sess, order.id, updated_item)
                    updated_standard_count += 1
                except Exception as e:
                    if log_text: self.log(f'  -> 更新失败: {e}', log_text)
            
            if updated_standard_count > 0 and log_text:
                self.log(f'标准更新了 {updated_standard_count} 个订单', log_text)
            
            if log_text: self.log('\n所有订单更新完成！', log_text)
            
            # 在主线程中调用UI更新
            def do_refresh():
                self.sell_orders, self.buy_orders = wm.orders.get_current_orders(self.sess)
                self.refresh_table_data()
            self.root.after(0, do_refresh)
            
        except Exception as e:
            if log_text: self.log(f"更新订单失败: {e}", log_text)
            print(f"后台更新失败: {e}")

    def update_orders(self):
        # 首先检查是否有未完成编辑的新增行
        for item_id, state_data in self.row_states.items():
            if state_data['state'] == 'new':
                item_name = state_data['current_data']['name']
                if not self.validate_item_name(item_name):
                    messagebox.showerror(
                        "操作中断",
                        f"无法更新，因为存在无效的新增物品: '{item_name}'。\n\n"
                        "请先双击该行，将物品名称修改为CSV文件中的有效中文名称。"
                    )
                    return  # 中断更新

        self.set_buttons_state(True)
        log_window, log_text = self.show_log_window("更新订单日志")
        
        try:
            self._update_orders_logic(log_text=log_text)
        finally:
            self.set_buttons_state(False)
            
            # 延迟1秒后自动执行"显示所有物品"
            def delayed_refresh():
                try:
                    # 重新获取最新的订单数据
                    if hasattr(self, 'sess') and self.sess:
                        self.sell_orders, self.buy_orders = wm.orders.get_current_orders(self.sess)
                        self.refresh_table_data()
                        # 在日志窗口显示完成信息
                        if 'log_text' in locals() and log_text.winfo_exists():
                            self.log('已自动刷新显示最新的订单数据', log_text)
                except Exception as e:
                    print(f"自动刷新失败: {e}")
            
            # 使用tkinter的after方法延迟1秒执行
            self.root.after(1000, delayed_refresh)

    def _update_reference_prices_logic(self, log_text=None):
        """获取并更新参考售价的核心逻辑（无UI窗口）"""
        try:
            if log_text: self.log('开始获取参考售价...', log_text)
            
            for item in self.table.get_children():
                values = list(self.table.item(item, 'values'))
                item_name = values[0]
                
                if not item_name or item_name in ['新物品', '0']:
                    continue
                
                if not self.validate_item_name(item_name):
                    if log_text: self.log(f"跳过无效物品: {item_name}", log_text)
                    continue
                
                try:
                    item_info = self.get_item_info(item_name)
                    if not item_info:
                        if log_text: self.log(f"物品 '{item_name}' 不在CSV数据中", log_text)
                        continue
                    
                    url_name = item_info['url_name']
                    if log_text: self.log(f"正在获取 {item_name} 的价格信息 (官方API)...", log_text)
                    
                    api_url = f"https://api.warframe.market/v1/items/{url_name}/orders"
                    headers = {'Platform': 'pc', 'Language': 'en'}
                    response = requests.get(api_url, headers=headers, timeout=10)
                    response.raise_for_status()
                    
                    orders_data = response.json()
                    price_summary = self.analyze_prices(orders_data, log_text)
                    
                    values[1] = price_summary
                    self.table.item(item, values=values)
                    
                    if log_text: self.log(f"  -> {item_name}: {price_summary}", log_text)
                    
                except Exception as e:
                    if log_text: self.log(f"获取 {item_name} 价格失败: {e}", log_text)
            
            if log_text: self.log('\n参考售价获取完成！', log_text)
            
        except Exception as e:
            if log_text: self.log(f"获取参考售价失败: {e}", log_text)

    def show_reference_prices(self):
        """（用户操作）显示参考售价，带日志窗口"""
        self.set_buttons_state(True)
        log_window, log_text = self.show_log_window("获取参考售价")
        
        try:
            self._update_reference_prices_logic(log_text=log_text)
        finally:
            self.set_buttons_state(False)
    
    def analyze_prices(self, orders_data, log_text):
        """分析价格数据，返回格式化的价格摘要"""
        try:
            # 官方API返回的是JSON数据
            orders = orders_data.get('payload', {}).get('orders', [])
            
            # 过滤出卖单 (order_type == 'sell')
            sell_orders = [o for o in orders if o.get('order_type') == 'sell']
            
            # 按白金价格从低到高排序
            sell_orders.sort(key=lambda o: o.get('platinum', 9999))
            
            # 过滤在线玩家的订单
            online_orders = []
            for order in sell_orders:
                user = order.get('user', {})
                status = user.get('status')
                if status in ['ingame', 'online']:
                    online_orders.append(order)

            # 限制为前10个在线订单
            online_orders = online_orders[:10]
            
            # 统计价格分布
            price_counts = {}
            for order in online_orders:
                price = order.get('platinum')
                if price:
                    price_counts[price] = price_counts.get(price, 0) + 1
            
            # 格式化输出
            if not price_counts:
                return "无在线卖家"
            
            # 按价格从低到高排序
            sorted_prices = sorted(price_counts.items())
            
            # 生成格式："1px2，2px5，4px3"
            price_parts = [f"{price}px{count}" for price, count in sorted_prices]
            
            return "，".join(price_parts)
            
        except Exception as e:
            import traceback
            self.log(f"  价格解析时发生意外错误: {traceback.format_exc()}", log_text)
            return f"价格解析失败: {e}"
    
    def show_reference_prices_thread(self):
        """启动参考售价获取的线程"""
        if self.auto_update_running:
            return
        threading.Thread(target=self.show_reference_prices, daemon=True).start()

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
