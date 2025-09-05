import pymem as pym
import pymem.process as pmp
import tkinter as tk

# --- pymem setup (placeholder) ---
pm = pym.Pymem("Hollow Knight Silksong.exe")
mono_dll = pmp.module_from_name(pm.process_handle, "mono-2.0-bdwgc.dll").lpBaseOfDll

def resolve_pointer_chain(pm, base, offsets):
    addr = pm.read_ulonglong(base)
    for offset in offsets[:-1]:
        addr = pm.read_ulonglong(addr + offset)
    return addr + offsets[-1]

# --- addresses/offsets (examples) ---
rosary_base = mono_dll + 0x00A024E8
rosary_offsets = [0x350, 0x10, 0x60, 0x0, 0xD8, 0xB8, 0x23C]

health_base = mono_dll + 0x00A030B8
health_offsets = [0x138, 0x1A8, 0x10, 0x60, 0x0, 0x110, 0x21C]

shards_base = mono_dll + 0x00A030B8
shards_offsets = [0x138, 0x1A8, 0x10, 0x60, 0x0, 0x110, 0x908]

soul_base = mono_dll + 0x00739028
soul_offsets = [0x128, 0x148, 0x5D8, 0x2F8, 0x148, 0x110, 0x240]

# --- colors ---
title_bg = "#2A2A2A"     # dark gray title bar
content_bg = "#3C3C3C"   # lighter gray content
text_color = "#EAEAEA"   # fallback text
highlight_color = "#FF914D"



# ------------------ ASCII Art ------------------
ascii_arts = {
    "block_silkware": r"""
           /$$ /$$ /$$                                                  
          |__/| $$| $$                                                  
  /$$$$$$$ /$$| $$| $$   /$$ /$$  /$$  /$$  /$$$$$$   /$$$$$$   /$$$$$$ 
 /$$_____/| $$| $$| $$  /$$/| $$ | $$ | $$ |____  $$ /$$__  $$ /$$__  $$
|  $$$$$$ | $$| $$| $$$$$$/ | $$ | $$ | $$  /$$$$$$$| $$  \__/| $$$$$$$$
 \____  $$| $$| $$| $$_  $$ | $$ | $$ | $$ /$$__  $$| $$      | $$_____/
 /$$$$$$$/| $$| $$| $$ \  $$|  $$$$$/$$$$/|  $$$$$$$| $$      |  $$$$$$$
|_______/ |__/|__/|__/  \__/ \_____/\___/  \_______/|__/       \_______/                                        
"""

}

# --- gradient helpers ---
def draw_vertical_gradient(canvas, x0, y0, x1, y1, color1, color2):
    """Draw vertical gradient rectangle on a Canvas."""
    r1, g1, b1 = canvas.winfo_rgb(color1)
    r2, g2, b2 = canvas.winfo_rgb(color2)
    h = y1 - y0
    for i in range(h):
        nr = int(r1 + (r2 - r1) * i / h)
        ng = int(g1 + (g2 - g1) * i / h)
        nb = int(b1 + (b2 - b1) * i / h)
        color = f"#{nr>>8:02x}{ng>>8:02x}{nb>>8:02x}"
        canvas.create_line(x0, y0 + i, x1, y0 + i, fill=color)

def gradient_text(canvas, x, y, text, font, color1, color2):
    """Fake gradient text by drawing each line in gradient color."""
    # Use font metrics for height
    step = 2
    bbox = canvas.bbox(canvas.create_text(x, y, text=text, font=font))
    height = bbox[3] - bbox[1] if bbox else 20
    r1, g1, b1 = canvas.winfo_rgb(color1)
    r2, g2, b2 = canvas.winfo_rgb(color2)
    for i in range(0, height, step):
        t = i / height
        nr = int(r1 + (r2 - r1) * t)
        ng = int(g1 + (g2 - g1) * t)
        nb = int(b1 + (b2 - b1) * t)
        color = f"#{nr>>8:02x}{ng>>8:02x}{nb>>8:02x}"
        canvas.create_text(x, y - height//2 + i, text=text, font=font, fill=color)

# --- UI setup ---
root = tk.Tk()
root.geometry("400x300")
root.attributes("-topmost", True)
root.overrideredirect(True)

# Gradient border canvas
border_canvas = tk.Canvas(root, width=390, height=290, highlightthickness=0, bd=0)
border_canvas.pack(fill="both", expand=True)

# Draw gradient border background
draw_vertical_gradient(border_canvas, 0, 0, 400, 300, "#FF512F", "#FF914D")

# Main container (inner frame)
outer = tk.Frame(border_canvas, bg=title_bg)
outer.place(relx=0.5, rely=0.5, anchor="center", width=390, height=290)

# --- Title bar (Canvas with solid text for readability) ---
title_frame = tk.Frame(outer, bg=title_bg, height=40)
title_frame.pack(fill="x")

title_canvas = tk.Canvas(title_frame, width=395, height=0,
                         bg=title_bg, highlightthickness=0, bd=0)
title_canvas.pack(fill="both", expand=True)

# Content area
content_frame = tk.Frame(outer, bg=content_bg)
content_frame.pack(fill="both", expand=True, padx=5, pady=5)

bg_label = tk.Label(
    content_frame,
    text=ascii_arts["block_silkware"],
    font=("Consolas", 6),  # Monospaced font
    fg="#FF914D",
    bg=content_bg,
    justify="left",          # Keep left-aligned
    anchor="nw"              # Top-left corner alignment
)
bg_label.place(relx=0.05, rely=0)    # Use fixed coordinates to prevent weird shifts

# Variables
do_rosary = tk.BooleanVar(value=False)
do_health = tk.BooleanVar(value=False)
do_shards = tk.BooleanVar(value=False)
do_soul = tk.BooleanVar(value=False)

# Cheat functions
def _do_rosary():
    try:
        addr = resolve_pointer_chain(pm, rosary_base, rosary_offsets)
        pm.write_int(addr, 9999)
    except: pass

def _do_health():
    try:
        addr = resolve_pointer_chain(pm, health_base, health_offsets)
        pm.write_int(addr, 99)
    except: pass

def _do_shards():
    try:
        addr = resolve_pointer_chain(pm, shards_base, shards_offsets)
        pm.write_int(addr, 9999)
    except: pass

def _do_soul():
    try:
        addr = resolve_pointer_chain(pm, soul_base, soul_offsets)
        pm.write_int(addr, 18)
    except: pass

def _cheat_loop():
    if do_rosary.get(): _do_rosary()
    if do_shards.get(): _do_shards()
    if do_health.get(): _do_health()
    if do_soul.get(): _do_soul()
    root.after(100, _cheat_loop)

# Checkbutton factory
def make_check(text, variable):
    return tk.Checkbutton(
        content_frame, text=text, variable=variable,
        bg=content_bg, fg=text_color,
        activebackground=content_bg, activeforeground=text_color,
        selectcolor=title_bg,
        font=("Segoe UI", 11, "bold"),
        anchor="w", padx=8
    )

# Place checkboxes
make_check("Inf Rosary Beads", do_rosary).place(relx=0.6, rely=0.7, anchor="center")
make_check("Inf Shell Shards", do_shards).place(relx=0.6, rely=0.5, anchor="center")
make_check("Godmode", do_health).place(relx=0.2, rely=0.7, anchor="center")
make_check("Inf Soul", do_soul).place(relx=0.2, rely=0.5, anchor="center")
_cheat_loop()
root.mainloop()
