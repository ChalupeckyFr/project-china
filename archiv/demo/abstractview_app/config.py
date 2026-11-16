"""Správa nastavení aplikace AbstractView, perzistence a logika shuffle."""

from __future__ import annotations

import copy
import json
import random
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from abstractview_app.theme import PRESET_COLOR_MAP

# Definice dostupných efektů
SHAPE_EFFECTS: tuple[tuple[str, str], ...] = (
    ("stars", "Hvězdný obrys"),
    ("nebula", "Polární prach"),
)

OBJECT_EFFECTS: tuple[tuple[str, str], ...] = (
    ("rings", "Prstence tvarů"),
)

ALL_EFFECT_KEYS: tuple[str, ...] = tuple(
    k for k, _ in (*SHAPE_EFFECTS, *OBJECT_EFFECTS)
)

BODY_PARTS: tuple[tuple[str, str, str], ...] = (
    ("head", "Hlava", "Zaoblené koule"),
    ("torso", "Trup (V-tvar)", "Otočené jehlany"),
    ("arms", "Ruce", "Zaoblené válce"),
    ("legs", "Nohy", "Zaoblené kvádry"),
)

PATTERN_STYLES: tuple[tuple[str, str], ...] = (
    ("solid", "Čistá barva"),
    ("brush", "Tahy štětcem"),
    ("spiral", "Spirála"),
    ("dots", "Tečky"),
    ("graffiti", "Graffiti"),
)

GRAFFITI_UNLOCK_SIZE: int = 60


def default_part_colors() -> dict[str, dict[str, str]]:
    return {
        "head": {"primary": "light_blue", "secondary": "white"},
        "torso": {"primary": "purple", "secondary": "pink"},
        "arms": {"primary": "light_green", "secondary": "yellow"},
        "legs": {"primary": "orange", "secondary": "red"},
    }


