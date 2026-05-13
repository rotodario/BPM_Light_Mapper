from __future__ import annotations

from PySide6.QtWidgets import QApplication


COLORS = {
    "bg": "#070D13",
    "panel": "#0B121A",
    "panel_alt": "#101A24",
    "panel_edge": "#1E3447",
    "text": "#EAF4FF",
    "muted": "#8EA6BA",
    "cyan": "#25D9FF",
    "cyan_dim": "#00D9FF",
    "green": "#41F078",
    "yellow": "#FFD447",
    "orange": "#FF9F43",
    "red": "#FF4D6D",
    "blue": "#4DA3FF",
    "purple": "#B18CFF",
    "lime": "#A2FF36",
}


GLOBAL_QSS = f"""
* {{
    font-family: "Segoe UI", "IBM Plex Sans", "Arial";
    color: {COLORS["text"]};
    font-size: 12px;
}}

QMainWindow, QWidget#Root {{
    background: {COLORS["bg"]};
}}

QFrame#AppHeader {{
    background: {COLORS["panel"]};
    border: 1px solid {COLORS["panel_edge"]};
    border-radius: 8px;
}}

QFrame#SectionPanel, QFrame#MetricCard, QFrame#TimingGrid {{
    background: {COLORS["panel"]};
    border: 1px solid {COLORS["panel_edge"]};
    border-radius: 8px;
}}

QFrame#SectionPanel:hover, QFrame#MetricCard:hover {{
    border-color: #2b4c66;
}}

QLabel#AppTitle {{
    color: {COLORS["text"]};
    font-size: 24px;
    font-weight: 800;
}}

QLabel#AppSubtitle {{
    color: {COLORS["cyan"]};
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 0px;
}}

QLabel#HeaderMeta, QLabel#PanelTitle, QLabel#MetricTitle, QLabel#MetricSubtitle {{
    color: {COLORS["muted"]};
}}

QLabel#PanelTitle {{
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0px;
    text-transform: uppercase;
}}

QLabel#MetricValue {{
    color: {COLORS["cyan"]};
    font-size: 30px;
    font-weight: 900;
}}

QLabel#MetricValueSmall {{
    color: {COLORS["text"]};
    font-size: 18px;
    font-weight: 800;
}}

QLabel#StatusBadge {{
    border-radius: 6px;
    padding: 5px 10px;
    font-weight: 900;
    font-size: 12px;
    color: #061015;
    background: {COLORS["muted"]};
}}

QPushButton {{
    background: #111C27;
    border: 1px solid #284257;
    border-radius: 6px;
    padding: 8px 12px;
    font-weight: 700;
}}

QPushButton:hover {{
    background: #172A39;
    border-color: {COLORS["cyan_dim"]};
}}

QPushButton:pressed {{
    background: #0A151E;
}}

QPushButton:disabled {{
    color: #5a6875;
    background: #0A1118;
    border-color: #162736;
}}

QPushButton[role="primary"] {{
    background: #0D3A46;
    border-color: {COLORS["cyan_dim"]};
    color: {COLORS["text"]};
}}

QPushButton[role="danger"] {{
    background: #401822;
    border-color: #7d263b;
}}

QPushButton::menu-indicator {{
    image: none;
    width: 0px;
}}

QMenu {{
    background: {COLORS["panel_alt"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["panel_edge"]};
    border-radius: 7px;
    padding: 6px;
}}

QMenu::item {{
    background: transparent;
    color: {COLORS["text"]};
    padding: 8px 24px 8px 12px;
    border-radius: 5px;
}}

QMenu::item:selected {{
    background: #103B4A;
    color: {COLORS["cyan"]};
}}

QMenu::item:disabled {{
    color: #5a6875;
}}

QGroupBox {{
    background: {COLORS["panel"]};
    border: 1px solid {COLORS["panel_edge"]};
    border-radius: 8px;
    margin-top: 14px;
    padding: 12px 10px 10px 10px;
    font-weight: 800;
    color: {COLORS["muted"]};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}}

QTabWidget::pane {{
    border: 1px solid {COLORS["panel_edge"]};
    background: {COLORS["bg"]};
    border-radius: 8px;
}}

QTabBar::tab {{
    background: #0b1118;
    border: 1px solid #1c2b3a;
    padding: 9px 16px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    color: {COLORS["muted"]};
    font-weight: 800;
}}

QTabBar::tab:selected {{
    background: {COLORS["panel_alt"]};
    color: {COLORS["cyan"]};
    border-color: {COLORS["cyan_dim"]};
}}

QTableWidget {{
    background: #071018;
    viewport-background-color: #071018;
    alternate-background-color: #0C1620;
    gridline-color: #1C3041;
    border: 1px solid {COLORS["panel_edge"]};
    border-radius: 8px;
    selection-background-color: #103B4A;
    selection-color: {COLORS["text"]};
}}

QHeaderView {{
    background: #101a24;
}}

QHeaderView::section {{
    background: #101a24;
    color: {COLORS["muted"]};
    border: 0;
    border-right: 1px solid #1e2c3a;
    padding: 8px;
    font-weight: 900;
}}

QTableCornerButton::section {{
    background: #101a24;
    border: 0;
    border-right: 1px solid #1e2c3a;
    border-bottom: 1px solid #1e2c3a;
}}

QPlainTextEdit {{
    background: #05080c;
    border: 1px solid #172331;
    border-radius: 8px;
    color: #8ecfe0;
    font-family: "Cascadia Mono", "Consolas";
    font-size: 11px;
}}

QProgressBar {{
    background: #091018;
    border: 1px solid {COLORS["panel_edge"]};
    border-radius: 5px;
    height: 8px;
    text-align: center;
}}

QProgressBar::chunk {{
    background: {COLORS["cyan"]};
    border-radius: 5px;
}}

QComboBox, QDoubleSpinBox {{
    background: #0b121a;
    border: 1px solid #26394c;
    border-radius: 6px;
    padding: 6px 8px;
    color: {COLORS["text"]};
}}

QComboBox::drop-down {{
    border: 0;
    width: 22px;
}}

QComboBox QAbstractItemView {{
    background: {COLORS["panel_alt"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["panel_edge"]};
    selection-background-color: #123647;
    selection-color: {COLORS["cyan"]};
    outline: 0;
}}

QComboBox QAbstractItemView::item {{
    min-height: 28px;
    padding: 6px 8px;
}}

QSplitter::handle {{
    background: #142130;
}}

QScrollBar:vertical, QScrollBar:horizontal {{
    background: #070b10;
    border: 0;
    width: 10px;
    height: 10px;
}}

QScrollBar::handle {{
    background: #26394c;
    border-radius: 5px;
}}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyleSheet(GLOBAL_QSS)
