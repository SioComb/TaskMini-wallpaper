# -*- coding: utf-8 -*-

import sys, math, datetime, collections
import psutil, jpholiday

from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, QDate
from PyQt6.QtGui  import QColor, QPainter, QPen, QFont, QTextCharFormat
from PyQt6.QtWidgets import QApplication, QWidget, QGridLayout, QLabel, QCalendarWidget

# 壁紙レイヤー固定
import win32gui, win32con
# GPU用：Windows パフォーマンスカウンタ
import win32pdh


# ───────────── WorkerW 検出（壁紙の子にする） ─────────────
def get_workerw():
    progman = win32gui.FindWindow("Progman", None)
    try:
        win32gui.SendMessageTimeout(progman, 0x052C, 0, 0, win32con.SMTO_NORMAL, 1000)
    except win32gui.error:
        pass
    result = []
    def enum_windows(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetClassName(hwnd) == "WorkerW":
            has_shell = []
            def enum_child(ch, __):
                if win32gui.GetClassName(ch) == "SHELLDLL_DefView":
                    has_shell.append(True)
                return True
            win32gui.EnumChildWindows(hwnd, enum_child, None)
            if not has_shell:
                result.append(hwnd)
        return True
    win32gui.EnumWindows(enum_windows, None)
    return result[0] if result else None


# ───────────── 軽量スパークライン ─────────────
class SparkGraph(QWidget):
    def __init__(self, max_points=300, y_max=100.0, y_label="%", grid=True, parent=None):
        super().__init__(parent)
        self.max_points = max_points
        self.y_max = y_max
        self.y_label = y_label
        self.grid = grid
        self.data = collections.deque([0.0]*max_points, maxlen=max_points)
        self.setMinimumHeight(180)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def push(self, v: float):
        self.data.append(float(max(0.0, v)))

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(self.rect(), QColor(14, 24, 38, 100))
        if self.grid:
            p.setPen(QPen(QColor(120,140,170,40), 1))
            for i in range(6):  p.drawLine(0, int(h*i/5), w, int(h*i/5))
            for i in range(12): p.drawLine(int(w*i/11), 0, int(w*i/11), h)
        p.setPen(QPen(QColor(96,165,250), 2))
        pts=[]; n=len(self.data)
        for i,val in enumerate(self.data):
            x = 0 if n<=1 else int(i*(w-1)/(n-1))
            y = h - int(min(val,self.y_max)/self.y_max*(h-4)) - 2
            pts.append(QPointF(x,y))
        if len(pts)>=2: p.drawPolyline(*pts)
        p.setPen(QPen(QColor(59,130,246,120),1)); p.drawLine(0,h-1,w,h-1)
        p.setPen(QColor(170,190,210,160)); p.setFont(QFont("Consolas",10))
        p.drawText(w-60, 18, f"{self.y_label}"); p.end()


# ───────────── パネル ─────────────
class Panel(QWidget):
    def __init__(self, title, subtitle="", show_border=True, parent=None):
        super().__init__(parent)
        self.title=title; self.subtitle=subtitle; self.show_border=show_border
        self.value_text=""; self.extra_text=""; self.graph:SparkGraph|None=None
        self.setMinimumSize(460,260)

    def set_graph(self, g:SparkGraph): self.graph=g; g.setParent(self)
    def set_value(self, t): self.value_text=t; self.update()
    def set_extra(self, t): self.extra_text=t; self.update()
    def set_subtitle(self, t): self.subtitle=t; self.update()

    def paintEvent(self, _):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r=self.rect().adjusted(1,1,-1,-1)
        p.setBrush(QColor(20,28,44,180)); p.setPen(Qt.PenStyle.NoPen); p.drawRoundedRect(r,14,14)
        if self.show_border:
            p.setPen(QPen(QColor(66,93,120,130),2)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(r,14,14)
        p.setPen(QColor(203,213,225)); p.setFont(QFont("Inter,Segoe UI,Meiryo UI,Arial",12,QFont.Weight.DemiBold))
        p.drawText(r.adjusted(16,12,-16,-16), Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop, self.title)
        if self.subtitle:
            p.setPen(QColor(148,163,184)); p.setFont(QFont("Consolas",10))
            p.drawText(r.adjusted(120,12,-16,-16), Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop, self.subtitle)
        if self.value_text:
            p.setPen(QColor(241,245,249)); p.setFont(QFont("Inter,Segoe UI,Meiryo UI",26,QFont.Weight.Bold))
            p.drawText(r.adjusted(0,8,-16,0), Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTop, self.value_text)
        if self.graph:
            g_rect = r.adjusted(16,56,-16,-56); self.graph.setGeometry(g_rect)
        if self.extra_text:
            p.setPen(QColor(148,163,184)); p.setFont(QFont("Consolas",11))
            p.drawText(r.adjusted(16,0,-16,-10), Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignBottom, self.extra_text)
        p.end()


# ───────────── カレンダー（濃い色） ─────────────
class CustomCalendar(QCalendarWidget):
    def __init__(self):
        super().__init__()
        self.setFirstDayOfWeek(Qt.DayOfWeek.Sunday)
        self.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.setNavigationBarVisible(True)
        self.setGridVisible(False)
        self.setStyleSheet("background-color: rgba(0,0,0,70); color: white; border-radius: 10px;")
        self.update_calendar_colors()

    def update_calendar_colors(self):
        default_fmt = QTextCharFormat()
        for d in (Qt.DayOfWeek.Monday, Qt.DayOfWeek.Tuesday, Qt.DayOfWeek.Wednesday,
                  Qt.DayOfWeek.Thursday, Qt.DayOfWeek.Friday):
            self.setWeekdayTextFormat(d, default_fmt)

        sat = QTextCharFormat(); sat.setForeground(QColor("#00B7FF"))  # 土
        sun = QTextCharFormat(); sun.setForeground(QColor("#FF40FF"))  # 日
        self.setWeekdayTextFormat(Qt.DayOfWeek.Saturday, sat)
        self.setWeekdayTextFormat(Qt.DayOfWeek.Sunday,   sun)

        hol = QTextCharFormat(); hol.setForeground(QColor("#4DE36B"))  # 祝
        today = datetime.date.today()
        y, m = today.year, today.month
        first = datetime.date(y, m, 1)
        last  = (first.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)
        for d in range(1, last.day+1):
            self.setDateTextFormat(QDate(y, m, d), QTextCharFormat())
        for d in range(1, last.day+1):
            day = datetime.date(y, m, d)
            if jpholiday.is_holiday(day):
                self.setDateTextFormat(QDate(y, m, d), hol)


# ───────────── アナログ時計 ─────────────
class AnalogClock(QWidget):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setMinimumSize(220,220)

    def paintEvent(self, _):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r=self.rect(); cx=r.center().x(); cy=r.center().y()
        radius=min(r.width(), r.height())//2 - 6
        p.setPen(QPen(QColor(255,180,140,180), 3))
        p.setBrush(QColor(255,255,255,10))
        p.drawEllipse(QPointF(cx,cy), radius, radius)
        now=datetime.datetime.now()
        def draw(angle_deg, length, thick):
            rad=math.radians(angle_deg-90)
            x=cx+length*math.cos(rad); y=cy+length*math.sin(rad)
            p.setPen(QPen(QColor(255,220,200,220), thick)); p.drawLine(cx,cy,int(x),int(y))
        sec=now.second + now.microsecond/1e6
        minv=now.minute + sec/60.0
        hour=(now.hour%12) + minv/60.0
        draw(hour*30,   radius*0.55, 5)
        draw(minv*6,    radius*0.75, 3)
        draw(sec*6,     radius*0.85, 1)
        p.end()


# ───────────── GPU モニタ（Windows PDH） ─────────────
class GPUMonitor:
    r"""
    GPU Engine\Utilization Percentage  … 使用率(%)を合算
    GPU Adapter Memory\Dedicated Usage … VRAM使用量(バイト)を合算
    """
    def __init__(self):
        self.query = win32pdh.OpenQuery()
        self.engine_counters = []
        self.mem_counters_usage = []
        self.mem_counters_limit = []

        try:
            # GPU Engine
            instances, _ = win32pdh.EnumObjectItems(None, None, "GPU Engine", win32pdh.PERF_DETAIL_WIZARD)
            for inst in instances:
                # (machine, object, instance, parentInstance, index, counter)
                path = win32pdh.MakeCounterPath((None, "GPU Engine", inst, None, 0, "Utilization Percentage"))
                c = win32pdh.AddCounter(self.query, path)
                self.engine_counters.append(c)

            # GPU Adapter Memory
            mem_instances, _ = win32pdh.EnumObjectItems(None, None, "GPU Adapter Memory", win32pdh.PERF_DETAIL_WIZARD)
            for inst in mem_instances:
                # Dedicated Usage
                path_u = win32pdh.MakeCounterPath((None, "GPU Adapter Memory", inst, None, 0, "Dedicated Usage"))
                self.mem_counters_usage.append(win32pdh.AddCounter(self.query, path_u))
                # Dedicated Limit（存在しない環境もあるので try/except）
                try:
                    path_l = win32pdh.MakeCounterPath((None, "GPU Adapter Memory", inst, None, 0, "Dedicated Limit"))
                    self.mem_counters_limit.append(win32pdh.AddCounter(self.query, path_l))
                except win32pdh.error:
                    pass


            # 初回収集
            win32pdh.CollectQueryData(self.query)
        except win32pdh.error:
            # 使えない環境では空のまま
            pass

    def read(self):
        try:
            win32pdh.CollectQueryData(self.query)
        except win32pdh.error:
            return None

        def val_of(c):
            try:
                _t, v = win32pdh.GetFormattedCounterValue(c, win32pdh.PDH_FMT_DOUBLE)
                return max(0.0, float(v))
            except win32pdh.error:
                return 0.0

        util = sum(val_of(c) for c in self.engine_counters)
        used_bytes = sum(val_of(c) for c in self.mem_counters_usage)
        total_bytes = sum(val_of(c) for c in self.mem_counters_limit) if self.mem_counters_limit else 0.0

        return {"util": util, "vram_used": used_bytes, "vram_total": total_bytes}


# ───────────── ダッシュボード ─────────────
class Dashboard(QWidget):
    def __init__(self):
        super().__init__()
        # 透明・枠なし
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # クリック透過（背面のボタンを押せる） … F10 で切替
        self.click_through = True
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        # レイアウト
        grid = QGridLayout(self)
        grid.setContentsMargins(40,40,40,40)
        grid.setHorizontalSpacing(36); grid.setVerticalSpacing(36)

        # パネルとグラフ
        self.cpu_graph = SparkGraph(y_max=100.0, y_label="%")
        self.ram_graph = SparkGraph(y_max=100.0, y_label="%")
        self.gpu_graph = SparkGraph(y_max=100.0, y_label="%")
        self.net_graph = SparkGraph(y_max=1024.0, y_label="KB/s")

        self.cpu_panel = Panel("CPU", subtitle=self._cpu_name()); self.cpu_panel.set_graph(self.cpu_graph)
        self.ram_panel = Panel("RAM", subtitle=self._ram_total()); self.ram_panel.set_graph(self.ram_graph)
        self.gpu_panel = Panel("GPU", subtitle=self._gpu_name()); self.gpu_panel.set_graph(self.gpu_graph)
        self.net_panel = Panel("Wi‑Fi", subtitle=self._net_iface()); self.net_panel.set_graph(self.net_graph)

        # 中央：上=カレンダー、下=時計（アナログ＋テキスト）
        cal_wrap = Panel("Calendar", show_border=False)
        self.calendar = CustomCalendar(); self.calendar.setParent(cal_wrap)
        cal_wrap.resizeEvent = lambda e, w=cal_wrap: self._place_calendar(w)

        self.clock_panel = Panel("", show_border=False)
        self.analog = AnalogClock(); self.analog.setParent(self.clock_panel)
        self.clock_label = QLabel("", self.clock_panel)
        self.clock_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.clock_label.setStyleSheet("color:#e5e7eb;")
        self.clock_label.setFont(QFont("Consolas", 22, QFont.Weight.DemiBold))
        self.clock_panel.resizeEvent = lambda e, w=self.clock_panel: self._place_clock(w)

        # 配置
        grid.addWidget(self.cpu_panel,   0, 0)
        grid.addWidget(cal_wrap,         0, 1)
        grid.addWidget(self.ram_panel,   0, 2)
        grid.addWidget(self.gpu_panel,   1, 0)
        grid.addWidget(self.clock_panel, 1, 1)
        grid.addWidget(self.net_panel,   1, 2)

        # 計測
        self.last_net = psutil.net_io_counters()
        self.gpu = GPUMonitor()

        # 1秒更新
        self.timer = QTimer(self); self.timer.timeout.connect(self.update_all); self.timer.start(1000)

        # 全画面
        self.to_fullscreen()

        # 壁紙レイヤーへ
        QTimer.singleShot(0, self.attach_to_wallpaper)

    # 画面操作
    def to_fullscreen(self):
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(0,0,screen.width(),screen.height()); self.show()

    def keyPressEvent(self, e):
        if e.key()==Qt.Key.Key_Escape:
            QApplication.quit()
        elif e.key()==Qt.Key.Key_F11:
            if self.isFullScreen(): self.showNormal(); self.resize(1460,820); self.move(120,120)
            else: self.to_fullscreen()
        elif e.key()==Qt.Key.Key_F10:
            self.click_through = not self.click_through
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, self.click_through)

    def _place_calendar(self, panel: Panel):
        r = panel.rect().adjusted(8,8,-8,-8)
        self.calendar.setGeometry(r.left(), r.top(), r.width(), int(r.height()*0.60))

    def _place_clock(self, panel: Panel):
        r = panel.rect().adjusted(8,8,-8,-8)
        size = min(r.width(), r.height())//2 + 20
        cx = r.center().x() - size//2
        self.analog.setGeometry(cx, r.top()+30, size, size)
        now = datetime.datetime.now()
        self.clock_label.setText(f"{now:%H:%M:%S}\n{now:%Y-%m-%d %A}")
        self.clock_label.setGeometry(r.left(), r.bottom()-120, r.width(), 110)

    # 情報
    def _cpu_name(self):
        try:
            return next((l for l in psutil.cpu_info().__dict__.values() if isinstance(l,str)), "CPU")
        except Exception:
            return "AMD Ryzen / Intel Core"
    def _ram_total(self):
        vm=psutil.virtual_memory(); return f"Total {vm.total/(1024**3):.1f} GB"
    def _gpu_name(self):  return "GPU"
    def _net_iface(self): return "Realtek / Wi‑Fi"

    # 壁紙の子に
    def attach_to_wallpaper(self):
        hwnd = int(self.winId()); workerw = get_workerw()
        if workerw:
            try: win32gui.SetParent(hwnd, workerw)
            except win32gui.error: pass
        win32gui.SetWindowPos(hwnd, win32con.HWND_BOTTOM, 0,0,0,0,
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE |
                              win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW)

    # 1秒更新
    def update_all(self):
        # CPU
        cpu=psutil.cpu_percent(); self.cpu_panel.set_value(f"{cpu:.0f}%"); self.cpu_graph.push(cpu)
        # RAM
        vm=psutil.virtual_memory()
        self.ram_panel.set_value(f"{vm.percent:.0f}%")
        used=(vm.total-vm.available)/(1024**3); free=vm.available/(1024**3)
        self.ram_panel.set_subtitle(f"Total {vm.total/(1024**3):.1f} GB")
        self.ram_panel.set_extra(f"Used: {used:.1f} GB  /  Free: {free:.1f} GB")
        self.ram_graph.push(vm.percent)
        # GPU
        gpu = self.gpu.read() if self.gpu else None
        if gpu:
            util = gpu["util"]
            used_b = gpu["vram_used"]; total_b = gpu["vram_total"]
            self.gpu_panel.set_value(f"{util:.0f}%")
            if used_b>0:
                used_gb = used_b/(1024**3)
                if total_b>0:
                    total_gb = total_b/(1024**3)
                    self.gpu_panel.set_extra(f"VRAM Used: {used_gb:.2f} / {total_gb:.2f} GB")
                else:
                    self.gpu_panel.set_extra(f"VRAM Used: {used_gb:.2f} GB")
            else:
                self.gpu_panel.set_extra("VRAM Used: --")
            self.gpu_graph.push(min(util,100.0))
        else:
            self.gpu_panel.set_value("--%"); self.gpu_panel.set_extra("VRAM Used: --"); self.gpu_graph.push(0.0)
        # ネット（下り）
        now = psutil.net_io_counters()
        up_kb=(now.bytes_sent - self.last_net.bytes_sent)/1024.0
        dn_kb=(now.bytes_recv - self.last_net.bytes_recv)/1024.0
        self.last_net = now
        self.net_panel.set_value(f"{dn_kb/1024.0:.2f} Mb/s" if dn_kb>1024 else f"{dn_kb:.0f} KB/s")
        self.net_panel.set_extra(f"↑ {up_kb:.1f} KB/s")
        self.net_graph.push(dn_kb)
        # 時計/カレンダー
        self._place_clock(self.clock_panel)
        self.calendar.update_calendar_colors()

    def paintEvent(self, _):
        p=QPainter(self)
        p.fillRect(self.rect(), QColor(9,15,26,235))
        p.setBrush(QColor(0,0,0,80)); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(-self.width()*0.25, -self.height()*0.25,
                             self.width()*1.5, self.height()*1.5))
        p.end()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Dashboard()
    w.show()
    sys.exit(app.exec())
