import ctypes
import math
from ctypes import wintypes, c_int16, c_void_p, POINTER, cast, Structure

from PySide6.QtCore import Qt, Signal, QTimer, QTime, QPoint, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QVariantAnimation, QAbstractAnimation, QUrl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QLineEdit, QFrame, QGraphicsOpacityEffect,
    QMenu, QDialog, QDialogButtonBox, QTextBrowser, QStyle, QStyleOption
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtGui import QPainter, QPainterPath, QPen, QColor, QFont, QAction, QFontMetrics



# ── Win32 native event constants ──
WM_NCHITTEST = 0x0084
HTCLIENT = 1
HTCAPTION = 2
HTLEFT = 10
HTRIGHT = 11
HTTOP = 12
HTTOPLEFT = 13
HTTOPRIGHT = 14
HTBOTTOM = 15
HTBOTTOMLEFT = 16
HTBOTTOMRIGHT = 17

BORDER_WIDTH = 10
TITLE_BAR_HEIGHT = 50
CORNER_RADIUS = 20


class MSG(Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


# ── 语音气泡播放状态 ──
_PLAYING_BUBBLES = set()  # 存放正在播放的 VoiceBubbleWidget 引用


class VoiceBubbleWidget(QFrame):
    """微信风格的语音气泡 — 显示扬声器图标 + 时长，点击播放/暂停。"""

    play_requested = Signal(str)  # filepath

    # 颜色配置
    AI_BG = "rgba(255,235,240,0.85)"
    AI_BG_DARK = "#3d3d5c"
    USER_BG = "#95ec69"
    USER_BG_DARK = "#4a9e3f"
    TEXT_COLOR = "#333"
    TEXT_COLOR_DARK = "#e0e0e0"

    # 宽度映射：时长(秒) -> 像素宽度
    MIN_WIDTH = 80
    MAX_WIDTH = 200

    def __init__(self, filepath: str, duration: float, text: str, is_user: bool, dark_mode: bool, parent=None):
        super().__init__(parent)
        self._filepath = filepath
        self._duration = duration
        self._text = text
        self._is_user = is_user
        self._dark = dark_mode
        self._playing = False
        self._anim_frame = 0

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(44)

        # 宽度根据时长映射
        w = self.MIN_WIDTH + int(duration * 12)
        self.setFixedWidth(min(w, self.MAX_WIDTH))

        # 动画定时器（播放时刷新波形）
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(300)
        self._anim_timer.timeout.connect(self._tick_anim)

        # 右键菜单
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # 初始背景样式（与文本气泡一致的 QSS 渲染路径）
        self._apply_bg_style()

    # ── 属性 ──
    @property
    def filepath(self) -> str:
        return self._filepath

    @property
    def voice_text(self) -> str:
        return self._text

    @property
    def is_playing(self) -> bool:
        return self._playing

    def set_playing(self, playing: bool):
        self._playing = playing
        if playing:
            _PLAYING_BUBBLES.add(self)
            self._anim_timer.start()
        else:
            _PLAYING_BUBBLES.discard(self)
            self._anim_timer.stop()
            self._anim_frame = 0
        self.update()

    # ── 事件 ──
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.play_requested.emit(self._filepath)
        super().mousePressEvent(event)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        action = QAction("转文字", self)
        action.triggered.connect(self._show_text_dialog)
        menu.addAction(action)
        menu.exec(self.mapToGlobal(pos))

    def _show_text_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("语音内容")
        dlg.resize(320, 160)
        layout = QVBoxLayout(dlg)
        browser = QTextBrowser(dlg)
        browser.setPlainText(self._text)
        browser.setOpenExternalLinks(False)
        layout.addWidget(browser)
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        btn_box.accepted.connect(dlg.accept)
        layout.addWidget(btn_box)
        dlg.exec()

    def _tick_anim(self):
        self._anim_frame = (self._anim_frame + 1) % 4
        self.update()

    # ── 背景样式（与文本气泡一致的 QSS 渲染路径）──
    def _apply_bg_style(self):
        if self._is_user:
            bg = self.USER_BG_DARK if self._dark else self.USER_BG
        else:
            bg = self.AI_BG_DARK if self._dark else self.AI_BG
        self.setStyleSheet(f"""
            VoiceBubbleWidget {{
                background-color: {bg};
                border-radius: 12px;
                border: none;
            }}
        """)

    # ── 绘制 ──
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()

        # QSS 背景绘制（与文本气泡完全相同的渲染路径）
        opt = QStyleOption()
        opt.initFrom(self)
        self.style().drawPrimitive(QStyle.PE_Widget, opt, painter, self)

        text_color = self.TEXT_COLOR_DARK if self._dark else self.TEXT_COLOR
        painter.setPen(QColor(text_color))

        icon_size = 18
        margin = 12
        center_y = rect.center().y()

        if self._is_user:
            # 用户气泡：图标在右侧，文字在左侧
            icon_x = rect.right() - margin - icon_size
            text_x = margin
            text_align = Qt.AlignmentFlag.AlignLeft
        else:
            # AI 气泡：图标在左侧，文字在右侧
            icon_x = margin
            text_x = margin + icon_size + 8
            text_align = Qt.AlignmentFlag.AlignLeft

        # 绘制扬声器图标
        self._draw_speaker(painter, icon_x, center_y - icon_size // 2, icon_size, text_color)

        # 播放时绘制波形动画
        if self._playing:
            self._draw_waveform(painter, icon_x + icon_size + 6, center_y, text_color)

        # 绘制时长文字
        minutes = int(self._duration) // 60
        seconds = int(self._duration) % 60
        duration_str = f"{minutes}'{seconds:02d}\""
        painter.setFont(QFont("Microsoft YaHei", 11))
        fm = QFontMetrics(painter.font())
        dur_w = fm.horizontalAdvance(duration_str)

        if self._is_user:
            dur_x = text_x
        else:
            dur_x = self.width() - margin - dur_w
        painter.drawText(dur_x, center_y + fm.ascent() // 2 - 1, duration_str)

        painter.end()

    def _draw_speaker(self, painter: QPainter, x: int, y: int, size: int, color: QColor):
        """绘制简易扬声器图标。"""
        painter.save()
        painter.setPen(QPen(QColor(color), 2))
        painter.setBrush(color)

        w = size
        h = size
        cx = x + w // 2
        cy = y + h // 2
        s = w // 6

        # 主体矩形
        speaker = QPainterPath()
        speaker.moveTo(cx + s * 2, y)
        speaker.lineTo(cx - s * 1, y + h // 3)
        speaker.lineTo(x, y + h // 3)
        speaker.lineTo(x, y + h * 2 // 3)
        speaker.lineTo(cx - s * 1, y + h * 2 // 3)
        speaker.lineTo(cx + s * 2, y + h)
        speaker.closeSubpath()
        painter.drawPath(speaker)

        # 声波弧线
        painter.setBrush(Qt.BrushStyle.NoBrush)
        arc_pen = QPen(QColor(color), 1.5)
        painter.setPen(arc_pen)
        arc1 = QPainterPath()
        arc1.moveTo(cx + s * 3, cy - h // 4)
        arc1.cubicTo(cx + s * 5, cy - h // 4, cx + s * 5, cy + h // 4, cx + s * 3, cy + h // 4)
        painter.drawPath(arc1)

        arc2 = QPainterPath()
        arc2.moveTo(cx + s * 4, cy - h // 2)
        arc2.cubicTo(cx + s * 7, cy - h // 2, cx + s * 7, cy + h // 2, cx + s * 4, cy + h // 2)
        painter.drawPath(arc2)

        painter.restore()

    def _draw_waveform(self, painter: QPainter, x: int, cy: int, color: QColor):
        """绘制播放动画的波形竖条。"""
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)

        bar_count = 4
        bar_width = 3
        gap = 3
        heights = [6, 12, 8, 14] if self._anim_frame % 2 == 0 else [10, 6, 14, 8]
        for i in range(bar_count):
            bh = heights[i]
            bx = x + i * (bar_width + gap)
            painter.drawRoundedRect(bx, cy - bh // 2, bar_width, bh, 1, 1)
        painter.restore()

    def update_theme(self, dark: bool):
        self._dark = dark
        self._apply_bg_style()
        self.update()


class ChatWindow(QWidget):
    message_sent = Signal(str)
    voice_mode_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dark_mode = False
        self._voice_mode = False
        self._bubbles = []  # (container, text_label, time_label, is_user)
        self._active_animations = set()

        # 语音播放器
        self._voice_player = QMediaPlayer()
        self._voice_audio = QAudioOutput()
        self._voice_player.setAudioOutput(self._voice_audio)
        self._voice_audio.setVolume(0.8)
        self._voice_player.mediaStatusChanged.connect(self._on_media_status)
        self._current_voice_bubble = None

        self._setup_window()
        self._build_ui()

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(360, 500)
        self.setMinimumSize(280, 350)

    def _build_ui(self):
        # Root container
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        self._root = QWidget()
        self._root.setObjectName("chatRoot")
        root_layout.addWidget(self._root)

        layout = QVBoxLayout(self._root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Title bar ---
        self._title_bar = QWidget()
        self._title_bar.setFixedHeight(TITLE_BAR_HEIGHT)

        title_layout = QHBoxLayout(self._title_bar)
        title_layout.setContentsMargins(14, 0, 10, 0)

        title_label = QLabel("千早爱音")
        title_label.setStyleSheet("color: white; font-size: 14px; font-weight: bold; border: none;")

        self._typing_label = QLabel("  对方正在输入...")
        self._typing_label.setStyleSheet("color: rgba(255,255,255,0.75); font-size: 12px; border: none;")
        self._typing_label.hide()

        self._close_btn = QPushButton("✕")
        self._close_btn.setFixedSize(36, 36)
        self._close_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: white; font-size: 16px;
                border: none; border-radius: 18px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.3); }
        """)
        self._close_btn.clicked.connect(self.hide)

        title_layout.addWidget(title_label)
        title_layout.addWidget(self._typing_label)
        title_layout.addStretch()
        title_layout.addWidget(self._close_btn)

        # --- Message area ---
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._msg_container = QWidget()
        self._msg_layout = QVBoxLayout(self._msg_container)
        self._msg_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._msg_layout.setSpacing(8)
        self._msg_layout.setContentsMargins(12, 12, 12, 12)

        self._scroll.setWidget(self._msg_container)

        # --- Input area ---
        self._input_widget = QWidget()
        input_layout = QHBoxLayout(self._input_widget)
        input_layout.setContentsMargins(8, 8, 8, 10)

        self._input = QLineEdit()
        self._input.setPlaceholderText("输入消息...")

        self._voice_btn = QPushButton("🎤 语音")
        self._voice_btn.setFixedSize(64, 36)
        self._voice_btn.setCheckable(True)
        self._voice_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #999;
                border: 1px solid #ddd; border-radius: 18px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(255,107,157,0.1);
                border-color: #FF6B9D; color: #FF6B9D;
            }
            QPushButton:checked {
                background: #FF6B9D; color: white; border: none;
            }
        """)
        self._voice_btn.toggled.connect(self._on_voice_toggled)

        self._send_btn = QPushButton("发送")
        self._send_btn.setFixedSize(58, 36)
        self._send_btn.setStyleSheet("""
            QPushButton {
                background: #FF6B9D; color: white; border: none;
                border-radius: 18px; font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { background: #ff4d8f; }
            QPushButton:disabled { background: #ccc; }
        """)

        input_layout.addWidget(self._input)
        input_layout.addWidget(self._voice_btn)
        input_layout.addWidget(self._send_btn)

        # --- Assemble ---
        layout.addWidget(self._title_bar)
        layout.addWidget(self._scroll)
        layout.addWidget(self._input_widget)

        # --- Signals ---
        self._send_btn.clicked.connect(self._on_send)
        self._input.returnPressed.connect(self._on_send)

        # --- Apply initial theme ---
        self._apply_theme()

    # ── Native edge resize + title bar drag ──

    def nativeEvent(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            msg = cast(c_void_p(int(message)), POINTER(MSG)).contents
            if msg.message == WM_NCHITTEST:
                return self._handle_nchittest(msg)
        return (False, 0)

    def _handle_nchittest(self, msg):
        x = c_int16(msg.lParam & 0xFFFF).value
        y = c_int16((msg.lParam >> 16) & 0xFFFF).value

        rect = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(msg.hwnd, ctypes.byref(rect))

        on_left = x <= rect.left + BORDER_WIDTH
        on_right = x >= rect.right - BORDER_WIDTH
        on_top = y <= rect.top + BORDER_WIDTH
        on_bottom = y >= rect.bottom - BORDER_WIDTH

        # Corners
        if on_top and on_left:
            return (True, HTTOPLEFT)
        if on_top and on_right:
            return (True, HTTOPRIGHT)
        if on_bottom and on_left:
            return (True, HTBOTTOMLEFT)
        if on_bottom and on_right:
            return (True, HTBOTTOMRIGHT)
        # Edges
        if on_left:
            return (True, HTLEFT)
        if on_right:
            return (True, HTRIGHT)
        if on_top:
            return (True, HTTOP)
        if on_bottom:
            return (True, HTBOTTOM)

        # Title bar drag (exclude close button)
        if y < rect.top + TITLE_BAR_HEIGHT:
            pt = wintypes.POINT(x, y)
            ctypes.windll.user32.ScreenToClient(msg.hwnd, ctypes.byref(pt))
            child = self.childAt(QPoint(pt.x, pt.y))
            if isinstance(child, QPushButton):
                return (False, 0)
            return (True, HTCAPTION)

        return (False, 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)

    # --- Send ---
    def _on_send(self):
        text = self._input.text().strip()
        if not text:
            return
        self._add_bubble(text, is_user=True)
        self._input.clear()
        self.message_sent.emit(text)
        self._set_loading(True)
        # 重置为默认提示文字
        self._typing_label.setText("  对方正在输入...")

    # --- Bubble creation ---
    def _create_bubble_widget(self, text: str, is_user: bool):
        container = QFrame()
        container.setObjectName("bubble_container")
        container.setFrameShape(QFrame.Shape.NoFrame)

        inner_layout = QVBoxLayout(container)
        inner_layout.setContentsMargins(14, 10, 14, 10)
        inner_layout.setSpacing(0)

        text_label = QLabel(text)
        text_label.setObjectName("bubble_text")
        text_label.setWordWrap(True)

        inner_layout.addWidget(text_label)

        self._style_bubble(container, is_user)

        return container, text_label

    def _animate_entrance(self, container: QFrame):
        opacity_effect = QGraphicsOpacityEffect(container)
        opacity_effect.setOpacity(0.0)
        container.setGraphicsEffect(opacity_effect)

        anim_opacity = QPropertyAnimation(opacity_effect, b"opacity")
        anim_opacity.setDuration(200)
        anim_opacity.setStartValue(0.0)
        anim_opacity.setEndValue(1.0)

        inner_layout = container.layout()
        orig = inner_layout.contentsMargins()
        slide_start = orig.top() + 15
        inner_layout.setContentsMargins(orig.left(), slide_start, orig.right(), orig.bottom())

        anim_slide = QVariantAnimation(container)
        anim_slide.setDuration(200)
        anim_slide.setStartValue(slide_start)
        anim_slide.setEndValue(orig.top())
        anim_slide.valueChanged.connect(
            lambda val: inner_layout.setContentsMargins(orig.left(), val, orig.right(), orig.bottom())
        )

        group = QParallelAnimationGroup(container)
        group.addAnimation(anim_opacity)
        group.addAnimation(anim_slide)

        def _on_finished():
            # Leave the opacity effect in place at 1.0 — removing it via
            # setGraphicsEffect(None) confuses Qt's render cache for sibling
            # widgets, causing subsequent animations on new bubbles to stop
            # working.
            opacity_effect.setOpacity(1.0)
            inner_layout.setContentsMargins(orig.left(), orig.top(), orig.right(), orig.bottom())
            self._active_animations.discard(group)

        group.finished.connect(_on_finished)
        self._active_animations.add(group)
        group.start(QAbstractAnimation.DeleteWhenStopped)

    def _add_bubble(self, text: str, is_user: bool):
        container, text_label = self._create_bubble_widget(text, is_user)

        # 动态约束气泡最大宽度 ≈ 滚动区可用宽度的 85%
        scroll_w = self._scroll.viewport().width()
        available = scroll_w - 24
        if available > 50:
            container.setMaximumWidth(int(available * 0.85))

        # Timestamp below the bubble
        time_str = QTime.currentTime().toString("HH:mm")
        time_color = "#888" if self._dark_mode else "#aaa"
        time_label = QLabel(time_str)
        time_label.setObjectName("bubble_time")
        time_label.setStyleSheet(
            f"color: {time_color}; font-size: 10px; background: transparent; border: none;"
        )
        time_label.setAlignment(
            Qt.AlignmentFlag.AlignRight if is_user
            else Qt.AlignmentFlag.AlignLeft
        )

        # Vertical group: bubble + timestamp
        bubble_group = QVBoxLayout()
        bubble_group.setContentsMargins(0, 0, 0, 0)
        bubble_group.setSpacing(2)
        bubble_group.addWidget(container)
        bubble_group.addWidget(time_label)

        # Row layout
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        if is_user:
            row.addStretch()
        row.addLayout(bubble_group)
        if not is_user:
            row.addStretch()

        self._msg_layout.addLayout(row)
        self._bubbles.append((container, text_label, time_label, is_user))

        self._animate_entrance(container)

        QTimer.singleShot(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        sb = self._scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _set_loading(self, active: bool):
        self._send_btn.setEnabled(not active)
        self._input.setEnabled(not active)
        self._typing_label.setVisible(active)
        if active:
            self._input.setFocus()

    # ── 语音气泡 ──
    def set_loading_text(self, text: str):
        """动态修改加载提示文字（如 '对方正在说话...'）。"""
        if self._typing_label.isVisible():
            self._typing_label.setText(f"  {text}")

    def _on_voice_toggled(self, checked: bool):
        self._voice_mode = checked
        self.voice_mode_changed.emit(checked)
        self._voice_btn.setText("🎤 语音ON" if checked else "🎤 语音")

    def is_voice_mode(self) -> bool:
        return self._voice_mode

    def display_voice_response(self, text: str, filepath: str, duration: float,
                                chinese_text: str = "", is_user: bool = False):
        """纯语音模式：直接显示语音气泡，不做打字机效果。"""
        self._set_loading(False)
        self._add_voice_bubble(filepath, duration, text, chinese_text, is_user)

    def _add_voice_bubble(self, filepath: str, duration: float, text: str,
                           chinese_text: str, is_user: bool):
        bubble = VoiceBubbleWidget(filepath, duration, text, is_user, self._dark_mode)

        # 播放信号连接
        bubble.play_requested.connect(self._play_voice)

        scroll_w = self._scroll.viewport().width()
        available = scroll_w - 24
        if available > 50:
            bubble.setMaximumWidth(int(available * 0.85))

        # 中文原文说明（语音气泡下方，浅灰小字）
        chinese_label = None
        if chinese_text:
            chinese_label = QLabel(chinese_text)
            chinese_label.setWordWrap(True)
            text_color = "#bbb" if self._dark_mode else "#999"
            chinese_label.setStyleSheet(
                f"color: {text_color}; font-size: 11px; background: transparent; border: none;"
            )
            chinese_label.setMaximumWidth(bubble.maximumWidth())

        # 时间戳
        time_str = QTime.currentTime().toString("HH:mm")
        time_color = "#888" if self._dark_mode else "#aaa"
        time_label = QLabel(time_str)
        time_label.setObjectName("bubble_time")
        time_label.setStyleSheet(
            f"color: {time_color}; font-size: 10px; background: transparent; border: none;"
        )
        time_label.setAlignment(
            Qt.AlignmentFlag.AlignRight if is_user
            else Qt.AlignmentFlag.AlignLeft
        )

        bubble_group = QVBoxLayout()
        bubble_group.setContentsMargins(0, 0, 0, 0)
        bubble_group.setSpacing(2)
        bubble_group.addWidget(bubble)
        if chinese_label:
            bubble_group.addWidget(chinese_label)
        bubble_group.addWidget(time_label)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        if is_user:
            row.addStretch()
        row.addLayout(bubble_group)
        if not is_user:
            row.addStretch()

        self._msg_layout.addLayout(row)
        self._bubbles.append((bubble, chinese_label, time_label, is_user))

        self._animate_voice_entrance(bubble)
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _animate_voice_entrance(self, widget: QFrame):
        """VoiceBubbleWidget 的淡入动画（无 slide，因为 VoiceBubbleWidget 无 layout）。"""
        opacity_effect = QGraphicsOpacityEffect(widget)
        opacity_effect.setOpacity(0.0)
        widget.setGraphicsEffect(opacity_effect)

        anim = QPropertyAnimation(opacity_effect, b"opacity")
        anim.setDuration(200)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)

        def _on_finished():
            opacity_effect.setOpacity(1.0)
            self._active_animations.discard(anim)

        anim.finished.connect(_on_finished)
        self._active_animations.add(anim)
        anim.start(QAbstractAnimation.DeleteWhenStopped)

    # ── 语音播放 ──
    def _play_voice(self, filepath: str):
        # 停止当前播放
        self._voice_player.stop()
        if self._current_voice_bubble:
            self._current_voice_bubble.set_playing(False)

        # 找到对应的气泡
        for child in self._bubbles:
            widget = child[0]
            if isinstance(widget, VoiceBubbleWidget) and widget.filepath == filepath:
                self._current_voice_bubble = widget
                widget.set_playing(True)
                break

        self._voice_player.setSource(QUrl.fromLocalFile(filepath))
        self._voice_player.play()

    def _on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self._current_voice_bubble:
                self._current_voice_bubble.set_playing(False)
                self._current_voice_bubble = None
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            if self._current_voice_bubble:
                self._current_voice_bubble.set_playing(False)
                self._current_voice_bubble = None

    # --- Public API ---
    def display_message(self, text: str, is_user: bool = False):
        self._add_bubble(text, is_user)

    def display_splitted_response(self, text: str):
        self._segments = self._split_text(text)
        self._seg_index = 0
        self._show_next_segment()

    def _split_text(self, text: str) -> list[str]:
        import re
        parts = re.split(r'(?<=[。！？\n])(?![。！？\n])', text)
        parts = [p.strip() for p in parts if p.strip()]
        MAX_LEN = 40
        result = []
        for part in parts:
            if len(part) <= MAX_LEN:
                result.append(part)
            else:
                sub = re.split(r'(?<=[，、；])(?![，、；])', part)
                for sp in sub:
                    sp = sp.strip()
                    if not sp:
                        continue
                    if len(sp) <= MAX_LEN:
                        result.append(sp)
                    else:
                        while sp:
                            result.append(sp[:MAX_LEN])
                            sp = sp[MAX_LEN:]
        return result

    def _show_next_segment(self):
        if self._seg_index < len(self._segments):
            self._add_bubble(self._segments[self._seg_index], False)
            self._seg_index += 1
            delay = min(8000, 4000 + len(self._segments[self._seg_index - 1]) * 100)
            QTimer.singleShot(delay, self._show_next_segment)
        else:
            self._segments = []
            self.set_loading(False)

    def set_loading(self, active: bool):
        self._set_loading(active)

    def show_error(self, text: str):
        msg = QLabel(text)
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setWordWrap(True)
        msg.setStyleSheet("color: #e74c3c; font-size: 12px; padding: 6px; background: transparent;")
        self._msg_layout.addWidget(msg)
        QTimer.singleShot(50, self._scroll_to_bottom)

    # --- Theme ---
    def toggle_theme(self):
        self._dark_mode = not self._dark_mode
        self._apply_theme()

    def _apply_theme(self):
        dark = self._dark_mode

        # Root
        root_bg = "#1e1e2e" if dark else "#ffffff"
        root_border = "#3d3d5c" if dark else "#e0e0e0"
        self._root.setStyleSheet(f"""
            background-color: {root_bg};
            border-radius: {CORNER_RADIUS}px;
            border: 1px solid {root_border};
        """)

        # Title bar
        title_color = "rgba(255, 150, 180, 0.92)" if not dark else "rgba(255, 107, 157, 0.88)"
        self._title_bar.setStyleSheet(
            f"background-color: {title_color}; border-radius: {CORNER_RADIUS}px {CORNER_RADIUS}px 0 0;"
        )

        # Scroll area
        scroll_bg = "#2d2d3f" if dark else "#f0f0f0"
        handle_color = "#555" if dark else "#ccc"
        self._scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background: {scroll_bg}; }}
            QScrollBar:vertical {{ width: 4px; background: transparent; }}
            QScrollBar::handle:vertical {{ background: {handle_color}; border-radius: 2px; }}
        """)

        # Input area
        input_bg = "#1e1e2e" if dark else "white"
        self._input_widget.setStyleSheet(
            f"background: {input_bg}; border-radius: 0 0 {CORNER_RADIUS}px {CORNER_RADIUS}px;"
        )

        # Close button
        close_color = "#666" if not dark else "white"
        close_hover = "rgba(0,0,0,0.1)" if not dark else "rgba(255,255,255,0.3)"
        self._close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {close_color}; font-size: 16px;
                border: none; border-radius: 18px;
            }}
            QPushButton:hover {{ background: {close_hover}; }}
        """)

        # Voice toggle button — dark mode adapted
        voice_border = "#5d5d7c" if dark else "#ddd"
        voice_color = "#aaa" if dark else "#999"
        voice_hover_bg = "rgba(255,107,157,0.2)" if dark else "rgba(255,107,157,0.1)"
        self._voice_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {voice_color};
                border: 1px solid {voice_border}; border-radius: 18px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: {voice_hover_bg};
                border-color: #FF6B9D; color: #FF6B9D;
            }}
            QPushButton:checked {{
                background: #FF6B9D; color: white; border: none;
            }}
        """)

        # QLineEdit
        edit_bg = "#3d3d5c" if dark else "#fafafa"
        edit_border = "#5d5d7c" if dark else "#ddd"
        edit_focus_bg = "#3d3d5c" if dark else "white"
        edit_color = "#e0e0e0" if dark else "black"
        placeholder_color = "#888" if dark else "#999"
        self._input.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid {edit_border}; border-radius: 18px;
                padding: 8px 16px; font-size: 13px;
                background: {edit_bg}; min-height: 20px;
                color: {edit_color};
            }}
            QLineEdit:focus {{ border-color: #FF6B9D; background: {edit_focus_bg}; }}
            QLineEdit::placeholder {{ color: {placeholder_color}; }}
        """)

        # Update all existing bubbles
        time_color = "#888" if dark else "#aaa"
        chinese_color = "#bbb" if dark else "#999"
        for container, text_label, time_label, is_user in self._bubbles:
            if isinstance(container, VoiceBubbleWidget):
                container.update_theme(dark)
                # 更新中文说明文字颜色
                if text_label is not None:
                    text_label.setStyleSheet(
                        f"color: {chinese_color}; font-size: 11px; background: transparent; border: none;"
                    )
            else:
                self._style_bubble(container, is_user)
            time_label.setStyleSheet(
                f"color: {time_color}; font-size: 10px; background: transparent; border: none;"
            )

    def _style_bubble(self, container: QFrame, is_user: bool):
        dark = self._dark_mode
        if is_user:
            bg = "#6b6b7b" if dark else "#e8e8e8"
            text_color = "white" if dark else "#333"
        else:
            bg = "#3d3d5c" if dark else "rgba(255,235,240,0.85)"
            text_color = "#e0e0e0" if dark else "#333"

        container.setStyleSheet(f"""
            QFrame#bubble_container {{
                background-color: {bg};
                border-radius: 12px;
                border: none;
            }}
            QLabel#bubble_text {{
                color: {text_color};
                background: transparent;
                border: none;
                font-size: 13px;
                line-height: 1.4;
            }}
        """)
