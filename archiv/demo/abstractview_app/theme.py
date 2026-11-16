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
    # Odlišená barva pro zakliknutý Shuffle vs. vybraný efekt
    shuffle_bg: str = "#8B5CF6"
    shuffle_hover: str = "#A78BFA"
    shadow_color: str = "#070C17"


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
    play_bg="#E11D48",
    play_hover="#F43F5E",
    play_glow="#9F1239",
    play_text="#FFFFFF",
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
    shuffle_bg="#7C3AED",
    shuffle_hover="#8B5CF6",
    shadow_color="#080E1A",
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
    play_bg="#E11D48",
    play_hover="#F43F5E",
    play_glow="#9F1239",
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
    shuffle_bg="#6D28D9",
    shuffle_hover="#7C3AED",
    shadow_color="#CFC4B0",
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


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    clean = hex_str.lstrip("#")
    if len(clean) != 6:
        return (128, 128, 128)
    return (int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16))


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    r = max(0, min(255, round(rgb[0])))
    g = max(0, min(255, round(rgb[1])))
    b = max(0, min(255, round(rgb[2])))
    return f"#{r:02X}{g:02X}{b:02X}"


def lerp_rgb(
    c1: tuple[int, int, int], c2: tuple[int, int, int], t: float
) -> tuple[int, int, int]:
    alpha = max(0.0, min(1.0, float(t)))
    return (
        round(c1[0] + (c2[0] - c1[0]) * alpha),
        round(c1[1] + (c2[1] - c1[1]) * alpha),
        round(c1[2] + (c2[2] - c1[2]) * alpha),
    )


def lerp_hex(h1: str, h2: str, t: float) -> str:
    return rgb_to_hex(lerp_rgb(hex_to_rgb(h1), hex_to_rgb(h2), t))


def interpolate_palette(light_progress: float) -> ThemePalette:
    """Plynule prolne barvy mezi DARK_PALETTE (0.0) a LIGHT_PALETTE (1.0)."""
    t = max(0.0, min(1.0, float(light_progress)))
    if t <= 0.001:
        return DARK_PALETTE
    if t >= 0.999:
        return LIGHT_PALETTE
    d = DARK_PALETTE
    l = LIGHT_PALETTE

    def readable_text(dark_color: str, light_color: str) -> str:
        # Při lineárním prolínání by text uprostřed splýval se šedým panelem.
        if t < 0.5:
            return lerp_hex(d.text_primary, dark_color, 1.0 - 2.0 * t)
        return lerp_hex(l.text_primary, light_color, 2.0 * t - 1.0)

    return ThemePalette(
        name="light" if t >= 0.5 else "dark",
        bg_primary=lerp_hex(d.bg_primary, l.bg_primary, t),
        bg_card=lerp_hex(d.bg_card, l.bg_card, t),
        bg_elevated=lerp_hex(d.bg_elevated, l.bg_elevated, t),
        bg_hover=lerp_hex(d.bg_hover, l.bg_hover, t),
        accent=lerp_hex(d.accent, l.accent, t),
        accent_hover=lerp_hex(d.accent_hover, l.accent_hover, t),
        accent_text=lerp_hex(d.accent_text, l.accent_text, t),
        play_bg=lerp_hex(d.play_bg, l.play_bg, t),
        play_hover=lerp_hex(d.play_hover, l.play_hover, t),
        play_glow=lerp_hex(d.play_glow, l.play_glow, t),
        play_text=lerp_hex(d.play_text, l.play_text, t),
        text_primary=readable_text(d.text_primary, l.text_primary),
        text_secondary=readable_text(d.text_secondary, l.text_secondary),
        text_muted=readable_text(d.text_muted, l.text_muted),
        border=lerp_hex(d.border, l.border, t),
        border_focus=lerp_hex(d.border_focus, l.border_focus, t),
        danger=lerp_hex(d.danger, l.danger, t),
        danger_hover=lerp_hex(d.danger_hover, l.danger_hover, t),
        success=lerp_hex(d.success, l.success, t),
        badge_bg=lerp_hex(d.badge_bg, l.badge_bg, t),
        badge_text=readable_text(d.badge_text, l.badge_text),
        slider_track=lerp_hex(d.slider_track, l.slider_track, t),
        slider_fill=lerp_hex(d.slider_fill, l.slider_fill, t),
        slider_thumb=lerp_hex(d.slider_thumb, l.slider_thumb, t),
        slider_thumb_hover=lerp_hex(d.slider_thumb_hover, l.slider_thumb_hover, t),
        shuffle_bg=lerp_hex(d.shuffle_bg, l.shuffle_bg, t),
        shuffle_hover=lerp_hex(d.shuffle_hover, l.shuffle_hover, t),
        shadow_color=lerp_hex(d.shadow_color, l.shadow_color, t),
    )


def get_palette(mode: str) -> ThemePalette:
    """Vrátí paletu podle názvu režimu ('light' nebo 'dark')."""
    return PALETTES.get(mode, DARK_PALETTE)
