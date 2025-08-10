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
        self.root.title('白金天诺 测试版 1.1')
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
        self.imported_items = set()  # 跟踪通过导入功能添加的行的item_id
        self.display_english = False  # 当前显示语言模式：False=中文，True=英文
        
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
        btn_width = 12  # 按钮字符宽度
        btn_px_width = btn_width * 8  # 估算像素宽度
        btn_spacing = 25  # 按钮间距
        
        # 左边：中/英切换按钮
        self.lang_toggle_btn = tk.Button(self.root, text='中→英', font=(None, 12), width=8, command=self.toggle_language)
        self.lang_toggle_btn.place(x=50, y=540)
        
        # 右边：四个功能按钮 (从右往左排列：删除、显示导入售价、导入、添加)
        # 计算四个按钮的总宽度：4个按钮(96px each) + 3个间距(25px each) = 459px
        # 调整位置确保在1000px宽度窗口内完全显示，右边留50px边距
        delete_btn_x = 950 - btn_px_width  # 950 - 96 = 854，确保删除按钮右边距50px
        show_prices_x = delete_btn_x - btn_px_width - btn_spacing
        import_btn_x = show_prices_x - btn_px_width - btn_spacing
        add_btn_x = import_btn_x - btn_px_width - btn_spacing

        self.add_btn = tk.Button(self.root, text='添加', font=(None, 12), width=btn_width, command=self.add_row)
        self.add_btn.place(x=add_btn_x, y=540)
        
        self.import_btn = tk.Button(self.root, text='导入', font=(None, 12), width=btn_width, command=self.import_items)
        self.import_btn.place(x=import_btn_x, y=540)
        
        self.show_new_prices_btn = tk.Button(self.root, text='显示导入售价', font=(None, 12), width=btn_width, command=self.show_new_items_prices_thread)
        self.show_new_prices_btn.place(x=show_prices_x, y=540)
        
        self.delete_btn = tk.Button(self.root, text='删除', font=(None, 12), width=btn_width, state='disabled', command=self.delete_row)
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
            
            # 优先读取带 max_rank 的新版本CSV，不存在时回退旧版
            csv_file_path_new = os.path.join(base_path, 'wfm_item_names_en_zh_with_max_rank.csv')
            csv_file_path_old = os.path.join(base_path, 'wfm_item_names_en_zh.csv')
            csv_file_path = csv_file_path_new if os.path.exists(csv_file_path_new) else csv_file_path_old
            print(f"尝试从以下路径加载CSV: {csv_file_path}")

            if os.path.exists(csv_file_path):
                with open(csv_file_path, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        chinese_name = row.get('Chinese', '').strip()
                        url_name = row.get('url_name', '').strip()
                        english_name = row.get('English', '').strip()
                        # 兼容不同列名: max_rank
                        raw_max_rank = (row.get('max_rank', '') or '').strip()
                        max_rank_val = None
                        if raw_max_rank != '':
                            try:
                                max_rank_val = int(float(raw_max_rank))
                            except Exception:
                                max_rank_val = None
                        if chinese_name:
                            self.item_names_data[chinese_name] = {
                                'url_name': url_name,
                                'english': english_name,
                                'chinese': chinese_name,
                                'max_rank': max_rank_val
                            }
                print(f"成功加载 {len(self.item_names_data)} 个物品名称")
            else:
                print("错误：在指定路径找不到 wfm_item_names_en_zh_with_max_rank.csv 或 wfm_item_names_en_zh.csv")
                messagebox.showerror("严重错误", "无法找到核心数据文件！\n程序无法运行。")
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
        
        # 只允许编辑特定列（允许编辑等级）
        editable_columns = ['name', 'type', 'price', 'quantity', 'rank']
        if column_name not in editable_columns:
            return
            
        # 获取当前值
        current_values = self.table.item(item, 'values')
        current_value = current_values[column_num - 1]
        
        # 创建编辑窗口
        self.create_edit_dialog(item, column_name, current_value)

    def create_edit_dialog(self, item, column_name, current_value):
        """创建编辑对话框"""
        # 定义列名映射
        column_map = {
            'name': '名称',
            'price': '价格',
            'quantity': '数量',
            'rank': '等级',
            'type': '类型'
        }
        display_name = column_map.get(column_name, column_name.capitalize())
        
        # 如果用户尝试编辑等级，但该行名称未填写或为占位/无效名称，则阻止并提示
        if column_name == 'rank':
            row_values = self.table.item(item, 'values')
            row_name = row_values[0] if row_values else ''
            if not row_name or row_name == '新物品' or not self.validate_item_name(row_name):
                messagebox.showerror("错误", "请先修改名称")
                return

        edit_window = tk.Toplevel(self.root)
        
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
                # 允许为空；不为空时必须为整数，且不能超过该物品在CSV中的 max_rank
                if new_value == '':
                    pass
                else:
                    if not new_value.isdigit():
                        messagebox.showerror("错误", f"{display_name} 必须是整数。")
                        return
                    rank_val = int(new_value)
                    if rank_val < 0:
                        messagebox.showerror("错误", f"{display_name} 不能为负数。")
                        return
                    # 获取该行的物品名称，查对应 max_rank
                    current_values = self.table.item(item, 'values')
                    item_name_in_row = current_values[0]
                    item_info = self.get_item_info(item_name_in_row) if item_name_in_row else None
                    max_rank_allowed = item_info.get('max_rank') if item_info else None
                    if max_rank_allowed is not None and rank_val > max_rank_allowed:
                        messagebox.showerror("错误", f"无效等级：最大等级为 {max_rank_allowed}。")
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
            '1',      # 价格占位
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
                    # 如果是导入的项目，也从导入跟踪中移除
                    self.imported_items.discard(item_id)
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
                # 根据当前显示模式调整名称显示
                if len(current_values) > 0:
                    chinese_name = state_data['current_data']['name']  # 状态数据中保存的是中文名称
                    display_name = self.get_name_display(chinese_name)
                    current_values[0] = display_name  # 更新显示名称
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
            chinese_name = getattr(order.item.zh_hans, 'item_name', order.item.url_name)
            # 根据显示模式决定显示的名称
            display_name = self.get_name_display(chinese_name)
            rank = getattr(order, 'mod_rank', '') if hasattr(order, 'mod_rank') and order.mod_rank is not None else ''
            
            # WFM API的逻辑是，sell_orders里是你想买的，所以是买单；buy_orders里是你想卖的，所以是卖单
            display_type = '买单' if order_type == 'sell' else '卖单'

            item = self.table.insert('', 'end', values=(
                display_name, '', display_type, order.platinum, rank, order.quantity
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
                current_values = list(state_data['current_data'].values())
                # 根据当前显示模式调整名称显示
                if len(current_values) > 0:
                    chinese_name = state_data['current_data']['name']  # 状态数据中保存的是中文名称
                    display_name = self.get_name_display(chinese_name)
                    current_values[0] = display_name  # 更新显示名称
                new_item = self.table.insert('', 'end', values=current_values)
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
            self.import_btn.config(state='disabled')
            self.show_new_prices_btn.config(state='disabled')
            self.delete_btn.config(state='disabled')
            self.lang_toggle_btn.config(state='disabled')
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
            self.import_btn.config(state='normal')
            self.show_new_prices_btn.config(state='normal')
            self.lang_toggle_btn.config(state='normal')
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
                    # 自动更新前也做一次本地合并，避免重复项影响后续流程
                    self.merge_duplicate_rows()
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
                self.imported_items.clear()  # 清空导入项目跟踪

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
                self.imported_items.clear()  # 清空导入项目跟踪

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

            # 在任何服务器交互前，先在本地表格合并完全相同的项目（名称/类型/价格/等级相同），数量相加
            self.merge_duplicate_rows(log_text=log_text)

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
                            # 解析并应用用户编辑的等级（如有），并校验不超过 CSV 的 max_rank
                            rank_param = getattr(target_order, 'mod_rank', None)
                            rank_str = str(current_data.get('rank', '')).strip()
                            if rank_str != '':
                                if rank_str.isdigit():
                                    candidate_rank = int(rank_str)
                                    item_info = self.get_item_info(item_name)
                                    max_rank_allowed = item_info.get('max_rank') if item_info else None
                                    if max_rank_allowed is not None and candidate_rank > max_rank_allowed:
                                        if log_text: self.log(f"  -> 等级无效：最大等级为 {max_rank_allowed}，已跳过此订单的更新。", log_text)
                                        continue
                                    rank_param = candidate_rank
                                else:
                                    if log_text: self.log("  -> 等级无效：必须为整数，已跳过此订单的更新。", log_text)
                                    continue
                            updated_item = wm.orders.OrderNewItem(
                                item_id=target_order.item.id,
                                order_type=target_order.order_type,
                                platinum=int(float(current_data['price'])),
                                quantity=int(float(current_data['quantity'])),
                                rank=rank_param,
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
                        # 解析并校验 rank
                        rank = None
                        r_str = str(current_data.get('rank', '')).strip()
                        if r_str != '':
                            if r_str.isdigit():
                                rank = int(r_str)
                                max_rank_allowed = item_info.get('max_rank')
                                if max_rank_allowed is not None and rank > max_rank_allowed:
                                    raise Exception(f"等级无效：最大等级为 {max_rank_allowed}")
                            else:
                                raise Exception("等级无效：必须为整数")
                        
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

    def merge_duplicate_rows(self, log_text=None):
        """在表格中合并重复行（名称、类型、价格、等级都相同），将数量相加。
        合并策略：
        - 保留首行为主行，更新其数量为总和；
        - 其他重复行：
          * 若为新建行（state == 'new'），直接从UI删除并移除状态；
          * 若为已存在的订单（有 order_id），标记为 'deleted' 并置红，等待后续删除API执行。
        """
        try:
            # 收集所有行，按 (name,type,price,rank) 分组
            groups = {}
            for item in self.table.get_children():
                values = list(self.table.item(item, 'values'))
                if not values or len(values) < 6:
                    continue
                name = str(values[0]).strip()
                order_type = str(values[2]).strip()  # '买单'/'卖单'
                price = str(values[3]).strip()
                rank = str(values[4]).strip()
                qty_str = str(values[5]).strip()
                try:
                    quantity = int(float(qty_str))
                except Exception:
                    quantity = 0

                key = (name, order_type, price, rank)
                groups.setdefault(key, []).append((item, quantity, values))

            # 帮助函数：通过table item查找row_id（不创建新temp id）
            def find_row_id_by_table_item(table_item):
                for rid, s in self.row_states.items():
                    if s.get('table_item') == table_item:
                        return rid
                return None

            # 处理每个有重复的分组
            for key, items in groups.items():
                if len(items) <= 1:
                    continue

                total_qty = sum(q for _, q, _ in items)
                primary_item, _, primary_values = items[0]

                # 更新主行数量
                primary_updated = list(primary_values)
                primary_updated[5] = str(total_qty)
                self.table.item(primary_item, values=primary_updated)

                # 更新主行状态为 modified（若不是new）
                primary_row_id = find_row_id_by_table_item(primary_item)
                if primary_row_id and primary_row_id in self.row_states:
                    st = self.row_states[primary_row_id]
                    columns = ['name', 'ref_price', 'type', 'price', 'rank', 'quantity']
                    st['current_data'] = dict(zip(columns, primary_updated))
                    if st['state'] != 'new':
                        st['state'] = 'modified'
                        self.update_row_color(primary_item, 'modified')

                # 处理重复项（除主行外）
                removed_new_count = 0
                marked_deleted_count = 0
                for dup_item, _, dup_values in items[1:]:
                    dup_row_id = find_row_id_by_table_item(dup_item)
                    if dup_row_id and dup_row_id in self.row_states:
                        st = self.row_states[dup_row_id]
                        if st.get('state') == 'new' and 'order_id' not in st:
                            # 纯新增行：直接移除
                            try:
                                self.table.delete(dup_item)
                            except Exception:
                                pass
                            del self.row_states[dup_row_id]
                            removed_new_count += 1
                        else:
                            # 已存在的订单：标记删除，等待后续删除
                            st['state'] = 'deleted'
                            self.update_row_color(dup_item, 'deleted')
                            marked_deleted_count += 1
                    else:
                        # 没有状态记录，保守起见只从UI移除
                        try:
                            self.table.delete(dup_item)
                            removed_new_count += 1
                        except Exception:
                            pass

                if log_text and (removed_new_count or marked_deleted_count):
                    self.log(
                        f"合并项: {key[0]} | 类型:{key[1]} | 价格:{key[2]} | 等级:{key[3]} -> 数量合计 {total_qty}"
                        f"，移除新增 {removed_new_count} 行，标记删除 {marked_deleted_count} 行",
                        log_text
                    )
        except Exception:
            # 合并失败不应中断更新流程
            import traceback
            if log_text:
                self.log(f"合并重复行时发生错误：\n{traceback.format_exc()}", log_text)

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
                displayed_name = values[0]
                # 读取该行选择的等级
                rank_str = str(values[4]).strip() if len(values) > 4 else ''
                rank_val = None
                if rank_str.isdigit():
                    try:
                        rank_val = int(rank_str)
                    except Exception:
                        rank_val = None
                
                if not displayed_name or displayed_name in ['新物品', '0']:
                    continue
                
                # 如果当前显示英文，需要转换为中文名称进行查询
                chinese_name = self.get_chinese_name_from_display(displayed_name)
                
                if not self.validate_item_name(chinese_name):
                    if log_text: self.log(f"跳过无效物品: {displayed_name}", log_text)
                    continue
                
                try:
                    item_info = self.get_item_info(chinese_name)
                    if not item_info:
                        if log_text: self.log(f"物品 '{chinese_name}' 不在CSV数据中", log_text)
                        continue
                    
                    url_name = item_info['url_name']
                    if log_text: self.log(f"正在获取 {displayed_name} 的价格信息 (官方API)...", log_text)
                    
                    api_url = f"https://api.warframe.market/v1/items/{url_name}/orders"
                    headers = {'Platform': 'pc', 'Language': 'en'}
                    response = requests.get(api_url, headers=headers, timeout=10)
                    response.raise_for_status()
                    
                    orders_data = response.json()
                    price_summary = self.analyze_prices(orders_data, log_text, rank_val)
                    
                    values[1] = price_summary
                    self.table.item(item, values=values)
                    
                    if log_text: self.log(f"  -> {displayed_name}: {price_summary}", log_text)
                    
                except Exception as e:
                    if log_text: self.log(f"获取 {displayed_name} 价格失败: {e}", log_text)
            
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
    
    def analyze_prices(self, orders_data, log_text, rank_val=None):
        """分析价格数据，返回格式化的价格摘要；当 rank_val 不为 None 时，仅统计该等级的订单"""
        try:
            # 官方API返回的是JSON数据
            orders = orders_data.get('payload', {}).get('orders', [])
            
            # 过滤出卖单 (order_type == 'sell')
            sell_orders = [o for o in orders if o.get('order_type') == 'sell']
            # 如指定了 rank，仅保留匹配该等级的订单（mods/arcanes适用）
            if rank_val is not None:
                sell_orders = [o for o in sell_orders if o.get('mod_rank') == rank_val]
            
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

    def import_items(self):
        """导入clicked_items.json文件中的物品"""
        if self.auto_update_running:
            return
            
        try:
            # 查找clicked_items.json文件
            import json
            
            # 确定JSON文件路径（与当前脚本同目录）
            if getattr(sys, 'frozen', False):
                # 如果是打包后的EXE文件
                base_path = os.path.dirname(sys.executable)
            else:
                # 如果是直接运行的.py脚本
                base_path = os.path.dirname(os.path.abspath(__file__))
            
            json_file_path = os.path.join(base_path, 'clicked_items.json')
            
            if not os.path.exists(json_file_path):
                messagebox.showerror("文件未找到", "未找到科学天诺生成的文件")
                return
            
            # 读取JSON文件
            with open(json_file_path, 'r', encoding='utf-8') as f:
                clicked_items = json.load(f)
            
            if not clicked_items:
                messagebox.showinfo("提示", "JSON文件为空")
                return
            
            imported_count = 0
            invalid_items = []
            
            # 遍历JSON中的每个物品
            for item_name, quantity in clicked_items.items():
                # 验证物品名称是否有效
                if not self.validate_item_name(item_name):
                    invalid_items.append(item_name)
                    continue
                
                # 根据显示模式决定显示的名称
                display_name = self.get_name_display(item_name)
                
                # 创建新行
                new_item = self.table.insert('', 'end', values=(
                    display_name,   # 名称（根据显示模式）
                    '',          # 参考售价占位
                    '卖单',       # 类型默认为卖单
                    '1',         # 价格默认为1
                    '',          # 等级占位
                    str(quantity)  # 数量从JSON读取
                ))
                
                # 标记为新行并记录为导入的项目
                temp_id = f"temp_{self.next_temp_id}"
                self.next_temp_id += 1
                
                columns = ['name', 'ref_price', 'type', 'price', 'rank', 'quantity']
                # 在状态数据中保存中文名称，而不是显示名称
                state_values = [item_name, '', '卖单', '1', '', str(quantity)]
                self.row_states[temp_id] = {
                    'state': 'new',
                    'table_item': new_item,
                    'original_data': None,
                    'current_data': dict(zip(columns, state_values))
                }
                
                # 添加到导入项目跟踪集合
                self.imported_items.add(temp_id)
                
                # 设置绿色背景
                self.update_row_color(new_item, 'new')
                imported_count += 1
            
            # 自动滚动到表格最下面
            if imported_count > 0:
                last_item = list(self.table.get_children())[-1]
                self.table.see(last_item)
            
            # 显示导入结果，并尝试清空 JSON 文件
            result_msg = f"成功导入 {imported_count} 个物品"
            if invalid_items:
                result_msg += f"\n无效物品名称（已跳过）: {', '.join(invalid_items)}"

            # 成功导入后清空 clicked_items.json
            clear_ok = False
            if imported_count > 0:
                try:
                    with open(json_file_path, 'w', encoding='utf-8') as f:
                        f.write('{}')
                    clear_ok = True
                except Exception:
                    clear_ok = False

            if clear_ok:
                result_msg += "\n已清空 clicked_items.json"
            else:
                if imported_count > 0:
                    result_msg += "\n未能清空 clicked_items.json，请手动删除或清空该文件"

            messagebox.showinfo("导入完成", result_msg)
            
        except Exception as e:
            messagebox.showerror("导入失败", f"导入过程中发生错误: {e}")

    def show_new_items_prices(self):
        """显示新添加物品的参考售价"""
        try:
            # 检查是否有导入的物品
            if not self.imported_items:
                messagebox.showinfo("提示", "没有通过导入功能添加的物品")
                return
            
            self.set_buttons_state(True)
            log_window, log_text = self.show_log_window("获取新添加物品的参考售价")
            self.log('开始获取新添加物品的参考售价...', log_text)
            
            processed_count = 0
            
            for item_id in self.imported_items:
                if item_id not in self.row_states:
                    continue
                    
                state_data = self.row_states[item_id]
                table_item = state_data.get('table_item')
                
                if not table_item or not self.table.exists(table_item):
                    continue
                
                values = list(self.table.item(table_item, 'values'))
                displayed_name = values[0]
                
                # 读取该行选择的等级
                rank_str = str(values[4]).strip() if len(values) > 4 else ''
                rank_val = None
                if rank_str.isdigit():
                    try:
                        rank_val = int(rank_str)
                    except Exception:
                        rank_val = None
                
                if not displayed_name or displayed_name in ['新物品', '0']:
                    continue
                
                # 转换为中文名称进行查询
                chinese_name = self.get_chinese_name_from_display(displayed_name)
                
                if not self.validate_item_name(chinese_name):
                    self.log(f"跳过无效物品: {displayed_name}", log_text)
                    continue
                
                try:
                    item_info = self.get_item_info(chinese_name)
                    if not item_info:
                        self.log(f"物品 '{chinese_name}' 不在CSV数据中", log_text)
                        continue
                    
                    url_name = item_info['url_name']
                    self.log(f"正在获取 {displayed_name} 的价格信息 (官方API)...", log_text)
                    
                    api_url = f"https://api.warframe.market/v1/items/{url_name}/orders"
                    headers = {'Platform': 'pc', 'Language': 'en'}
                    response = requests.get(api_url, headers=headers, timeout=10)
                    response.raise_for_status()
                    
                    orders_data = response.json()
                    price_summary = self.analyze_prices(orders_data, log_text, rank_val)
                    
                    values[1] = price_summary
                    self.table.item(table_item, values=values)
                    
                    # 更新状态数据（注意：状态数据应该保存中文名称）
                    columns = ['name', 'ref_price', 'type', 'price', 'rank', 'quantity']
                    state_data['current_data'][columns[1]] = price_summary  # 只更新参考售价
                    
                    self.log(f"  -> {displayed_name}: {price_summary}", log_text)
                    processed_count += 1
                    
                except Exception as e:
                    self.log(f"获取 {displayed_name} 价格失败: {e}", log_text)
            
            self.log(f'\n新添加物品的参考售价获取完成！处理了 {processed_count} 个物品', log_text)
            
        except Exception as e:
            if 'log_text' in locals() and log_text.winfo_exists():
                self.log(f"获取新添加物品参考售价失败: {e}", log_text)
        finally:
            self.set_buttons_state(False)

    def show_new_items_prices_thread(self):
        """启动新添加物品参考售价获取的线程"""
        if self.auto_update_running:
            return
        threading.Thread(target=self.show_new_items_prices, daemon=True).start()

    def get_name_display(self, chinese_name):
        """根据当前显示模式返回对应的名称（中文或英文）"""
        if not self.display_english:
            return chinese_name  # 显示中文
        
        # 需要显示英文
        item_info = self.get_item_info(chinese_name)
        if item_info:
            english_name = item_info.get('english', '')
            return english_name if english_name else chinese_name
        return chinese_name

    def get_chinese_name_from_display(self, displayed_name):
        """从显示的名称获取中文名称（用于价格查询等内部处理）"""
        if not self.display_english:
            return displayed_name  # 当前显示中文，直接返回
        
        # 当前显示英文，需要反向查找中文名称
        for chinese_name, info in self.item_names_data.items():
            if info.get('english', '') == displayed_name:
                return chinese_name
        
        # 如果找不到对应的中文名称，返回原名称
        return displayed_name

    def toggle_language(self):
        """切换表格名称列的中英文显示"""
        if self.auto_update_running:
            return
            
        # 切换显示模式
        self.display_english = not self.display_english
        
        # 更新按钮文本提示当前模式
        if self.display_english:
            self.lang_toggle_btn.config(text='英→中')
        else:
            self.lang_toggle_btn.config(text='中→英')
        
        # 更新表格中所有行的名称显示
        for item in self.table.get_children():
            values = list(self.table.item(item, 'values'))
            if values and len(values) > 0:
                current_name = values[0]
                
                if self.display_english:
                    # 切换到英文显示：查找对应的英文名
                    item_info = self.get_item_info(current_name)
                    if item_info:
                        english_name = item_info.get('english', '')
                        if english_name:
                            values[0] = english_name
                else:
                    # 切换到中文显示：通过反向查找恢复中文名
                    chinese_name = None
                    for cn, info in self.item_names_data.items():
                        if info.get('english', '') == current_name:
                            chinese_name = cn
                            break
                    if chinese_name:
                        values[0] = chinese_name
                
                # 更新表格显示
                self.table.item(item, values=values)

if __name__ == '__main__':
    root = tk.Tk()
    app = BaiJinTianNuoApp(root)
    root.mainloop()
