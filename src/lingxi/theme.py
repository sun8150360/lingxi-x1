from pathlib import Path

from PySide6.QtGui import QFontDatabase


def load_chinese_font() -> str:
    for path in (Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/msyhbd.ttc")):
        if path.exists():
            font_id = QFontDatabase.addApplicationFont(str(path))
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                return families[0]
    return "Microsoft YaHei UI"


LIQUID_GLASS_QSS = """
QWidget {
    color: #1D1D1F;
    font-family: "Microsoft YaHei UI";
    font-size: 13px;
}
QMainWindow { background: #F5F5F7; }
QFrame#glassCard {
    background-color: rgba(255, 255, 255, 178);
    border: 1px solid rgba(255, 255, 255, 235);
    border-radius: 22px;
}
QFrame#metricCard {
    background-color: rgba(255, 255, 255, 148);
    border: 1px solid rgba(255, 255, 255, 225);
    border-radius: 15px;
}
QLabel#appTitle { font-size: 22px; font-weight: 700; }
QLabel#appSubtitle { color: rgba(60, 60, 67, 165); font-size: 11px; }
QLabel#sectionTitle { color: rgba(29, 29, 31, 195); font-weight: 650; font-size: 12px; }
QLabel#metricValue { font-size: 20px; font-weight: 680; }
QLabel#metricCaption { color: rgba(60, 60, 67, 145); font-size: 10px; }
QPushButton, QComboBox, QDoubleSpinBox, QSpinBox {
    background-color: rgba(255, 255, 255, 150);
    border: 1px solid rgba(255, 255, 255, 225);
    border-radius: 11px;
    padding: 7px 10px;
    min-height: 18px;
}
QPushButton:hover, QComboBox:hover, QDoubleSpinBox:hover, QSpinBox:hover {
    background-color: rgba(255, 255, 255, 220);
    border-color: rgba(0, 122, 255, 105);
}
QPushButton:pressed { background-color: rgba(0, 122, 255, 55); }
QPushButton#roundStepper {
    min-width: 30px;
    max-width: 30px;
    min-height: 30px;
    max-height: 30px;
    padding: 0;
    border-radius: 15px;
    color: #007AFF;
    background-color: rgba(255, 255, 255, 205);
    border: 1px solid rgba(0, 122, 255, 55);
    font-size: 17px;
    font-weight: 600;
}
QPushButton#roundStepper:hover {
    color: white;
    background-color: rgba(0, 122, 255, 205);
    border-color: rgba(0, 122, 255, 210);
}
QPushButton#roundStepper:pressed { background-color: #0066D6; }
QPushButton#primaryButton {
    color: white;
    background-color: rgba(0, 122, 255, 225);
    border-color: rgba(255, 255, 255, 195);
    font-weight: 650;
}
QPushButton#primaryButton:hover { background-color: rgba(0, 113, 237, 245); }
QPushButton#dangerButton { background-color: rgba(255, 69, 85, 95); }
QComboBox::drop-down { border: 0; width: 24px; }
QComboBox QAbstractItemView {
    color: #1D1D1F;
    background: rgba(250, 250, 252, 245);
    border: 1px solid rgba(0, 0, 0, 25);
    selection-background-color: #3478F6;
    selection-color: white;
    border-radius: 8px;
}
QTabWidget::pane { border: 0; }
QTabBar::tab {
    background: transparent;
    color: rgba(60, 60, 67, 160);
    padding: 8px 18px;
    margin: 2px;
    border-radius: 10px;
}
QTabBar::tab:selected { background: rgba(255, 255, 255, 205); color: #007AFF; }
QCheckBox { spacing: 8px; }
QStatusBar { color: rgba(60, 60, 67, 175); background: rgba(255, 255, 255, 90); }
QToolTip { color: #1D1D1F; background: #FFFFFF; border: 1px solid #D4D4D8; }
"""
