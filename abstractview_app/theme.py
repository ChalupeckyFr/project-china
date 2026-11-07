"""Centralizovaný grafický styl aplikace AbstractView.

Tento modul slouží jako jediný zdroj pravdy pro barvy, typografii, rozestupy
a předvolby barev. Pokud jiný návrhář nebo člen týmu potřebuje upravit vzhled
aplikace, stačí změnit hodnoty v tomto souboru.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ThemePalette:
    """Barevná paleta pro jeden vizuální režim (light nebo dark)."""

    name: str
    # Hlavní pozadí okna (dark = tmavě modrá, light = příjemná béžová)
    bg_primary: str
    # Pozadí karet a panelů
    bg_card: str
    # Pozadí vnořených prvků (vstupy, plátna, neaktivní tlačítka)
    bg_elevated: str
    # Barva při najetí myší (hover)
    bg_hover: str
    # Aktivní / vybraný prvek
    accent: str
    accent_hover: str
    accent_text: str
    # Hero tlačítko pro spuštění výstupu
    play_bg: str
    play_hover: str
    play_glow: str
    play_text: str
    # Texty
    text_primary: str
    text_secondary: str
    text_muted: str
    # Okraje a oddělovače
    border: str
    border_focus: str
    # Stavové barvy
    danger: str
    danger_hover: str
    success: str
    badge_bg: str
    badge_text: str
    # Posuvníky
    slider_track: str
    slider_fill: str
    slider_thumb: str
    slider_thumb_hover: str


# Tmavý režim ("dark") – není přímo černý, ale klidná tmavě modrá
DARK_PALETTE = ThemePalette(
    name="dark",
    bg_primary="#0E1729",
    bg_card="#15223B",
    bg_elevated="#1D2E4F",
    bg_hover="#273D66",
    accent="#3B82F6",
    accent_hover="#60A5FA",
    accent_text="#FFFFFF",
    play_bg="#10B981",
    play_hover="#34D399",
    play_glow="#059669",
    play_text="#06281E",
    text_primary="#F0F5FF",
    text_secondary="#B8C7E0",
    text_muted="#7E92B5",
    border="#293E66",
    border_focus="#60A5FA",
    danger="#EF4444",
    danger_hover="#F87171",
    success="#22C55E",
    badge_bg="#233559",
    badge_text="#93C5FD",
    slider_track="#243759",
    slider_fill="#3B82F6",
    slider_thumb="#E2EEFF",
    slider_thumb_hover="#FFFFFF",
)

# Světlý režim ("light") – jemná béžová, příjemná pro oči
LIGHT_PALETTE = ThemePalette(
    name="light",
    bg_primary="#F4EFE6",
    bg_card="#EAE2D3",
    bg_elevated="#DFD5C3",
    bg_hover="#D2C5AE",
    accent="#2563EB",
    accent_hover="#1D4ED8",
    accent_text="#FFFFFF",
    play_bg="#0D9488",
    play_hover="#0F766E",
    play_glow="#14B8A6",
    play_text="#FFFFFF",
    text_primary="#221E18",
    text_secondary="#52493C",
    text_muted="#7D7160",
    border="#C8BCA6",
    border_focus="#2563EB",
    danger="#DC2626",
    danger_hover="#B91C1C",
    success="#16A34A",
    badge_bg="#D8CEBC",
    badge_text="#3B3328",
    slider_track="#C9BDA8",
    slider_fill="#2563EB",
    slider_thumb="#221E18",
    slider_thumb_hover="#000000",
)

PALETTES: dict[str, ThemePalette] = {
    "dark": DARK_PALETTE,
    "light": LIGHT_PALETTE,
}


@dataclass(frozen=True)
class PresetColor:
    """Předdefinovaný odstín pro barvení objektů a graffiti."""

    key: str
    label: str
    hex_code: str
    rgb: tuple[int, int, int]


PRESET_COLORS: tuple[PresetColor, ...] = (
    PresetColor("red", "Červená", "#EF4444", (239, 68, 68)),
    PresetColor("pink", "Růžová", "#EC4899", (236, 72, 153)),
    PresetColor("purple", "Fialová", "#A855F7", (168, 85, 247)),
    PresetColor("dark_blue", "Tmavě modrá", "#1D4ED8", (29, 78, 216)),
    PresetColor("light_blue", "Světle modrá", "#38BDF8", (56, 189, 248)),
    PresetColor("dark_green", "Tmavě zelená", "#15803D", (21, 128, 61)),
    PresetColor("light_green", "Světle zelená", "#4ADE80", (74, 222, 128)),
    PresetColor("yellow", "Žlutá", "#FACC15", (250, 204, 21)),
    PresetColor("orange", "Oranžová", "#FB923C", (251, 146, 60)),
    PresetColor("white", "Bílá", "#F8FAFC", (248, 250, 252)),
)

PRESET_COLOR_MAP: dict[str, PresetColor] = {c.key: c for c in PRESET_COLORS}


@dataclass(frozen=True)
class LayoutMetrics:
    """Rozměrové konstanty pro dynamické rozložení a typografii."""

    font_family: str = "Segoe UI"
    font_size_title: int = 15
    font_size_section: int = 12
    font_size_body: int = 10
    font_size_small: int = 9
    card_padding: int = 14
    card_radius: int = 12
    button_radius: int = 8
    compact_breakpoint: int = 860
    min_window_width: int = 560
    min_window_height: int = 460
    default_window_width: int = 1100
    default_window_height: int = 800


METRICS = LayoutMetrics()


def get_palette(mode: str) -> ThemePalette:
    """Vrátí paletu podle názvu režimu ('light' nebo 'dark')."""
    return PALETTES.get(mode, DARK_PALETTE)
