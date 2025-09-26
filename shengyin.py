import tkinter as tk
from tkinter import messagebox
import subprocess
import threading
import webbrowser
import os
import re
import signal

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Index-TTS 启动器")
        self.root.geometry("450x180")

        self.process = None
        self.is_running = False
        self.project_path = os.path.expanduser("~/index-tts")

        self.status_label = tk.Label(root, text="状态：已停止", font=("Helvetica", 14))
        self.status_label.pack(pady=10)

        self.progress_label = tk.Label(root, text="点击启动按钮开始", font=("Helvetica", 11), fg="gray")
        self.progress_label.pack(pady=2)

        self.url_label = tk.Label(root, text="网址将显示在这里", fg="blue", cursor="hand2", font=("Helvetica", 12))
        self.url_label.pack(pady=5)
        self.url_label.bind("<Button-1>", self.open_url)

        self.toggle_button = tk.Button(root, text="启动服务", command=self.toggle_server, font=("Helvetica", 14), width=15)
        self.toggle_button.pack(pady=10)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def toggle_server(self):
        if self.is_running:
            self.stop_server()
        else:
            self.start_server()

    def start_server(self):
        if not os.path.isdir(self.project_path):
            messagebox.showerror("错误", f"项目路径不存在: {self.project_path}")
            return
            
        self.update_gui_for_starting()
        
        self.server_thread = threading.Thread(target=self._run_server_and_capture_output)
        self.server_thread.daemon = True
        self.server_thread.start()

    def stop_server(self):
        if self.process:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                self.process.wait()
            except ProcessLookupError:
                pass
            except Exception as e:
                # 隐藏这个小报错，因为它不影响功能
                if "Errno 48" in str(e):
                    pass
                else:
                    messagebox.showerror("错误", f"停止服务时出错: {e}")
        
        self.process = None
        self.update_gui_for_stopping()
    
    def _run_server_and_capture_output(self):
        command = f"cd {self.project_path} && source venv_uv/bin/activate && uv run python webui.py"
        
        try:
            self.process = subprocess.Popen(
                ['/bin/bash', '-c', command],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                preexec_fn=os.setsid 
            )

            for line in iter(self.process.stdout.readline, ''):
                clean_line = line.strip()
                # print(clean_line) # 可以取消注释这行来在终端查看实时日志
                
                if "GPT weights restored" in clean_line:
                    self.update_progress_label("✅ 1/5: GPT 模型加载完毕")
                elif "semantic_codec weights restored" in clean_line:
                    self.update_progress_label("✅ 2/5: 语义编解码器加载完毕")
                elif "s2mel weights restored" in clean_line:
                    self.update_progress_label("✅ 3/5: S2Mel 模型加载完毕")
                elif "campplus_model weights restored" in clean_line:
                    self.update_progress_label("✅ 4/5: CAM++ 模型加载完毕")
                elif "bigvgan weights restored" in clean_line:
                    self.update_progress_label("✅ 5/5: 声码器 BigVGAN 加载完毕")
                
                match = re.search(r"Running on local URL:\s+(http://[\d\.:]+)", clean_line)
                if match:
                    url = match.group(1)
                    self.update_progress_label("🚀 服务启动成功！")
                    self.root.after(0, self.update_url_and_open, url)
            
            # ✨ --- 核心修复在这里 --- ✨
            # 在调用 wait() 之前，检查 self.process 是否还存在
            # 如果用户点击了“停止”，self.process 会变成 None，这个检查可以避免程序崩溃
            if self.process:
                self.process.wait()

            # 如果进程是自己结束的（而不是用户点击停止），也需要更新UI
            if self.is_running:
                 self.root.after(0, self.update_gui_for_stopping)

        except Exception as e:
             # 当错误是由用户手动停止服务引起时，没必要弹窗报错
             if self.is_running:
                 self.root.after(0, lambda: messagebox.showerror("错误", f"启动失败: {e}"))
                 self.root.after(0, self.update_gui_for_stopping)
    
    def update_progress_label(self, text):
        self.root.after(0, lambda: self.progress_label.config(text=text))

    def update_url_and_open(self, url):
        self.url_label.config(text=url)
        browser_url = url.replace("0.0.0.0", "127.0.0.1")
        webbrowser.open(browser_url)

    def update_gui_for_starting(self):
        self.is_running = True
        self.status_label.config(text="状态：正在启动...", fg="orange")
        self.toggle_button.config(text="停止服务")
        self.url_label.config(text="等待服务开启...")
        self.progress_label.config(text="▶️ 开始执行启动命令...")

    def update_gui_for_stopping(self):
        self.is_running = False
        self.status_label.config(text="状态：已停止", fg="black")
        self.toggle_button.config(text="启动服务")
        self.url_label.config(text="服务已停止")
        self.progress_label.config(text="点击启动按钮开始")

    def open_url(self, event):
        url = self.url_label.cget("text")
        if url.startswith("http"):
            browser_url = url.replace("0.0.0.0", "127.0.0.1")
            webbrowser.open(browser_url)
            
    def on_closing(self):
        if self.is_running:
            if messagebox.askokcancel("退出", "服务仍在运行中。你确定要退出吗？"):
                self.stop_server()
                self.root.destroy()
        else:
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()