# Kreslení snímku, který později přijde z kamery. Spouští se samo, ne ze spustit.py.
import json
import tkinter as tk
from pathlib import Path

import numpy as np

# Bez toho Windows okno roztáhne a body jsou kostrbaté.
try:
    import ctypes

    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


# --- Rozměry a barvy -------------------------------------------------------

# Stejná mřížka, jakou posílá Arducam ToF. Jeden bod je jedno místo v prostoru.
WIDTH = 240
HEIGHT = 180
# Nevybarvené místo je daleko. Vybarvené je člověk, jeho vzdálenost se dá přepsat.
FAR_MM = 4000
NEAR_START = 1200
# 30 snímků za sekundu je mezera 33 ms.
INTERVAL_START = 33

TITLE = "simulate"
SIZE = "1100x760"
WINDOW_BG = "#ececec"
PANEL_BG = "#f7f7f7"
# Daleko je světle šedá, předloha světle modrá, nový tah černý.
FAR_COLOR = (214, 214, 214)
GUIDE_COLOR = (186, 216, 245)
INK_COLOR = (0, 0, 0)
GAP_COLOR = (236, 236, 236)


# --- Okno ------------------------------------------------------------------

window = tk.Tk()
window.title(TITLE)
window.geometry(SIZE)
window.minsize(780, 520)
window.resizable(True, True)
window.configure(bg=WINDOW_BG)


# --- Stav ------------------------------------------------------------------

# person je to, co se na tom snímku nakreslilo. Předloha v tom není.
frames = []
index = 0
brush_width = 5
interval_ms = INTERVAL_START
near_mm = NEAR_START
# Složka v kořeni projektu. Test si cestu přepíše.
EXPORT_DIR = Path(__file__).resolve().parents[1] / "vstup"
# Kam se na plátně vejde obrázek mřížky.
view = {"scale": 1, "ox": 0, "oy": 0}
last_cell = None
thumb_images = []
thumb_labels = []


# --- Snímky ----------------------------------------------------------------

def empty_frame():
    # Nový snímek nemá žádný vlastní tah.
    return {"person": np.zeros((HEIGHT, WIDTH), dtype=bool)}


def reset_frames():
    # Začátek je jedna prázdná fotka.
    global frames, index
    frames = [empty_frame()]
    index = 0


def shown_on(number):
    # Co je na snímku vidět: jeho čára a všechno, co prosvítá z předlohy.
    ink = frames[number]["person"].copy()
    if number > 0:
        ink |= shown_on(number - 1)
    return ink


def guide_mask():
    # Předloha je vždy jen snímek hned před tímto. Nic jiného se do toho neplete.
    if index == 0:
        return None
    immediate = frames[index - 1]["person"]
    stacked = shown_on(index - 1)
    # #region agent log
    try:
        import time
        _payload = {
            "sessionId": "6d201f",
            "hypothesisId": "A",
            "location": "simulate.py:guide_mask",
            "message": "guide source counts",
            "data": {
                "index": index,
                "frameCount": len(frames),
                "immediatePixels": int(immediate.sum()),
                "stackedPixels": int(stacked.sum()),
                "olderFramesIncluded": bool(int(stacked.sum()) > int(immediate.sum())),
            },
            "timestamp": int(time.time() * 1000),
        }
        with open(r"c:\Users\Frantik\Desktop\Škola\Kroužek\project-china\.cursor\debug-6d201f.log", "a", encoding="utf-8") as _log:
            _log.write(json.dumps(_payload) + "\n")
    except Exception:
        pass
    # #endregion
    chosen = immediate
    # #region agent log
    try:
        import time
        _payload = {
            "sessionId": "6d201f",
            "runId": "post-fix",
            "hypothesisId": "A",
            "location": "simulate.py:guide_mask",
            "message": "guide returned",
            "data": {"returnedPixels": int(chosen.sum()), "immediatePixels": int(immediate.sum())},
            "timestamp": int(time.time() * 1000),
        }
        with open(r"c:\Users\Frantik\Desktop\Škola\Kroužek\project-china\.cursor\debug-6d201f.log", "a", encoding="utf-8") as _log:
            _log.write(json.dumps(_payload) + "\n")
    except Exception:
        pass
    # #endregion
    return chosen


