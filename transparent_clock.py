# taskmini_widget.py

import sys
import datetime
import psutil
import jpholiday

from PyQt6.QtWidgets import QApplication, QWidget, QGridLayout, QLabel, QCalendarWidget
from PyQt6.QtCore import Qt, QTimer, QDate
from PyQt6.QtGui import QColor, QTextCharFormat, QFont

# Win32
import win32gui
import win32con
import win32api

# ───────────────────────────
# WorkerW の取得（壁紙の背面に固定するための親ウィンドウ）
# 参考: Progman に 0x052C を投げて WorkerW を起動 → SHELLDLL_DefView を持たない WorkerW を探す
# ───────────────────────────
def get_workerw():
    progman = win32gui.FindWindow("Progman", None)
    # 0x052C: 指定メッセージで WorkerW 生成をトリガ
    try:
        win32gui.SendMessageTimeout(
            progman, 0x052C, 0, 0, win32con.SMTO_NORMAL, 1000
        )
    except win32gui.error:
        pass

    workerw_list = []

    def enum_windows(hwnd, lparam):
        # SHELLDLL_DefView を子にもつのはアイコンを表示してる WorkerW ではないケースがあるため
        # ここでは SHELLDLL_DefView を持たない WorkerW を親候補にする
        if win32gui.IsWindowVisible(hwnd):
            cname = win32gui.GetClassName(hwnd)
            if cname == "WorkerW":
                # 子に SHELLDLL_DefView がいるかチェック
                has_shellview = []

                def enum_child(child, lparam2):
                    if win32gui.GetClassName(child) == "SHELLDLL_DefView":
                        has_shellview.append(True)
                    return True

                win32gui.EnumChildWindows(hwnd, enum_child, None)
                if not has_shellview:
                    workerw_list.append(hwnd)
        return True

    win32gui.EnumWindows(enum_windows, None)
    # 候補があれば先頭を返す
    return workerw_list[0] if workerw_list else None


# ───────────────────────────
# カレンダー（日曜始まり／土=シアン, 日=マゼンタ, 祝=ライトグリーン）
# ───────────────────────────
class CustomCalendar(QCalendarWidget):
    def __init__(self):
        super().__init__()
        self.setFirstDayOfWeek(Qt.DayOfWeek.Sunday)
        self.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.setNavigationBarVisible(True)
        self.setGridVisible(False)
        self.setStyleSheet("background-color: rgba(0,0,0,120); color: white;")
        self.update_calendar_colors()

    def update_calendar_colors(self):
        default_fmt = QTextCharFormat()
        for d in (
            Qt.DayOfWeek.Monday, Qt.DayOfWeek.Tuesday, Qt.DayOfWeek.Wednesday,
            Qt.DayOfWeek.Thursday, Qt.DayOfWeek.Friday
        ):
            self.setWeekdayTextFormat(d, default_fmt)

        sat_fmt = QTextCharFormat(); sat_fmt.setForeground(QColor("#00FFFF"))
        sun_fmt = QTextCharFormat(); sun_fmt.setForeground(QColor("#FF00FF"))
        self.setWeekdayTextFormat(Qt.DayOfWeek.Saturday, sat_fmt)
        self.setWeekdayTextFormat(Qt.DayOfWeek.Sunday,   sun_fmt)

        holiday_fmt = QTextCharFormat(); holiday_fmt.setForeground(QColor("#90EE90"))

        today = datetime.date.today()
        y, m = today.year, today.month
        first = datetime.date(y, m, 1)
        last  = (first.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)

        # クリア → 祝日塗り
        for d in range(1, last.day + 1):
            self.setDateTextFormat(QDate(y, m, d), QTextCharFormat())
        for d in range(1, last.day + 1):
            day = datetime.date(y, m, d)
            if jpholiday.is_holiday(day):
                self.setDateTextFormat(QDate(y, m, d), holiday_fmt)


