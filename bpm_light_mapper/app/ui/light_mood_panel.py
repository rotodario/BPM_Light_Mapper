from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout

from bpm_light_mapper.app.light_mood.mood_engine import LightMoodRecommendation
from bpm_light_mapper.app.ui.theme import COLORS


COLOR_SWATCHES = {
    "azul profundo": "#063C8C",
    "congo blue": "#24135F",
    "lavanda frio": "#9D9CFF",
    "ambar tungsteno": "#FFB347",
    "rojo profundo": "#A40F2B",
    "blanco frio": "#DCEEFF",
    "blanco calido": "#FFD7A0",
    "cyan": "#25D9FF",
    "verde lima": "#A2FF36",
    "magenta": "#FF4FD8",
    "CTB suave desde contra": "#7EB6FF",
    "contra azul saturado": "#1054D8",
    "contra abierto con lime accents": "#70EFFF",
    "contra calido suave": "#FFB36A",
}


class LightMoodPanel(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("LightMoodCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        self.mood_label = QLabel("Mood estimado")
        self.mood_label.setObjectName("LightMoodTitle")
        self.confidence_label = QLabel("Confianza: -")
        self.confidence_label.setObjectName("LightMoodMeta")
        self.explanation_label = QLabel("Analiza un archivo para generar una receta de iluminacion.")
        self.explanation_label.setWordWrap(True)
        self.explanation_label.setObjectName("LightMoodText")

        layout.addWidget(self.mood_label)
        layout.addWidget(self.confidence_label)
        layout.addWidget(self.explanation_label)

        palette_title = QLabel("PALETA DE LUZ")
        palette_title.setObjectName("PanelTitle")
        layout.addWidget(palette_title)
        self.palette_grid = QGridLayout()
        self.palette_grid.setHorizontalSpacing(8)
        self.palette_grid.setVerticalSpacing(6)
        layout.addLayout(self.palette_grid)

        self.base_value = self._add_palette_row(0, "Base")
        self.secondary_value = self._add_palette_row(1, "Secundario")
        self.backlight_value = self._add_palette_row(2, "Contraluz")
        self.front_value = self._add_palette_row(3, "Frontal")

        show_title = QLabel("PARAMETROS DE SHOW")
        show_title.setObjectName("PanelTitle")
        layout.addWidget(show_title)
        self.show_grid = QGridLayout()
        self.show_grid.setHorizontalSpacing(8)
        self.show_grid.setVerticalSpacing(5)
        layout.addLayout(self.show_grid)

        self.intensity_value = self._add_show_row(0, "Intensidad")
        self.movement_value = self._add_show_row(1, "Movimiento")
        self.fade_value = self._add_show_row(2, "Fade")
        self.strobe_value = self._add_show_row(3, "Strobe")
        self.atmosphere_value = self._add_show_row(4, "Ambiente")

        notes_title = QLabel("NOTAS OPERADOR")
        notes_title.setObjectName("PanelTitle")
        self.notes_label = QLabel("-")
        self.notes_label.setObjectName("LightMoodText")
        self.notes_label.setWordWrap(True)
        layout.addWidget(notes_title)
        layout.addWidget(self.notes_label)
        layout.addStretch(1)

    def reset(self) -> None:
        self.mood_label.setText("Mood estimado")
        self.confidence_label.setText("Confianza: -")
        self.explanation_label.setText("Analiza un archivo para generar una receta de iluminacion.")
        for label in [
            self.base_value,
            self.secondary_value,
            self.backlight_value,
            self.front_value,
        ]:
            label.setText("-")
            label.setStyleSheet("")
        for label in [
            self.intensity_value,
            self.movement_value,
            self.fade_value,
            self.strobe_value,
            self.atmosphere_value,
            self.notes_label,
        ]:
            label.setText("-")

    def set_recommendation(self, recommendation: LightMoodRecommendation) -> None:
        recipe = recommendation.recipe
        self.mood_label.setText(recommendation.mood.upper())
        self.confidence_label.setText(f"Confianza: {recommendation.confidence:.0%}")
        self.explanation_label.setText(recommendation.explanation)
        self._set_palette_value(self.base_value, recipe.base_color)
        self._set_palette_value(self.secondary_value, recipe.secondary_color)
        self._set_palette_value(self.backlight_value, recipe.backlight)
        self._set_palette_value(self.front_value, recipe.front)
        self.intensity_value.setText(recipe.intensity)
        self.movement_value.setText(recipe.movement_speed)
        self.fade_value.setText(recipe.fade_type)
        self.strobe_value.setText(recipe.strobe)
        self.atmosphere_value.setText(recipe.atmosphere)
        self.notes_label.setText(recipe.operator_notes)

    def _add_palette_row(self, row: int, title: str) -> QLabel:
        title_label = QLabel(title)
        title_label.setObjectName("LightMoodMeta")
        value_label = QLabel("-")
        value_label.setObjectName("LightMoodValue")
        value_label.setWordWrap(True)
        self.palette_grid.addWidget(title_label, row, 0)
        self.palette_grid.addWidget(value_label, row, 1)
        return value_label

    def _add_show_row(self, row: int, title: str) -> QLabel:
        title_label = QLabel(title)
        title_label.setObjectName("LightMoodMeta")
        value_label = QLabel("-")
        value_label.setObjectName("LightMoodValue")
        value_label.setWordWrap(True)
        self.show_grid.addWidget(title_label, row, 0)
        self.show_grid.addWidget(value_label, row, 1)
        return value_label

    def _set_palette_value(self, label: QLabel, value: str) -> None:
        swatch = COLOR_SWATCHES.get(value, COLORS["muted"])
        label.setText(value)
        label.setStyleSheet(
            "QLabel#LightMoodValue {"
            f"color: {COLORS['text']};"
            f"border-left: 10px solid {swatch};"
            "padding-left: 6px;"
            "}"
        )