def add_frame():
    # Vloží prázdný snímek hned za ten otevřený a přepne se na něj.
    global index
    frames.insert(index + 1, empty_frame())
    index += 1
    sync_interval()
    rebuild_strip()
    redraw_board()


def remove_frame(number):
    # Pravý klik na náhled. Poslední snímek smazat nejde.
    global index
    if len(frames) < 2 or not 0 <= number < len(frames):
        return
    del frames[number]
    if number < index:
        index -= 1
    elif index >= len(frames):
        index = len(frames) - 1
    sync_interval()
    rebuild_strip()
    redraw_board()


def select(number):
    # Levý klik na náhled ten snímek otevře.
    global index
    if number == index or not 0 <= number < len(frames):
        return
    index = number
    rebuild_strip()
    redraw_board()


# --- Kreslení --------------------------------------------------------------

def paint_cell(cx, cy, erase):
    # Šířka 1 je jeden bod. Větší číslo je kruh. Guma na předlohu nesáhne.
    radius = (brush_width - 1) / 2
    ys, xs = np.ogrid[:HEIGHT, :WIDTH]
    hit = (xs - cx) ** 2 + (ys - cy) ** 2 <= radius ** 2
    frames[index]["person"][hit] = not erase


def line_cells(start, end):
    # Rychlý tah myší nesmí nechat díry.
    x0, y0 = start
    x1, y1 = end
    steps = max(abs(x1 - x0), abs(y1 - y0), 1)
    for step in range(steps + 1):
        part = step / steps
        yield round(x0 + (x1 - x0) * part), round(y0 + (y1 - y0) * part)


def event_cell(event):
    # Přepočet bodu na obrazovce na políčko mřížky.
    scale = view["scale"]
    x = (event.x - view["ox"]) // scale
    y = (event.y - view["oy"]) // scale
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        return int(x), int(y)
    return None


def stroke(event, erase):
    # Od posledního bodu tahu se dokreslí čára.
    global last_cell
    cell = event_cell(event)
    if cell is None:
        return
    if last_cell is None:
        paint_cell(*cell, erase)
    else:
        for point in line_cells(last_cell, cell):
            paint_cell(*point, erase)
    last_cell = cell
    redraw_board()
    refresh_current_thumb()


def on_press(event):
    global last_cell
    last_cell = None
    stroke(event, erase=False)


def on_drag(event):
    stroke(event, erase=False)


def on_erase_press(event):
    global last_cell
    last_cell = None
    stroke(event, erase=True)


def on_erase_drag(event):
    stroke(event, erase=True)


# --- Obrázky ---------------------------------------------------------------

def cell_colors():
    # Nejdřív šedá mřížka, přes ni světle modrá předloha, navrch černý tah.
    rgb = np.empty((HEIGHT, WIDTH, 3), dtype=np.uint8)
    rgb[:] = FAR_COLOR
    guide = guide_mask()
    if guide is not None:
        rgb[guide] = GUIDE_COLOR
    rgb[frames[index]["person"]] = INK_COLOR
    return rgb


def photo(rgb):
    # Tk umí obrázek z textu PPM. Držíme ho v proměnné, jinak zmizí.
    height, width = rgb.shape[:2]
    ppm = f"P6 {width} {height} 255\n".encode() + np.ascontiguousarray(rgb).tobytes()
    return tk.PhotoImage(data=ppm, format="ppm")


def grid_photo(scale):
    # Jeden čtvereček na bod a tenká mezera, ať je mřížka vidět.
    colors = cell_colors()
    if scale <= 1:
        return photo(colors)
    block = colors.repeat(scale, axis=0).repeat(scale, axis=1)
    block[scale - 1 :: scale, :, :] = GAP_COLOR
    block[:, scale - 1 :: scale, :] = GAP_COLOR
    return photo(block)


def silhouette(person, width_px):
    # Náhled nahoře je jen vybarvený tvar, bez mřížky a bez předlohy.
    height_px = max(1, round(width_px * HEIGHT / WIDTH))
    ys = np.linspace(0, HEIGHT, height_px, endpoint=False).astype(int)
    xs = np.linspace(0, WIDTH, width_px, endpoint=False).astype(int)
    small = person[ys][:, xs]
    rgb = np.full((height_px, width_px, 3), 255, dtype=np.uint8)
    rgb[small] = INK_COLOR
    return photo(rgb)


