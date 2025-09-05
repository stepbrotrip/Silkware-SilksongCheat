import pymem as pym
import pymem.process as pmp
import tkinter as tk
import keyboard as kb
import threading

# --- pymem setup ---
pm = pym.Pymem("Hollow Knight Silksong.exe")
mono_dll = pmp.module_from_name(pm.process_handle, "mono-2.0-bdwgc.dll").lpBaseOfDll
unity_dll = pmp.module_from_name(pm.process_handle, "UnityPlayer.dll").lpBaseOfDll

def resolve_pointer_chain(pm, base, offsets):
    addr = pm.read_ulonglong(base)
    for offset in offsets[:-1]:
        addr = pm.read_ulonglong(addr + offset)
    return addr + offsets[-1]

# --- addresses ---
rosary_base = mono_dll + 0x00A024E8
rosary_offsets = [0x350, 0x10, 0x60, 0x0, 0xD8, 0xB8, 0x23C]
health_base = mono_dll + 0x00A030B8
health_offsets = [0x138, 0x1A8, 0x10, 0x60, 0x0, 0x110, 0x21C]
shards_base = mono_dll + 0x00A030B8
shards_offsets = [0x138, 0x1A8, 0x10, 0x60, 0x0, 0x110, 0x908]
soul_base = mono_dll + 0x00763240
soul_offsets = [0x298, 0xB80, 0x308, 0x20, 0x78, 0x250, 0x240]
y_base = unity_dll + 0x01F419A0
y_offsets = [0x8, 0x90, 0x10, 0x38, 0x18, 0x20, 0x430]
x_base = unity_dll + 0x01F41A68
x_offsets = [0x48, 0x608,0x40,0x98,0x158,0x90,0x42C]

# --- Superfly patch address ---
superfly_addr = unity_dll + 0xEBB8AA
superfly_orig_bytes = None

# --- movement settings ---
fly_speed = 2.5
no_cspd = 1.5
x_spd = 0.4

# --- colors ---
title_bg = "#2A2A2A"
content_bg = "#3C3C3C"
dark_frame_bg = "#252525"
text_color = "#FF914D"

ascii_art = r"""
           /$$ /$$ /$$                                                  
          |__/| $$| $$                                                  
  /$$$$$$$ /$$| $$| $$   /$$ /$$  /$$  /$$  /$$$$$$   /$$$$$$   /$$$$$$ 
 /$$_____/| $$| $$| $$  /$$/| $$ | $$ | $$ |____  $$ /$$__  $$ /$$__  $$
|  $$$$$$ | $$| $$| $$$$$$/ | $$ | $$ | $$  /$$$$$$$| $$  \__/| $$$$$$$$
 \____  $$| $$| $$| $$_  $$ | $$ | $$ | $$ /$$__  $$| $$      | $$_____/
 /$$$$$$$/| $$| $$| $$ \  $$|  $$$$$/$$$$/|  $$$$$$$| $$      |  $$$$$$$
|_______/ |__/|__/|__/  \__/ \_____/\___/  \_______/|__/       \_______/                                        
"""

# --- UI setup ---
root = tk.Tk()
root.geometry("550x300")  # extra width for hotkey frame
root.attributes("-topmost", True)
root.overrideredirect(True)

# Gradient border canvas
border_canvas = tk.Canvas(root, width=540, height=290, highlightthickness=0, bd=0)
border_canvas.pack(fill="both", expand=True)
def draw_vertical_gradient(canvas, x0, y0, x1, y1, color1, color2):
    r1, g1, b1 = canvas.winfo_rgb(color1)
    r2, g2, b2 = canvas.winfo_rgb(color2)
    h = y1 - y0
    for i in range(h):
        nr = int(r1 + (r2 - r1) * i / h)
        ng = int(g1 + (g2 - g1) * i / h)
        nb = int(b1 + (b2 - b1) * i / h)
        color = f"#{nr>>8:02x}{ng>>8:02x}{nb>>8:02x}"
        canvas.create_line(x0, y0+i, x1, y0+i, fill=color)

draw_vertical_gradient(border_canvas, 0, 0, 550, 300, "#FF512F", "#FF914D")

outer = tk.Frame(border_canvas, bg=title_bg)
outer.place(relx=0.5, rely=0.5, anchor="center", width=540, height=290)

title_frame = tk.Frame(outer, bg=title_bg, height=60)
title_frame.pack(fill="x")
title_frame.pack_propagate(False)
content_frame = tk.Frame(outer, bg=content_bg)
content_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)

bg_label = tk.Label(title_frame, text=ascii_art, font=("Consolas",4), fg="#FF914D", bg=title_bg, justify="left", anchor="nw")
bg_label.place(relx=0.45, rely=0.5, anchor="center")

