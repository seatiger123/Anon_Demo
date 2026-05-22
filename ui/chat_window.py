from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QLineEdit, QSizePolicy
)


class ChatWindow(QWidget):
    message_sent = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_pos = None
        self._setup_window()
        self._build_ui()

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(360, 500)

    def _build_ui(self):
        # Root widget with rounded corners and shadow
        self.setStyleSheet("""
            #chatRoot {
                background-color: #ffffff;
                border-radius: 12px;
                border: 1px solid #e0e0e0;
            }
        """)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        self._root = QWidget()
        self._root.setObjectName("chatRoot")
        root_layout.addWidget(self._root)

        layout = QVBoxLayout(self._root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Title bar ---
        title_bar = QWidget()
        title_bar.setFixedHeight(42)
        title_bar.setStyleSheet("background-color: #FF6B9D; border-radius: 12px 12px 0 0;")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(14, 0, 10, 0)

        title_label = QLabel("千早爱音")
        title_label.setStyleSheet("color: white; font-size: 14px; font-weight: bold; border: none;")

        self._typing_label = QLabel("  对方正在输入...")
        self._typing_label.setStyleSheet("color: rgba(255,255,255,0.75); font-size: 12px; border: none;")
        self._typing_label.hide()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: white; font-size: 14px;
                border: none; border-radius: 13px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.3); }
        """)
        close_btn.clicked.connect(self.hide)

        title_layout.addWidget(title_label)
        title_layout.addWidget(self._typing_label)
        title_layout.addStretch()
        title_layout.addWidget(close_btn)

        # Make title bar draggable
        title_bar.mousePressEvent = self._title_press
        title_bar.mouseMoveEvent = self._title_drag

        # --- Message area ---
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("""
            QScrollArea { border: none; background: #f0f0f0; }
            QScrollBar:vertical { width: 4px; background: transparent; }
            QScrollBar::handle:vertical { background: #ccc; border-radius: 2px; }
        """)

        self._msg_container = QWidget()
        self._msg_layout = QVBoxLayout(self._msg_container)
        self._msg_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._msg_layout.setSpacing(8)
        self._msg_layout.setContentsMargins(12, 12, 12, 12)

        self._scroll.setWidget(self._msg_container)

        # --- Loading indicator ---
        self._loading = QLabel("正在思考...")
        self._loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loading.setStyleSheet("color: #999; font-size: 12px; padding: 6px; background: transparent;")
        self._loading.hide()

        # --- Input area ---
        input_widget = QWidget()
        input_widget.setStyleSheet("background: white; border-radius: 0 0 12px 12px;")
        input_layout = QHBoxLayout(input_widget)
        input_layout.setContentsMargins(8, 8, 8, 10)

        self._input = QLineEdit()
        self._input.setPlaceholderText("输入消息...")
        self._input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ddd; border-radius: 18px;
                padding: 8px 16px; font-size: 13px;
                background: #fafafa; min-height: 20px;
            }
            QLineEdit:focus { border-color: #FF6B9D; background: white; }
        """)

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
        layout.addWidget(title_bar)
        layout.addWidget(self._scroll)
        layout.addWidget(self._loading)
        layout.addWidget(input_widget)

        # --- Signals ---
        self._send_btn.clicked.connect(self._on_send)
        self._input.returnPressed.connect(self._on_send)

    # --- Title bar drag ---
    def _title_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()

    def _title_drag(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()

    # --- Send ---
    def _on_send(self):
        text = self._input.text().strip()
        if not text:
            return
        self._add_bubble(text, is_user=True)
        self._input.clear()
        self.message_sent.emit(text)
        self._set_loading(True)

    # --- Bubbles ---
    def _add_bubble(self, text: str, is_user: bool):
        bubble = QLabel(text)
        bubble.setWordWrap(True)
        bubble.setMaximumWidth(300)
        bubble.setStyleSheet(f"""
            background-color: {'#FF6B9D' if is_user else 'white'};
            color: {'white' if is_user else '#333'};
            border-radius: 12px;
            padding: 10px 14px;
            font-size: 13px;
            line-height: 1.4;
        """)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        if is_user:
            row.addStretch()
        row.addWidget(bubble)
        if not is_user:
            row.addStretch()

        self._msg_layout.addLayout(row)

        QTimer.singleShot(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        sb = self._scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _set_loading(self, active: bool):
        self._send_btn.setEnabled(not active)
        self._input.setEnabled(not active)
        self._loading.setVisible(active)
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
        parts = re.split(r'(?<=[。！？\n])', text)
        parts = [p.strip() for p in parts if p.strip()]
        MAX_LEN = 40
        result = []
        for part in parts:
            if len(part) <= MAX_LEN:
                result.append(part)
            else:
                sub = re.split(r'(?<=[，、；])', part)
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
