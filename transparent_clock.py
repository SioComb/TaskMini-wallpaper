import tkinter as tk
import time
import ctypes

# ウィンドウの透明化と最前面化
def make_window_transparent(window):
    hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
    style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
    ctypes.windll.user32.SetWindowLongW(hwnd, -20, style | 0x80000 | 0x20)  # WS_EX_LAYERED | WS_EX_TRANSPARENT
    ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, 0, 255, 0x2)  # 透明度255
    window.attributes("-topmost", True)

# 時計の更新
def update_time():
    current_time = time.strftime("%H:%M:%S")
    label.config(text=current_time)
    label.after(1000, update_time)

root = tk.Tk()
root.overrideredirect(True)  # 枠なし
root.attributes("-topmost", True)
root.attributes("-transparentcolor", "black")  # 背景黒を透明化
root.configure(bg="black")

label = tk.Label(root, font=("Consolas", 40), fg="white", bg="black")
label.pack()

# ウィンドウ位置（右下）
screen_w = root.winfo_screenwidth()
screen_h = root.winfo_screenheight()
root.geometry(f"+{screen_w-200}+{screen_h-100}")

make_window_transparent(root)
update_time()

root.mainloop()
