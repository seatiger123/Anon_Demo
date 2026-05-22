import os

from PySide6.QtCore import Qt, Signal, QRect, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPixmap, QRegion, QPainter, QBrush, QColor, QFont, QPainterPath
from PySide6.QtWidgets import QWidget, QMenu


class FloatingWidget(QWidget):
    clicked = Signal()

    NORMAL_SIZE = 80
    HOVER_SIZE = 100

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_position = None
        self._press_position = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(self.NORMAL_SIZE, self.NORMAL_SIZE)

        self._original_pixmap = None
        self._cached_pixmap = None
        self._setup_icon()

        self._animation = QPropertyAnimation(self, b"geometry")
        self._animation.setDuration(150)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _setup_icon(self):
        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "resources", "icon.png"
        )
        if os.path.exists(icon_path):
            self._original_pixmap = QPixmap(icon_path)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Anti-aliased circular clip path — smooth edges
        path = QPainterPath()
        path.addEllipse(0, 0, self.width(), self.height())
        painter.setClipPath(path)

        # Background circle
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#FF6B9D"))
        painter.drawEllipse(self.rect())

        # Pixmap
        if self._original_pixmap is not None:
            if self._cached_pixmap is None:
                self._cached_pixmap = self._original_pixmap.scaled(
                    self.width(), self.height(),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation
                )
            x = (self.width() - self._cached_pixmap.width()) // 2
            y = (self.height() - self._cached_pixmap.height()) // 2
            painter.drawPixmap(x, y, self._cached_pixmap)
        else:
            # Fallback: draw text
            painter.setPen(QColor("white"))
            painter.setFont(QFont("sans-serif", 28, QFont.Weight.Bold))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "爱")

    def resizeEvent(self, event):
        self._cached_pixmap = None
        self.update()
        super().resizeEvent(event)

    def enterEvent(self, event):
        self._animate_to(self.HOVER_SIZE)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animate_to(self.NORMAL_SIZE)
        super().leaveEvent(event)

    def _animate_to(self, target_size):
        center = self.geometry().center()
        target_rect = QRect(0, 0, target_size, target_size)
        target_rect.moveCenter(center)

        # Clamp to screen bounds so the widget doesn't go off-screen
        screen = self.screen()
        if screen:
            sg = screen.availableGeometry()
            if target_rect.left() < sg.left():
                target_rect.moveLeft(sg.left())
            if target_rect.top() < sg.top():
                target_rect.moveTop(sg.top())
            if target_rect.right() > sg.right():
                target_rect.moveRight(sg.right())
            if target_rect.bottom() > sg.bottom():
                target_rect.moveBottom(sg.bottom())

        self._animation.stop()
        self._animation.setStartValue(self.geometry())
        self._animation.setEndValue(target_rect)
        self._animation.start()

    def contextMenuEvent(self, event):
        # Only respond to right-clicks within the circular area
        hit_region = QRegion(QRect(0, 0, self.width(), self.height()),
                             QRegion.RegionType.Ellipse)
        if not hit_region.contains(self.mapFromGlobal(event.globalPos())):
            event.ignore()
            return

        menu = QMenu(self)
        quit_action = menu.addAction("退出")
        quit_action.triggered.connect(self._quit_app)
        menu.exec(event.globalPos())

    def _quit_app(self):
        from PySide6.QtWidgets import QApplication
        QApplication.quit()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Only respond to clicks within the circular area
            hit_region = QRegion(QRect(0, 0, self.width(), self.height()),
                                 QRegion.RegionType.Ellipse)
            if not hit_region.contains(event.position().toPoint()):
                event.ignore()
                return

            self._drag_position = event.globalPosition().toPoint()
            self._press_position = event.globalPosition().toPoint()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_position:
            delta = event.globalPosition().toPoint() - self._drag_position
            self.move(self.pos() + delta)
            self._drag_position = event.globalPosition().toPoint()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._press_position:
            distance = (event.globalPosition().toPoint() - self._press_position).manhattanLength()
            if distance < 10:
                self.clicked.emit()
            self._drag_position = None
            self._press_position = None
            event.accept()