# --- Make window draggable by title_frame ---
def start_move(event):
    root.x = event.x_root
    root.y = event.y_root

def do_move(event):
    dx = event.x_root - root.x
    dy = event.y_root - root.y
    x = root.winfo_x() + dx
    y = root.winfo_y() + dy
    root.geometry(f"+{x}+{y}")
    root.x = event.x_root
    root.y = event.y_root

title_frame.bind("<Button-1>", start_move)
title_frame.bind("<B1-Motion>", do_move)
bg_label.bind("<Button-1>", start_move)
bg_label.bind("<B1-Motion>", do_move)

# --- Variables ---
do_rosary = tk.BooleanVar(value=False)
do_health = tk.BooleanVar(value=False)
do_shards = tk.BooleanVar(value=False)
do_soul = tk.BooleanVar(value=False)
superfly = tk.BooleanVar(value=False)
speed = tk.BooleanVar(value=False)
flight = tk.BooleanVar(value=False)
superfly_orig_bytes = None

# --- Hotkey storage ---
hotkeys = {
    "Inf Rosary": None,
    "Inf Shell Shards": None,
    "Godmode": None,
    "Inf Soul": None,
    "Super Speed": None,
    "Flight": None,
    "No Clip": None
}

def set_hotkey(cheat_name, btn, var):
    def capture():
        btn.config(text="Press a key…")
        event = kb.read_event(suppress=True)
        if event.event_type == kb.KEY_DOWN:
            hotkeys[cheat_name] = event.name
            btn.config(text=f"Hotkey: {event.name}")
            # Register toggle
            kb.add_hotkey(event.name, lambda: var.set(not var.get()))
    threading.Thread(target=capture, daemon=True).start()

# --- Cheat loop ---
def _do_speed():
    try:
        x_addr = resolve_pointer_chain(pm, x_base, x_offsets)
        cx = pm.read_float(x_addr)
        if kb.is_pressed("left"):  cx -= x_spd
        if kb.is_pressed("right"): cx += x_spd
        pm.write_float(x_addr, cx)
    except: pass

def _do_flight():
    try:
        y_addr = resolve_pointer_chain(pm, y_base, y_offsets)
        cy = pm.read_float(y_addr)
        if kb.is_pressed("up"):    cy += 1
        if kb.is_pressed("down"):  cy -= 1
        pm.write_float(y_addr, cy)
    except: pass

def toggle_superfly():
    global superfly_orig_bytes
    if superfly.get():  # cheat enabled
        try:
            if superfly_orig_bytes is None:
                superfly_orig_bytes = pm.read_bytes(superfly_addr, 5)  # save original
            pm.write_bytes(superfly_addr, b'\x90' * 5, 5)  # NOP gravity
        except Exception as e:
            print("Error enabling No Clip:", e)
    else:  # cheat disabled
        try:
            if superfly_orig_bytes:
                pm.write_bytes(superfly_addr, superfly_orig_bytes, len(superfly_orig_bytes))
        except Exception as e:
            print("Error disabling No Clip:", e)
superfly.trace_add("write", lambda *args: toggle_superfly())

def _do_superfly():
    try:
        x_addr = resolve_pointer_chain(pm, x_base, x_offsets)
        y_addr = resolve_pointer_chain(pm, y_base, y_offsets)
        cx = pm.read_float(x_addr)
        cy = pm.read_float(y_addr)
        if kb.is_pressed("left"):  cx -= x_spd
        if kb.is_pressed("right"): cx += x_spd
        if kb.is_pressed("up"):    cy += .5
        if kb.is_pressed("down"):  cy -= .5
        pm.write_float(x_addr, cx)
        pm.write_float(y_addr, cy)
    except: pass



def _cheat_loop():
    try:
        if do_rosary.get(): pm.write_int(resolve_pointer_chain(pm, rosary_base, [0x350,0x10,0x60,0x0,0xD8,0xB8,0x23C]), 9999)
        if do_shards.get(): pm.write_int(resolve_pointer_chain(pm, shards_base, [0x138,0x1A8,0x10,0x60,0x0,0x110,0x908]), 9999)
        if do_health.get(): pm.write_int(resolve_pointer_chain(pm, health_base, [0x138,0x1A8,0x10,0x60,0x0,0x110,0x21C]), 10)
        if do_soul.get(): pm.write_int(resolve_pointer_chain(pm, soul_base, [0x298,0xB80,0x308,0x20,0x78,0x250,0x240]), 18)
        if speed.get(): _do_speed()
        if flight.get(): _do_flight()
        if superfly.get(): _do_superfly()
    except: pass
    root.after(20, _cheat_loop)

