from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LightingRecipe:
    base_color: str
    secondary_color: str
    backlight: str
    front: str
    intensity: str
    movement_speed: str
    fade_type: str
    strobe: str
    atmosphere: str
    operator_notes: str


RECIPES: dict[str, LightingRecipe] = {
    "Calm": LightingRecipe(
        base_color="azul profundo",
        secondary_color="lavanda frio",
        backlight="CTB suave desde contra",
        front="blanco calido bajo",
        intensity="25-40%",
        movement_speed="muy lenta",
        fade_type="fade largo y continuo",
        strobe="no",
        atmosphere="humo fino",
        operator_notes="Mantener sombras abiertas y evitar cambios bruscos.",
    ),
    "Dark": LightingRecipe(
        base_color="congo blue",
        secondary_color="rojo profundo",
        backlight="contra azul saturado",
        front="frontal minimo, recorte frio",
        intensity="30-55%",
        movement_speed="lenta",
        fade_type="fade medio con blackout parcial",
        strobe="no, salvo golpes puntuales",
        atmosphere="humo denso controlado",
        operator_notes="Priorizar siluetas y volumen, no banar toda la escena.",
    ),
    "Epic": LightingRecipe(
        base_color="blanco frio",
        secondary_color="azul profundo",
        backlight="contraluz ancho con beams",
        front="blanco calido moderado",
        intensity="70-90%",
        movement_speed="media con barridos amplios",
        fade_type="fade progresivo con lifts",
        strobe="solo en climax",
        atmosphere="haze uniforme",
        operator_notes="Construir capas: wash base, contra fuerte y aperturas en golpes grandes.",
    ),
    "Aggressive": LightingRecipe(
        base_color="rojo profundo",
        secondary_color="blanco frio",
        backlight="contra duro y recortado",
        front="frontal bajo, alto contraste",
        intensity="80-100%",
        movement_speed="rapida",
        fade_type="cuts y fades cortos",
        strobe="si, sincronizado a golpes fuertes",
        atmosphere="haze medio",
        operator_notes="Usar blancos como impactos, no como wash permanente.",
    ),
    "Euphoric": LightingRecipe(
        base_color="cyan",
        secondary_color="magenta",
        backlight="contra abierto con lime accents",
        front="blanco frio limpio",
        intensity="75-100%",
        movement_speed="media-rapida",
        fade_type="chases suaves y bumps",
        strobe="opcional en drops",
        atmosphere="haze uniforme",
        operator_notes="Alternar cyan/magenta y abrir blancos en coros o drops.",
    ),
    "Romantic": LightingRecipe(
        base_color="ambar tungsteno",
        secondary_color="lavanda frio",
        backlight="contra calido suave",
        front="blanco calido / CTO",
        intensity="35-60%",
        movement_speed="muy lenta",
        fade_type="fade largo",
        strobe="no",
        atmosphere="humo fino",
        operator_notes="Cuidar pieles con CTO y usar lavanda como separacion.",
    ),
    "Tension": LightingRecipe(
        base_color="congo blue",
        secondary_color="verde lima",
        backlight="contra estrecho con sombras",
        front="frontal frio bajo",
        intensity="45-70%",
        movement_speed="lenta con pequenos movimientos",
        fade_type="fade escalonado",
        strobe="no, usar bumps secos",
        atmosphere="haze visible",
        operator_notes="Crear incomodidad con contraste frio y acentos verdes cortos.",
    ),
    "Groove": LightingRecipe(
        base_color="ambar tungsteno",
        secondary_color="cyan",
        backlight="contra calido con side light",
        front="blanco calido moderado",
        intensity="55-80%",
        movement_speed="media, ligada al pulso",
        fade_type="fade corto con swing",
        strobe="no",
        atmosphere="haze ligero",
        operator_notes="Marcar negras y contratiempos con side light, sin sobrecargar.",
    ),
    "Minimal": LightingRecipe(
        base_color="blanco frio",
        secondary_color="azul profundo",
        backlight="lineas limpias desde contra",
        front="frontal muy bajo",
        intensity="20-45%",
        movement_speed="estatica o muy lenta",
        fade_type="fade largo o snaps aislados",
        strobe="no",
        atmosphere="haze muy fino",
        operator_notes="Pocas fuentes, posiciones claras y cambios muy intencionados.",
    ),
    "Dramatic": LightingRecipe(
        base_color="rojo profundo",
        secondary_color="lavanda frio",
        backlight="contra alto con silueta",
        front="blanco calido lateral",
        intensity="55-85%",
        movement_speed="lenta-media",
        fade_type="fades teatrales",
        strobe="no, reservar para acentos extremos",
        atmosphere="humo medio",
        operator_notes="Jugar con claroscuros y cambios de foco, no con velocidad constante.",
    ),
}


def recipe_for_mood(mood: str) -> LightingRecipe:
    return RECIPES.get(mood, RECIPES["Groove"])