# ───────────────────────────
# メイン（田の字レイアウト）
# ───────────────────────────
class TaskMiniWidget(QWidget):
    def __init__(self):
        super().__init__()

        # 枠なし・半透明。最前面は付けない（WorkerWの子にするので不要）
        self.setWindowTitle("TaskMini Dashboard")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.fnt = QFont("Consolas", 14)
        self.big = QFont("Consolas", 16)

        grid = QGridLayout(self)
        grid.setSpacing(10); grid.setContentsMargins(8, 8, 8, 8)

        def make_label(text, big=False):
            lbl = QLabel(text)
            lbl.setFont(self.big if big else self.fnt)
            lbl.setStyleSheet("color:white; background-color: rgba(0,0,0,90); padding:6px 8px; border-radius:8px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            return lbl

        self.cpu_label   = make_label("CPU: -- %")
        self.calendar    = CustomCalendar()
        self.ram_label   = make_label("RAM: -- %")
        self.gpu_label   = make_label("GPU: -- %")
        self.clock_label = make_label("--:--:--\nYYYY/MM/DD", big=True)
        self.net_label   = make_label("NET: ↑-- KB/s ↓-- KB/s")

        # 田の字配置
        grid.addWidget(self.cpu_label,   0, 0)
        grid.addWidget(self.calendar,    0, 1)
        grid.addWidget(self.ram_label,   0, 2)
        grid.addWidget(self.gpu_label,   1, 0)
        grid.addWidget(self.clock_label, 1, 1)
        grid.addWidget(self.net_label,   1, 2)

        # 右下に配置
        self.resize(820, 420)
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - self.width() - 24, screen.height() - self.height() - 24)

        # ネット速度
        self.last_net = psutil.net_io_counters()

        # 1秒更新
        self.timer = QTimer(self); self.timer.timeout.connect(self.update_info); self.timer.start(1000)

        # 表示直後に WorkerW の子にして背面固定（失敗時は HWND_BOTTOM を併用）
        QTimer.singleShot(0, self.attach_to_wallpaper)

        # 深夜にカレンダー更新（24h）
        self.midnight_timer = QTimer(self)
        self.midnight_timer.timeout.connect(self.calendar.update_calendar_colors)
        self.midnight_timer.start(24 * 60 * 60 * 1000)

    # 壁紙ウィンドウ（WorkerW）の子にする
    def attach_to_wallpaper(self):
        hwnd = int(self.winId())
        workerw = get_workerw()
        if workerw:
            try:
                win32gui.SetParent(hwnd, workerw)
                # 念のため一度背面に送っておく
                win32gui.SetWindowPos(
                    hwnd, win32con.HWND_BOTTOM, self.x(), self.y(), 0, 0,
                    win32con.SWP_NOSIZE | win32con.SWP_NOMOVE | win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW
                )
                return
            except win32gui.error:
                pass
        # フォールバック：親変更に失敗したら最下段へ
        win32gui.SetWindowPos(
            hwnd, win32con.HWND_BOTTOM, self.x(), self.y(), 0, 0,
            win32con.SWP_NOSIZE | win32con.SWP_NOMOVE | win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW
        )

    def update_info(self):
        # CPU / RAM
        self.cpu_label.setText(f"CPU: {psutil.cpu_percent():.1f} %")
        self.ram_label.setText(f"RAM: {psutil.virtual_memory().percent:.1f} %")

        # GPU（AMD対応は後で実装予定）
        self.gpu_label.setText("GPU: -- %")

        # ネット速度（KB/s）
        now = psutil.net_io_counters()
        up_kb   = (now.bytes_sent - self.last_net.bytes_sent) / 1024.0
        down_kb = (now.bytes_recv - self.last_net.bytes_recv) / 1024.0
        self.last_net = now
        self.net_label.setText(f"NET: ↑{up_kb:.1f} KB/s ↓{down_kb:.1f} KB/s")

        # 時計
        n = datetime.datetime.now()
        self.clock_label.setText(f"{n:%H:%M:%S}\n{n:%Y/%m/%d (%a)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = TaskMiniWidget()
    w.show()
    sys.exit(app.exec())
