import ctypes
from ctypes import wintypes, c_int16, c_void_p, POINTER, cast, Structure

from PySide6.QtCore import Qt, Signal, QTimer, QTime, QPoint, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QVariantAnimation, QAbstractAnimation
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QLineEdit, QFrame, QGraphicsOpacityEffect
)



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


class ChatWindow(QWidget):
    message_sent = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dark_mode = False
        self._bubbles = []  # (container, text_label, time_label, is_user)
        self._active_animations = set()
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
        for container, text_label, time_label, is_user in self._bubbles:
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