# --- 2x4 grid layout ---
# --- Tooltip helper --- 
class Tooltip: 
    def __init__(self, widget, text, delay=500): 
        self.widget = widget 
        self.text = text 
        self.delay = delay 
        self.tipwindow = None 
        self.id = None 
        widget.bind("<Enter>", self.schedule) 
        widget.bind("<Leave>", self.hide) 
        widget.bind("<Motion>", self.move) 
    def schedule(self, event=None): 
        self.unschedule() 
        self.id = self.widget.after(self.delay, self.show) 
    def unschedule(self): 
        if self.id: 
            self.widget.after_cancel(self.id) 
            self.id = None 
    def show(self, event=None): 
        if self.tipwindow: 
            return 
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5 
        self.tipwindow = tw = tk.Toplevel(self.widget) 
        tw.wm_overrideredirect(True) 
        tw.wm_geometry(f"+{x}+{y}") 
        tw.wm_attributes("-topmost", True) 
        frame = tk.Frame(tw, bg="#FF914D", bd=0) 
        frame.pack(padx=1, pady=1) 
        content = tk.Frame(frame, bg=content_bg) 
        content.pack() 
        label = tk.Label(content, text=self.text, bg=content_bg, fg="#FF914D", font=("Segoe UI", 10), justify="left", padx=6, pady=4) 
        label.pack() 
    def hide(self, event=None): 
        self.unschedule() 
        if self.tipwindow: 
            self.tipwindow.destroy() 
            self.tipwindow = None 
    def move(self, event): 
        if self.tipwindow: 
            x = event.x_root + 20
            y = event.y_root + 10 
            self.tipwindow.wm_geometry(f"+{x}+{y}")

def make_check(text, var, tooltip_text=None, row=0, col=0):
    chk = tk.Checkbutton(content_frame, text=text, variable=var, bg=content_bg, fg=text_color,
                          activebackground=content_bg, activeforeground=text_color,
                          selectcolor=title_bg, font=("Segoe UI", 11, "bold"), anchor="w", padx=8)
    if tooltip_text:
        Tooltip(chk, tooltip_text)
    chk.grid(row=row, column=col, sticky="w", padx=5, pady=5)
    return chk

make_check("Inf Rosary Beads", do_rosary, "Gives you infinite Rosary Beads", 0, 0)
make_check("Inf Shell Shards", do_shards, "Gives you infinite Shell Shards", 0, 1)
make_check("Godmode", do_health, "Sets your health to max constantly", 1, 0)
make_check("Inf Soul", do_soul, "Gives infinite Soul", 1, 1)
make_check("Super Speed", speed, "Fast left/right movement", 2, 0)
make_check("Flight", flight, "Vertical flight only", 2, 1)
make_check("Better Fly", superfly, "Fly + move fast (NOP applied) Sometimes breaks when going through objects", 3, 0)

# --- Hotkey frame ---
hotkey_frame = tk.Frame(outer, bg=dark_frame_bg)
hotkey_frame.pack(side="right", fill="y", padx=5, pady=5)

for i, (cheat, var) in enumerate([("Inf Rosary", do_rosary),
                                  ("Inf Shell Shards", do_shards),
                                  ("Godmode", do_health),
                                  ("Inf Soul", do_soul),
                                  ("Super Speed", speed),
                                  ("Flight", flight),
                                  ("Better Flight", superfly)]):
    lbl = tk.Label(hotkey_frame, text=cheat, bg=dark_frame_bg, fg=text_color, font=("Segoe UI", 10, "bold"))
    lbl.grid(row=i, column=0, sticky="w", pady=2)
    btn = tk.Button(hotkey_frame, text="Set Hotkey", bg=title_bg, fg="#FFFFFF", bd=0)
    btn.grid(row=i, column=1, pady=2, padx=3)
    # Pass the button itself to set_hotkey
    btn.config(command=lambda c=cheat, b=btn, v=var: set_hotkey(c, b, v))


def safe_close():
    global superfly_orig_bytes
    try:
        if superfly_orig_bytes:
            pm.write_bytes(superfly_addr, superfly_orig_bytes, len(superfly_orig_bytes))
    except:
        pass
    root.destroy()


close_btn = tk.Button(title_frame, text="✕", font=("Segoe UI",10,"bold"), fg="#EAEAEA",
                      bg=title_bg, activebackground="#FF512F", activeforeground="#FFFFFF",
                      bd=0, command=safe_close)
close_btn.pack(side="right", padx=5, pady=5)

# --- Menu toggle keybind ---
menu_visible = True
def toggle_menu():
    global menu_visible
    if menu_visible: root.withdraw()
    else: root.deiconify()
    menu_visible = not menu_visible
kb.add_hotkey(".", toggle_menu)

# --- Start ---
_cheat_loop()
root.mainloop()
