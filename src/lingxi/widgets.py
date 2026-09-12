from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap, QRadialGradient
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QLabel, QVBoxLayout, QWidget


class LiquidBackground(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._background_cache = QPixmap()

    def _rebuild_background(self) -> None:
        if self.width() <= 0 or self.height() <= 0:
            return
        cache = QPixmap(self.size())
        painter = QPainter(cache)
        painter.setRenderHint(QPainter.Antialiasing)
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.0, QColor("#F8FAFD"))
        gradient.setColorAt(0.48, QColor("#F5F5F7"))
        gradient.setColorAt(1.0, QColor("#EDF2F8"))
        painter.fillRect(cache.rect(), gradient)
        for cx, cy, radius, color in (
            (0.13, 0.08, 0.42, QColor(96, 165, 250, 72)),
            (0.87, 0.12, 0.36, QColor(191, 130, 255, 58)),
            (0.62, 0.94, 0.46, QColor(80, 220, 200, 46)),
            (0.40, 0.32, 0.24, QColor(255, 255, 255, 150)),
        ):
            radial = QRadialGradient(self.width() * cx, self.height() * cy, min(self.width(), self.height()) * radius)
            radial.setColorAt(0, color)
            radial.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))
            painter.fillRect(cache.rect(), radial)
        painter.end()
        self._background_cache = cache

    def resizeEvent(self, event) -> None:
        self._rebuild_background()
        super().resizeEvent(event)

    def paintEvent(self, event) -> None:
        if self._background_cache.size() != self.size():
            self._rebuild_background()
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._background_cache)


class GlassCard(QFrame):
    def __init__(self, parent=None, metric: bool = False) -> None:
        super().__init__(parent)
        self.setObjectName("metricCard" if metric else "glassCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        if not metric:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(24)
            shadow.setOffset(0, 6)
            shadow.setColor(QColor(38, 64, 96, 24))
            self.setGraphicsEffect(shadow)


class MetricCard(GlassCard):
    def __init__(self, caption: str, value: str = "—", parent=None) -> None:
        super().__init__(parent, metric=True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(1)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("metricValue")
        self.caption_label = QLabel(caption)
        self.caption_label.setObjectName("metricCaption")
        layout.addWidget(self.value_label)
        layout.addWidget(self.caption_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)