@dataclass
class AppSettings:
    """Veškerá nastavení aplikace s definovanými 'prvními hodnotami' (výchozí stav)."""

    # Vzhled aplikace: 'dark' (tmavě modrá) nebo 'light' (béžová)
    theme_mode: str = "dark"

    # Zdroj dat: 'sample' (3 ukázkové pózy), 'csv' (vlastní soubor), 'camera' (kamera)
    source_type: str = "sample"
    sample_id: str = "pose_raise"
    csv_path: str = ""
    camera_port: int = 0

    # Výběr efektu a shuffle
    active_effect: str = "stars"
    shape_shuffle: bool = False
    object_shuffle: bool = False
    open_panels: list[str] = field(default_factory=list)
    panel_positions: dict[str, list[float]] = field(default_factory=dict)
    window_geometry: str = ""
    window_state: str = "normal"

    # Nastavení shuffle (sdílené mezi tvarovými a objektovými efekty)
    # První hodnota: 60s (1 min), rozsah 15s až 300s (5 min)
    shuffle_interval_s: int = 60
    # První hodnota: 1.0s, rozsah 0.0s až 5.0s
    shuffle_transition_s: float = 1.0
    # Pořadí: 'normal' (první hodnota), 'random', 'custom'
    shuffle_order: str = "normal"
    custom_enabled_effects: list[str] = field(
        default_factory=lambda: list(ALL_EFFECT_KEYS)
    )

    # Nastavení tvarových efektů
    # Gravitace obrysu: 0 = jen hvězdné nebe, 100 = jen obrys těla na černé, první hodnota = 20
    gravity: int = 20
    # Počet objektů/hvězd v obraze: 0 až 2500, první hodnota = 600
    star_count: int = 600
    # Specifická nastavení tvarových efektů
    shooting_stars_freq: int = 25
    twinkle_speed: int = 40
    nebula_swirl: int = 45
    nebula_color: str = "light_blue"

    # Nastavení objektového efektu (Prstence tvarů)
    # Rychlost začíná na 0 (stojí na místě) až 100 (rychle obíhají)
    orbit_speed: int = 0
    # Velikost tvarů (10 až 100), určuje i počet tvarů; od 60 odemyká Graffiti
    shape_size: int = 35
    # Barvy: 'global' (společná) nebo 'per_part' (pokročilé po částech těla)
    color_mode: str = "global"
    primary_color: str = "light_blue"
    secondary_color: str = "white"
    part_colors: dict[str, dict[str, str]] = field(
        default_factory=default_part_colors
    )
    # Styl vzoru: 'solid', 'brush', 'spiral', 'dots', 'graffiti'
    pattern_style: str = "solid"

    # Graffiti kreslicí plátno
    graffiti_brush_color: str = "red"
    graffiti_eraser: bool = False
    graffiti_brush_size: int = 8
    # Uložené tahy: seznam slovníků {"color": str, "eraser": bool, "size": int, "points": [[x, y], ...]}
    graffiti_strokes: list[dict[str, Any]] = field(default_factory=list)

    def validate(self) -> None:
        """Ošetří hranice všech hodnot, aby nikdy nevznikla chyba."""
        if self.theme_mode not in ("dark", "light"):
            self.theme_mode = "dark"
        if self.source_type not in ("sample", "csv", "camera"):
            self.source_type = "sample"
        if self.sample_id not in ("pose_calm", "pose_spread", "pose_raise"):
            self.sample_id = "pose_raise"
        if self.active_effect not in ALL_EFFECT_KEYS:
            self.active_effect = "stars"
        panel_ids = ("shape", "object", "shuffle")
        self.open_panels = [
            key for key in dict.fromkeys(
                key for key in self.open_panels if isinstance(key, str)
            ) if key in panel_ids
        ] if isinstance(self.open_panels, list) else []
        if not isinstance(self.panel_positions, dict):
            self.panel_positions = {}
        clean_positions: dict[str, list[float]] = {}
        for key in panel_ids:
            value = self.panel_positions.get(key)
            if isinstance(value, list) and len(value) == 2:
                try:
                    clean_positions[key] = [
                        round(max(0.0, min(1.0, float(value[0]))), 4),
                        round(max(0.0, min(1.0, float(value[1]))), 4),
                    ]
                except (TypeError, ValueError):
                    pass
        self.panel_positions = clean_positions
        if not isinstance(self.window_geometry, str) or len(self.window_geometry) > 80:
            self.window_geometry = ""
        if self.window_state not in ("normal", "zoomed", "fullscreen"):
            self.window_state = "normal"

        self.shuffle_interval_s = int(max(15, min(300, self.shuffle_interval_s)))
        self.shuffle_transition_s = float(
            round(max(0.0, min(5.0, float(self.shuffle_transition_s))), 2)
        )
        if self.shuffle_order not in ("normal", "random", "custom"):
            self.shuffle_order = "normal"

        valid_custom = [
            k for k in self.custom_enabled_effects if k in ALL_EFFECT_KEYS
        ]
        self.custom_enabled_effects = (
            valid_custom if valid_custom else list(ALL_EFFECT_KEYS)
        )

        self.gravity = int(max(0, min(100, self.gravity)))
        self.star_count = int(max(0, min(2500, self.star_count)))
        self.shooting_stars_freq = int(max(0, min(100, self.shooting_stars_freq)))
        self.twinkle_speed = int(max(0, min(100, self.twinkle_speed)))
        self.nebula_swirl = int(max(0, min(100, self.nebula_swirl)))
        if self.nebula_color not in PRESET_COLOR_MAP:
            self.nebula_color = "light_blue"

        self.orbit_speed = int(max(0, min(100, self.orbit_speed)))
        self.shape_size = int(max(10, min(100, self.shape_size)))
        if self.color_mode not in ("global", "per_part"):
            self.color_mode = "global"
        if self.primary_color not in PRESET_COLOR_MAP:
            self.primary_color = "light_blue"
        if self.secondary_color not in PRESET_COLOR_MAP:
            self.secondary_color = "white"

        defaults = default_part_colors()
        cleaned_parts: dict[str, dict[str, str]] = {}
        for part_key, _, _ in BODY_PARTS:
            entry = self.part_colors.get(part_key, defaults[part_key])
            prim = entry.get("primary", defaults[part_key]["primary"])
            sec = entry.get("secondary", defaults[part_key]["secondary"])
            if prim not in PRESET_COLOR_MAP:
                prim = defaults[part_key]["primary"]
            if sec not in PRESET_COLOR_MAP:
                sec = defaults[part_key]["secondary"]
            cleaned_parts[part_key] = {"primary": prim, "secondary": sec}
        self.part_colors = cleaned_parts

        valid_styles = {k for k, _ in PATTERN_STYLES}
        if self.pattern_style not in valid_styles:
            self.pattern_style = "solid"
        if (
            self.pattern_style == "graffiti"
            and not self.is_graffiti_unlocked
        ):
            self.pattern_style = "solid"

        if self.graffiti_brush_color not in PRESET_COLOR_MAP:
            self.graffiti_brush_color = "red"
        self.graffiti_brush_size = int(max(2, min(28, self.graffiti_brush_size)))

    @property
    def is_graffiti_unlocked(self) -> bool:
        """Graffiti režim se odemkne, když jsou tvary dostatečně zvětšené."""
        return self.shape_size >= GRAFFITI_UNLOCK_SIZE

    @property
    def uses_secondary_color(self) -> bool:
        return self.pattern_style in ("brush", "spiral", "dots")

    @property
    def show_graffiti_editor(self) -> bool:
        return self.pattern_style == "graffiti" and self.is_graffiti_unlocked

    @property
    def computed_shape_count(self) -> int:
        """Počet tvarů v prstencích nepřímo úměrný jejich velikosti.

        Malé tvary (velikost 10) -> 88 tvarů.
        Velké tvary (velikost 100) -> 16 tvarů.
        """
        ratio = (self.shape_size - 10) / 90.0
        return max(12, round(88 - ratio * 72))