def redraw_board():
    # Obrázek se vejde do plátna. Větší okno jen zvětší čtverečky.
    width_px = max(board.winfo_width(), WIDTH)
    height_px = max(board.winfo_height(), HEIGHT)
    scale = max(1, min(width_px // WIDTH, height_px // HEIGHT))
    picture = grid_photo(scale)
    view["scale"] = scale
    view["ox"] = (width_px - WIDTH * scale) // 2
    view["oy"] = (height_px - HEIGHT * scale) // 2
    board.delete("all")
    board.create_image(view["ox"], view["oy"], image=picture, anchor="nw")
    board.image = picture


def refresh_current_thumb():
    if not thumb_labels:
        return
    image = silhouette(frames[index]["person"], 72)
    thumb_images[index] = image
    thumb_labels[index].configure(image=image)


def rebuild_strip():
    # Řada náhledů. Levý klik otevře, pravý smaže. Plus přidá snímek za otevřený.
    for child in strip.winfo_children():
        if child is not plus_button:
            child.destroy()
    thumb_images.clear()
    thumb_labels.clear()
    for number, frame in enumerate(frames):
        image = silhouette(frame["person"], 72)
        thumb_images.append(image)
        edge = "#111111" if number == index else WINDOW_BG
        label = tk.Label(
            strip,
            image=image,
            bg="white",
            highlightthickness=2,
            highlightbackground=edge,
        )
        label.pack(side="left", padx=4, pady=8)
        label.bind("<Button-1>", lambda _event, number=number: select(number))
        label.bind("<Button-3>", lambda _event, number=number: remove_frame(number))
        thumb_labels.append(label)
    plus_button.pack(side="left", padx=(8, 4), pady=8)


# --- Čísla vpravo ----------------------------------------------------------

def read_number(variable, fallback):
    # Nechá jen celé číslo od jedničky výš. Jinak vrátí to, co platilo.
    text = variable.get().strip()
    if text.isdigit() and int(text) >= 1:
        return int(text)
    return fallback


def apply_interval(_event=None):
    global interval_ms
    interval_ms = read_number(interval_var, interval_ms)
    interval_var.set(str(interval_ms))


def apply_distance(_event=None):
    global near_mm
    near_mm = read_number(distance_var, near_mm)
    distance_var.set(str(near_mm))


def sync_interval():
    # U jedné fotky mezera nic neznamená, políčko je zašedlé.
    state = "disabled" if len(frames) < 2 else "normal"
    color = "#9a9a9a" if len(frames) < 2 else "#222222"
    interval_entry.configure(state=state)
    interval_caption.configure(fg=color)
    interval_unit.configure(fg=color)


def set_width(value):
    global brush_width
    brush_width = int(float(value))


def on_wheel(event):
    # Kolečko nad mřížkou mění šířku. Windows ho posílá do okna, které má fokus.
    if not cursor_over_board():
        return
    step = 1 if event.delta > 0 else -1
    # Posuvník sám číslo neuloží, když ho posune program. Proto se šířka zapíše napřed.
    set_width(min(30, max(1, brush_width + step)))
    width_scale.set(brush_width)
    # #region agent log
    try:
        import time
        _payload = {
            "sessionId": "6d201f",
            "hypothesisId": "W",
            "location": "simulate.py:on_wheel",
            "message": "brush width from wheel",
            "data": {"delta": int(event.delta), "brushWidth": brush_width},
            "timestamp": int(time.time() * 1000),
        }
        with open(r"c:\Users\Frantik\Desktop\Škola\Kroužek\project-china\.cursor\debug-6d201f.log", "a", encoding="utf-8") as _log:
            _log.write(json.dumps(_payload) + "\n")
    except Exception:
        pass
    # #endregion


def cursor_over_board():
    try:
        px, py = board.winfo_pointerxy()
        x, y = board.winfo_rootx(), board.winfo_rooty()
        width, height = board.winfo_width(), board.winfo_height()
    except tk.TclError:
        return False
    return width > 1 and x <= px < x + width and y <= py < y + height


# --- Export ----------------------------------------------------------------

def export_frames():
    # Zapíše mřížky vzdáleností. Předloha v souboru není, jen tahy toho snímku.
    apply_interval()
    apply_distance()
    people = np.stack([frame["person"] for frame in frames])
    data = np.where(people, near_mm, FAR_MM).astype(np.float32)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    np.save(EXPORT_DIR / "frames.npy", data)
    info = {
        "width": WIDTH,
        "height": HEIGHT,
        "frames": len(frames),
        "interval_ms": interval_ms,
        "near_mm": near_mm,
        "far_mm": FAR_MM,
        "unit": "mm",
    }
    (EXPORT_DIR / "info.json").write_text(json.dumps(info), encoding="utf-8")


def on_resize(_event):
    redraw_board()


# --- Rozložení -------------------------------------------------------------

# Nahoře náhledy. Vpravo mezera, vzdálenost, export a šířka. Zbytek je mřížka.
top = tk.Frame(window, bg=WINDOW_BG, height=88)
top.grid(row=0, column=0, sticky="nsew")
side = tk.Frame(window, bg=PANEL_BG, width=240)
side.grid(row=0, column=1, rowspan=2, sticky="nsew")
# Děti jsou vložené packem. Bez toho by se sloupec scvrkl na šířku tlačítka.
side.pack_propagate(False)
board = tk.Canvas(window, bg=WINDOW_BG, highlightthickness=0)
board.grid(row=1, column=0, sticky="nsew")
window.rowconfigure(1, weight=1)
window.columnconfigure(0, weight=1)

strip = tk.Frame(top, bg=WINDOW_BG)
strip.pack(side="left", fill="y")
plus_button = tk.Button(strip, text="+", font=("Segoe UI", 18), command=add_frame, width=3)

interval_row = tk.Frame(side, bg=PANEL_BG)
interval_row.pack(fill="x", padx=12, pady=(16, 4))
interval_caption = tk.Label(interval_row, text="Mezera", bg=PANEL_BG, font=("Segoe UI", 12))
interval_caption.pack(side="left")
interval_var = tk.StringVar(value=str(interval_ms))
interval_entry = tk.Entry(interval_row, textvariable=interval_var, font=("Segoe UI", 12), width=6, justify="right")
interval_entry.pack(side="left", padx=8)
interval_entry.bind("<Return>", apply_interval)
interval_entry.bind("<FocusOut>", apply_interval)
interval_unit = tk.Label(interval_row, text="ms", bg=PANEL_BG, font=("Segoe UI", 12))
interval_unit.pack(side="left")

distance_row = tk.Frame(side, bg=PANEL_BG)
distance_row.pack(fill="x", padx=12, pady=(8, 4))
tk.Label(distance_row, text="Vzdálenost", bg=PANEL_BG, font=("Segoe UI", 12)).pack(side="left")
distance_var = tk.StringVar(value=str(near_mm))
distance_entry = tk.Entry(distance_row, textvariable=distance_var, font=("Segoe UI", 12), width=6, justify="right")
distance_entry.pack(side="left", padx=8)
distance_entry.bind("<Return>", apply_distance)
distance_entry.bind("<FocusOut>", apply_distance)
tk.Label(distance_row, text="mm", bg=PANEL_BG, font=("Segoe UI", 12)).pack(side="left")

export_button = tk.Button(side, text="Export", font=("Segoe UI", 14), command=export_frames)
export_button.pack(fill="x", padx=12, pady=(12, 20))
tk.Label(side, text="Šířka", bg=PANEL_BG, font=("Segoe UI", 12)).pack(fill="x", padx=12, pady=(8, 0))
width_scale = tk.Scale(
    side,
    from_=1,
    to=30,
    orient="horizontal",
    command=set_width,
    bg=PANEL_BG,
    highlightthickness=0,
)
width_scale.set(brush_width)
width_scale.pack(fill="x", padx=12)

# Levé tlačítko kreslí, pravé maže.
board.bind("<Button-1>", on_press)
board.bind("<B1-Motion>", on_drag)
board.bind("<Button-3>", on_erase_press)
board.bind("<B3-Motion>", on_erase_drag)
board.bind("<Configure>", on_resize)
board.bind("<Enter>", lambda _event: board.focus_set())
window.bind_all("<MouseWheel>", on_wheel)

reset_frames()
sync_interval()
rebuild_strip()

# Okno zůstane otevřené, dokud ho člověk nezavře.
if __name__ == "__main__":
    window.mainloop()
