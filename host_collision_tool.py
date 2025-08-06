import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
import csv
import json
import time
from urllib.parse import urlparse
import os
from concurrent.futures import ThreadPoolExecutor
import queue

class CollisionResult:
    def __init__(self, url, domain, ip, port, title, status_code, content_length):
        self.url = url
        self.domain = domain
        self.ip = ip
        self.port = port
        self.title = title
        self.status_code = status_code
        self.content_length = content_length

class HostCollisionTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Host碰撞工具 v1.0")
        self.root.geometry("1200x800")
        
        # 数据存储
        self.ip_list = []
        self.main_domain_list = []
        self.domain_prefix_list = []
        self.subdomain_list = []
        self.results = []
        self.is_running = False
        self.completed = 0
        self.total = 0
        
        # 创建GUI
        self.create_ui()
        
    def create_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 输入区域
        input_frame = ttk.LabelFrame(main_frame, text="配置参数", padding="5")
        input_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 第一行：IP列表和主域名列表并排
        # IP列表
        ttk.Label(input_frame, text="IP列表 (每行一个):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.ip_text = scrolledtext.ScrolledText(input_frame, height=4, width=40)
        self.ip_text.grid(row=0, column=1, padx=(5, 10), pady=2)
        ttk.Button(input_frame, text="导入IP", command=lambda: self.import_file("ip")).grid(row=0, column=2, padx=(5, 0), pady=2)
        
        # 主域名列表
        ttk.Label(input_frame, text="主域名列表 (每行一个):").grid(row=0, column=3, sticky=tk.W, padx=(20, 0), pady=2)
        self.domain_text = scrolledtext.ScrolledText(input_frame, height=4, width=40)
        self.domain_text.grid(row=0, column=4, padx=(5, 0), pady=2)
        ttk.Button(input_frame, text="导入域名", command=lambda: self.import_file("domain")).grid(row=0, column=5, padx=(5, 0), pady=2)
        
        # 第二行：域名前缀和子域名列表并排
        # 域名前缀
        ttk.Label(input_frame, text="域名前缀 (每行一个):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.prefix_text = scrolledtext.ScrolledText(input_frame, height=4, width=40)
        self.prefix_text.grid(row=1, column=1, padx=(5, 10), pady=2)
        ttk.Button(input_frame, text="导入前缀", command=lambda: self.import_file("prefix")).grid(row=1, column=2, padx=(5, 0), pady=2)
        
        # 子域名列表
        ttk.Label(input_frame, text="子域名列表 (每行一个):").grid(row=1, column=3, sticky=tk.W, padx=(20, 0), pady=2)
        self.subdomain_text = scrolledtext.ScrolledText(input_frame, height=4, width=40)
        self.subdomain_text.grid(row=1, column=4, padx=(5, 0), pady=2)
        ttk.Button(input_frame, text="导入子域名", command=lambda: self.import_file("subdomain")).grid(row=1, column=5, padx=(5, 0), pady=2)
        
        # 参数设置
        param_frame = ttk.Frame(input_frame)
        param_frame.grid(row=2, column=0, columnspan=6, sticky=(tk.W, tk.E), pady=(10, 0))
        
        ttk.Label(param_frame, text="线程数:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.thread_count = tk.StringVar(value="50")
        ttk.Entry(param_frame, textvariable=self.thread_count, width=10).grid(row=0, column=1, padx=(0, 20))
        
        ttk.Label(param_frame, text="端口 (逗号分隔):").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.port_list = tk.StringVar(value="80,443")
        ttk.Entry(param_frame, textvariable=self.port_list, width=20).grid(row=0, column=3, padx=(0, 20))
        
        # 控制按钮放在右边
        self.start_button = ttk.Button(param_frame, text="开始碰撞", command=self.start_collision)
        self.start_button.grid(row=0, column=4, padx=(20, 5))
        
        self.stop_button = ttk.Button(param_frame, text="停止碰撞", command=self.stop_collision, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=5, padx=(0, 5))
        
        self.clear_button = ttk.Button(param_frame, text="清空结果", command=self.clear_results)
        self.clear_button.grid(row=0, column=6, padx=(0, 5))
        
        self.export_button = ttk.Button(param_frame, text="导出结果", command=self.export_results)
        self.export_button.grid(row=0, column=7, padx=(0, 0))
        

        
        # 状态和进度
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.status_label = ttk.Label(status_frame, text="状态: 就绪")
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        
        self.stats_label = ttk.Label(status_frame, text="结果数: 0")
        self.stats_label.grid(row=0, column=1, padx=(20, 0))
        
        self.progress = ttk.Progressbar(status_frame, mode='determinate')
        self.progress.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        # 配置状态框架的列权重，让进度条占满整行
        status_frame.columnconfigure(0, weight=1)
        
        # 结果显示
        result_frame = ttk.LabelFrame(main_frame, text="碰撞结果", padding="5")
        result_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # 创建Treeview显示结果
        columns = ('URL', '域名', 'IP', '端口', '标题', '状态码', '内容长度')
        self.result_tree = ttk.Treeview(result_frame, columns=columns, show='headings', height=6)
        
        # 设置列标题
        for col in columns:
            self.result_tree.heading(col, text=col)
            # 根据内容调整列宽
            if col in ['端口', '状态码', '内容长度']:
                self.result_tree.column(col, width=40)  # 进一步缩小端口、状态码、内容长度列宽
            elif col == 'URL':
                self.result_tree.column(col, width=200)  # URL列稍宽一些
            elif col == '标题':
                self.result_tree.column(col, width=180)  # 标题列稍宽一些
            else:
                self.result_tree.column(col, width=120)  # 其他列适中宽度
        
        # 添加滚动条
        result_scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=result_scrollbar.set)
        
        self.result_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        result_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 绑定右键菜单事件
        self.result_tree.bind("<Button-3>", self.show_context_menu)
        self.result_tree.bind("<Double-1>", self.on_double_click)
        
        # 创建右键菜单
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="复制URL", command=self.copy_url)
        self.context_menu.add_command(label="复制域名", command=self.copy_domain)
        self.context_menu.add_command(label="复制IP", command=self.copy_ip)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="复制所有信息", command=self.copy_all_info)
    
    def import_file(self, file_type):
        filename = filedialog.askopenfilename(
            title=f"选择{file_type}文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                
                if file_type == "ip":
                    self.ip_text.delete(1.0, tk.END)
                    self.ip_text.insert(1.0, content)
                elif file_type == "domain":
                    self.domain_text.delete(1.0, tk.END)
                    self.domain_text.insert(1.0, content)
                elif file_type == "prefix":
                    self.prefix_text.delete(1.0, tk.END)
                    self.prefix_text.insert(1.0, content)
                elif file_type == "subdomain":
                    self.subdomain_text.delete(1.0, tk.END)
                    self.subdomain_text.insert(1.0, content)
                    
                messagebox.showinfo("成功", f"成功导入{file_type}文件")
            except Exception as e:
                messagebox.showerror("错误", f"导入文件失败: {str(e)}")
    
    def export_results(self):
        if not self.results:
            messagebox.showwarning("警告", "没有结果可导出")
            return
            
        filename = filedialog.asksaveasfilename(
            title="保存结果",
            defaultextension=".csv",
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(['URL', '域名', 'IP', '端口', '标题', '状态码', '内容长度'])
                    for result in self.results:
                        writer.writerow([
                            result.url, result.domain, result.ip, result.port,
                            result.title, result.status_code, result.content_length
                        ])
                messagebox.showinfo("成功", f"结果已导出到: {filename}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {str(e)}")
    
    def clear_results(self):
        self.results.clear()
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        self.stats_label.config(text="结果数: 0")
    
    def start_collision(self):
        if self.is_running:
            return
            
        # 获取输入数据
        self.ip_list = [ip.strip() for ip in self.ip_text.get(1.0, tk.END).strip().split('\n') if ip.strip()]
        self.main_domain_list = [domain.strip() for domain in self.domain_text.get(1.0, tk.END).strip().split('\n') if domain.strip()]
        self.domain_prefix_list = [prefix.strip() for prefix in self.prefix_text.get(1.0, tk.END).strip().split('\n') if prefix.strip()]
        self.subdomain_list = [subdomain.strip() for subdomain in self.subdomain_text.get(1.0, tk.END).strip().split('\n') if subdomain.strip()]
        
        if not self.ip_list:
            messagebox.showwarning("警告", "请输入IP列表")
            return
            
        if not self.main_domain_list and not self.subdomain_list:
            messagebox.showwarning("警告", "请输入主域名列表或子域名列表")
            return
        
        # 验证参数
        try:
            thread_count = int(self.thread_count.get())
            if thread_count < 1 or thread_count > 1000:
                raise ValueError("线程数必须在1-1000之间")
        except ValueError as e:
            messagebox.showerror("错误", f"线程数设置错误: {str(e)}")
            return
            
        try:
            ports = [int(p.strip()) for p in self.port_list.get().split(',') if p.strip()]
            for port in ports:
                if port < 1 or port > 65535:
                    raise ValueError("端口必须在1-65535之间")
        except ValueError as e:
            messagebox.showerror("错误", f"端口设置错误: {str(e)}")
            return
        
        # 生成目标列表
        targets = self.generate_targets()
        if not targets:
            messagebox.showwarning("警告", "没有生成任何目标")
            return
        
        self.total = len(targets)
        self.completed = 0
        self.progress['maximum'] = self.total
        self.progress['value'] = 0
        self.status_label.config(text=f"状态: 开始碰撞，共{self.total}个目标")
        
        # 启动碰撞线程
        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        collision_thread = threading.Thread(target=self.run_collision, args=(targets, thread_count, ports))
        collision_thread.daemon = True
        collision_thread.start()
    
    def stop_collision(self):
        self.is_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_label.config(text="状态: 已停止")
    
    def generate_targets(self):
        targets = []
        
        # 获取用户设置的端口列表
        try:
            ports = [int(p.strip()) for p in self.port_list.get().split(',') if p.strip()]
        except ValueError:
            ports = [80, 443]  # 默认端口
        
        # 从子域名列表生成目标
        for subdomain in self.subdomain_list:
            for ip in self.ip_list:
                for port in ports:
                    targets.append((subdomain, ip, port))
        
        # 从主域名和前缀生成目标
        for main_domain in self.main_domain_list:
            for prefix in self.domain_prefix_list:
                subdomain = f"{prefix}.{main_domain}"
                for ip in self.ip_list:
                    for port in ports:
                        targets.append((subdomain, ip, port))
        
        return targets
    
    def run_collision(self, targets, thread_count, ports):
        # 使用线程池执行碰撞检测
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = []
            for target in targets:
                if not self.is_running:
                    break
                future = executor.submit(self.check_target, target[0], target[1], target[2])
                futures.append(future)
            
            # 等待所有任务完成
            for future in futures:
                if not self.is_running:
                    break
                try:
                    result = future.result(timeout=30)
                    if result:
                        self.results.append(result)
                        # 在主线程中更新UI
                        self.root.after(0, self.update_result_display, result)
                except Exception as e:
                    print(f"检查目标时出错: {e}")
        
        # 碰撞完成
        self.root.after(0, self.collision_finished)
    
    def check_target(self, domain, ip, port):
        # 定义协议尝试顺序
        protocols_to_try = []
        
        # 根据端口确定协议尝试顺序
        if port == 443:
            protocols_to_try = ['https']  # 443端口只探测HTTPS
        elif port == 80:
            protocols_to_try = ['http']   # 80端口只探测HTTP
        else:
            # 对于其他端口，尝试两种协议
            protocols_to_try = ['http', 'https']
        
        for protocol in protocols_to_try:
            try:
                # 构建URL
                url = f"{protocol}://{domain}:{port}"
                
                # 设置请求头
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Host': domain
                }
                
                # 发送请求
                response = requests.get(url, headers=headers, timeout=10, allow_redirects=False)
                
                # 提取标题
                title = ""
                content_length = len(response.content)
                
                if response.status_code == 200 and 'text/html' in response.headers.get('content-type', ''):
                    try:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        title_tag = soup.find('title')
                        if title_tag:
                            title = title_tag.get_text().strip()
                    except:
                        pass
                
                # 创建结果对象
                result = CollisionResult(
                    url=url,
                    domain=domain,
                    ip=ip,
                    port=port,
                    title=title,
                    status_code=response.status_code,
                    content_length=content_length
                )
                
                return result
                
            except requests.exceptions.RequestException:
                # 请求失败，继续尝试下一个协议
                continue
            except Exception as e:
                print(f"检查目标 {domain}:{port} ({protocol}) 时出错: {e}")
                continue
        
        # 所有协议都失败，返回None
        return None
    
    def update_result_display(self, result):
        # 更新进度
        self.completed += 1
        self.progress['value'] = self.completed
        self.stats_label.config(text=f"结果数: {len(self.results)}")
        
        # 添加到结果列表
        self.result_tree.insert('', 'end', values=(
            result.url, result.domain, result.ip, result.port,
            result.title, result.status_code, result.content_length
        ))
        
        # 自动滚动到底部
        self.result_tree.see(self.result_tree.get_children()[-1])
    
    def collision_finished(self):
        self.is_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_label.config(text=f"状态: 碰撞完成，共检查{self.completed}个目标，发现{len(self.results)}个结果")

    def show_context_menu(self, event):
        try:
            # 获取当前选中的项
            selected_item = self.result_tree.selection()
            if not selected_item:
                return

            # 获取选中的项的值
            item_values = self.result_tree.item(selected_item[0])['values']
            url = item_values[0]

            # 设置菜单位置
            self.context_menu.post(event.x_root, event.y_root)
        except Exception as e:
            print(f"显示右键菜单失败: {e}")

    def on_double_click(self, event):
        try:
            # 获取当前选中的项
            selected_item = self.result_tree.selection()
            if not selected_item:
                return

            # 获取选中的项的值
            item_values = self.result_tree.item(selected_item[0])['values']
            url = item_values[0]

            # 打开URL
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self.root.update() # 确保剪贴板内容更新
            messagebox.showinfo("提示", f"已复制URL: {url}")
        except Exception as e:
            print(f"双击事件失败: {e}")

    def copy_url(self):
        try:
            selected_item = self.result_tree.selection()
            if not selected_item:
                return
            item_values = self.result_tree.item(selected_item[0])['values']
            url = item_values[0]
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self.root.update()
            messagebox.showinfo("提示", f"已复制URL: {url}")
        except Exception as e:
            print(f"复制URL失败: {e}")

    def copy_domain(self):
        try:
            selected_item = self.result_tree.selection()
            if not selected_item:
                return
            item_values = self.result_tree.item(selected_item[0])['values']
            domain = item_values[1]
            self.root.clipboard_clear()
            self.root.clipboard_append(domain)
            self.root.update()
            messagebox.showinfo("提示", f"已复制域名: {domain}")
        except Exception as e:
            print(f"复制域名失败: {e}")

    def copy_ip(self):
        try:
            selected_item = self.result_tree.selection()
            if not selected_item:
                return
            item_values = self.result_tree.item(selected_item[0])['values']
            ip = item_values[2]
            self.root.clipboard_clear()
            self.root.clipboard_append(ip)
            self.root.update()
            messagebox.showinfo("提示", f"已复制IP: {ip}")
        except Exception as e:
            print(f"复制IP失败: {e}")

    def copy_all_info(self):
        try:
            selected_item = self.result_tree.selection()
            if not selected_item:
                return
            item_values = self.result_tree.item(selected_item[0])['values']
            url = item_values[0]
            domain = item_values[1]
            ip = item_values[2]
            port = item_values[3]
            title = item_values[4]
            status_code = item_values[5]
            content_length = item_values[6]

            all_info = f"URL: {url}\n域名: {domain}\nIP: {ip}\n端口: {port}\n标题: {title}\n状态码: {status_code}\n内容长度: {content_length}"
            self.root.clipboard_clear()
            self.root.clipboard_append(all_info)
            self.root.update()
            messagebox.showinfo("提示", "已复制所有信息")
        except Exception as e:
            print(f"复制所有信息失败: {e}")

def main():
    root = tk.Tk()
    app = HostCollisionTool(root)
    root.mainloop()

if __name__ == "__main__":
    main() 