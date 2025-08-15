import sys
import psutil
import jpholiday
import datetime
from PyQt6.QtWidgets import QApplication, QWidget, QGridLayout, QLabel, QCalendarWidget
from PyQt6.QtCore import Qt, QTimer, QDate
from PyQt6.QtGui import QColor, QTextCharFormat, QFont


class CustomCalendar(QCalendarWidget):
    def __init__(self):
        super().__init__()
        self.setFirstDayOfWeek(Qt.DayOfWeek.Sunday)  # 日曜始まり
        self.update_calendar_colors()

    def update_calendar_colors(self):
        today = datetime.date.today()
        year, month = today.year, today.month

        # 全セルの色をリセット
        default_format = QTextCharFormat()
        self.setWeekdayTextFormat(Qt.DayOfWeek.Monday, default_format)
        self.setWeekdayTextFormat(Qt.DayOfWeek.Tuesday, default_format)
        self.setWeekdayTextFormat(Qt.DayOfWeek.Wednesday, default_format)
        self.setWeekdayTextFormat(Qt.DayOfWeek.Thursday, default_format)
        self.setWeekdayTextFormat(Qt.DayOfWeek.Friday, default_format)
        self.setWeekdayTextFormat(Qt.DayOfWeek.Saturday, default_format)
        self.setWeekdayTextFormat(Qt.DayOfWeek.Sunday, default_format)

        # 土曜シアン
        sat_format = QTextCharFormat()
        sat_format.setForeground(QColor("#00FFFF"))
        self.setWeekdayTextFormat(Qt.DayOfWeek.Saturday, sat_format)

        # 日曜マゼンタ
        sun_format = QTextCharFormat()
        sun_format.setForeground(QColor("#FF00FF"))
        self.setWeekdayTextFormat(Qt.DayOfWeek.Sunday, sun_format)

        # 祝日ライトグリーン
        holiday_format = QTextCharFormat()
        holiday_format.setForeground(QColor("#90EE90"))

        # その月の全日付をチェック
        for day in range(1, 32):
            try:
                date = datetime.date(year, month, day)
                if jpholiday.is_holiday(date):
                    qdate = QDate(date.year, date.month, date.day)
                    self.setDateTextFormat(qdate, holiday_format)
            except ValueError:
                continue


class TaskMiniWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TaskMini Dashboard")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # フォント
        font = QFont("Consolas", 14)

        # レイアウト
        layout = QGridLayout()
        layout.setSpacing(10)

        # 各ラベル
        self.cpu_label = QLabel("CPU: -- %")
        self.cpu_label.setFont(font)
        self.cpu_label.setStyleSheet("color: white;")

        self.ram_label = QLabel("RAM: -- %")
        self.ram_label.setFont(font)
        self.ram_label.setStyleSheet("color: white;")

        self.gpu_label = QLabel("GPU: -- %")
        self.gpu_label.setFont(font)
        self.gpu_label.setStyleSheet("color: white;")

        self.net_label = QLabel("NET: -- KB/s")
        self.net_label.setFont(font)
        self.net_label.setStyleSheet("color: white;")

        self.clock_label = QLabel("--:--:--\nYYYY/MM/DD")
        self.clock_label.setFont(QFont("Consolas", 16))
        self.clock_label.setStyleSheet("color: white;")

        # カレンダー
        self.calendar = CustomCalendar()
        self.calendar.setStyleSheet("background-color: rgba(0, 0, 0, 100); color: white;")

        # グリッド配置
        layout.addWidget(self.cpu_label, 0, 0)
        layout.addWidget(self.calendar, 0, 1)
        layout.addWidget(self.ram_label, 0, 2)
        layout.addWidget(self.gpu_label, 1, 0)
        layout.addWidget(self.clock_label, 1, 1)
        layout.addWidget(self.net_label, 1, 2)

        self.setLayout(layout)
        self.resize(800, 400)

        # ネット速度計測用
        self.last_net_io = psutil.net_io_counters()

        # タイマー更新
        timer = QTimer(self)
        timer.timeout.connect(self.update_info)
        timer.start(1000)

    def update_info(self):
        # CPU / RAM
        self.cpu_label.setText(f"CPU: {psutil.cpu_percent():.1f} %")
        self.ram_label.setText(f"RAM: {psutil.virtual_memory().percent:.1f} %")

        # GPU → 仮表示（AMD対応は後で追加）
        self.gpu_label.setText("GPU: -- %")

        # ネットワーク速度
        current_net_io = psutil.net_io_counters()
        sent = (current_net_io.bytes_sent - self.last_net_io.bytes_sent) / 1024
        recv = (current_net_io.bytes_recv - self.last_net_io.bytes_recv) / 1024
        self.net_label.setText(f"NET: ↑{sent:.1f} KB/s ↓{recv:.1f} KB/s")
        self.last_net_io = current_net_io

        # 時計
        now = datetime.datetime.now()
        self.clock_label.setText(f"{now:%H:%M:%S}\n{now:%Y/%m/%d (%a)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = TaskMiniWidget()
    widget.show()
    sys.exit(app.exec())