def default_config_path() -> Path:
    """Vrátí cestu k souboru s uloženým nastavením vedle aplikace."""
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(__file__).resolve().parent.parent
    return base / "abstractview_settings.json"


class SettingsStore:
    """Načítání, ukládání a resetování nastavení aplikace."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path is not None else default_config_path()
        self.settings = self.load()

    def load(self) -> AppSettings:
        if not self.path.exists():
            settings = AppSettings()
            settings.validate()
            return settings
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return AppSettings()
            defaults = asdict(AppSettings())
            merged = {**defaults, **{k: v for k, v in raw.items() if k in defaults}}
            settings = AppSettings(**merged)
            settings.validate()
            return settings
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return AppSettings()

    def save(self) -> None:
        self.settings.validate()
        try:
            self.path.write_text(
                json.dumps(asdict(self.settings), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass

    def reset_to_defaults(self) -> AppSettings:
        """Vrátí všechna nastavení na jejich první hodnotu a uloží."""
        self.settings = AppSettings()
        self.settings.validate()
        self.save()
        return self.settings


class ShuffleScheduler:
    """Řídí střídání efektů pro režimy 'normal', 'random' a 'custom'.

    - 'normal': přehrává efekty postupně tak, jak jdou za sebou.
    - 'random': náhodné pořadí bez opakování – nejprve projdou všechny
      aktivní efekty v cyklu, než se může jakýkoliv opakovat, a na hranici
      dvou cyklů se nikdy nezopakuje stejný efekt dvakrát po sobě.
    - 'custom': střídá pouze efekty povolené uživatelem.
    - Pokud je zapnutý shuffle tvarových i objektových efektů zároveň,
      míchají se ve společné frontě.
    """

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self._queue: list[str] = []
        self._last_signature: tuple[Any, ...] | None = None
        self._current_index: int = 0
        self._cycle_Anchor_s: float = 0.0

    def active_pool(self, settings: AppSettings) -> list[str]:
        """Sestaví seznam efektů zařazených do fronty."""
        pool: list[str] = []
        if settings.shape_shuffle:
            pool.extend(k for k, _ in SHAPE_EFFECTS)
        if settings.object_shuffle:
            pool.extend(k for k, _ in OBJECT_EFFECTS)

        if not pool:
            return [settings.active_effect]

        if settings.shuffle_order == "custom":
            filtered = [k for k in pool if k in settings.custom_enabled_effects]
            if filtered:
                pool = filtered

        return pool

    def generate_random_bag(
        self, pool: list[str], last_effect: str | None = None
    ) -> list[str]:
        """Vygeneruje jednu permutaci všech efektů v poolu bez duplicit.

        Pokud má pool alespoň 2 prvky a první prvek by byl shodný s posledním
        přehraným efektem z předchozího kola, prohodí jej s jiným prvkem.
        """
        bag = list(pool)
        self._rng.shuffle(bag)
        if len(bag) > 1 and last_effect is not None and bag[0] == last_effect:
            swap_idx = self._rng.randint(1, len(bag) - 1)
            bag[0], bag[swap_idx] = bag[swap_idx], bag[0]
        return bag

    def _ensure_queue(self, settings: AppSettings, needed_index: int) -> None:
        pool = self.active_pool(settings)
        signature = (
            tuple(pool),
            settings.shuffle_order,
            settings.shape_shuffle,
            settings.object_shuffle,
        )
        if signature != self._last_signature:
            self._last_signature = signature
            self._queue.clear()

        while len(self._queue) <= needed_index + 2:
            if settings.shuffle_order == "random":
                last_item = self._queue[-1] if self._queue else None
                self._queue.extend(self.generate_random_bag(pool, last_item))
            else:
                self._queue.extend(copy.copy(pool))

    def state_at(
        self, settings: AppSettings, elapsed_s: float
    ) -> tuple[str, str | None, float]:
        """Vrátí (aktuální_efekt, následující_efekt, alpha_přechodu 0..1)."""
        if not (settings.shape_shuffle or settings.object_shuffle):
            return settings.active_effect, None, 0.0

        pool = self.active_pool(settings)
        if len(pool) <= 1:
            only = pool[0] if pool else settings.active_effect
            return only, None, 0.0

        interval = max(15.0, float(settings.shuffle_interval_s))
        transition = min(
            max(0.0, float(settings.shuffle_transition_s)), interval * 0.45
        )
        step_index = max(0, int(elapsed_s // interval))
        in_step_s = elapsed_s - step_index * interval

        self._ensure_queue(settings, step_index + 1)
        current_effect = self._queue[step_index]
        next_effect = self._queue[step_index + 1]

        if transition <= 1e-6 or in_step_s < (interval - transition):
            return current_effect, None, 0.0

        alpha = (in_step_s - (interval - transition)) / transition
        alpha = max(0.0, min(1.0, alpha))
        # Smoothstep pro plynulé prolínání
        smooth_alpha = alpha * alpha * (3.0 - 2.0 * alpha)
        return current_effect, next_effect, smooth_alpha
