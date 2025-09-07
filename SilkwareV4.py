import pymem as pym
import pymem.process as pmp
import tkinter as tk
import keyboard as kb
import threading
import os
import json
from tkinter import ttk, simpledialog, messagebox
import pygame
import time

pygame.init()
pygame.joystick.init()
joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
for j in joysticks: j.init()



docs_path = os.path.join(os.path.expanduser("~"), "Documents", "Silkware")
os.makedirs(docs_path, exist_ok=True)
config_path = os.path.join(docs_path, "config.json")

# --- pymem setup ---
pm = pym.Pymem("Hollow Knight Silksong.exe")
mono_dll = pmp.module_from_name(pm.process_handle, "mono-2.0-bdwgc.dll").lpBaseOfDll
unity_dll = pmp.module_from_name(pm.process_handle, "UnityPlayer.dll").lpBaseOfDll

def resolve_pointer_chain(pm, base, offsets):
    addr = pm.read_ulonglong(base)
    for offset in offsets[:-1]:
        addr = pm.read_ulonglong(addr + offset)
    return addr + offsets[-1]

# List configs
def list_configs():
    files = [f for f in os.listdir(docs_path) if f.endswith(".json")]
    return files

def ask_config_name():
    dialog = tk.Toplevel(root)
    dialog.title("Save Config")
    dialog.attributes("-topmost", True)
    dialog.grab_set()
    dialog.overrideredirect(True)

    # --- Center inside cheat menu ---
    root.update_idletasks()
    rw, rh = root.winfo_width(), root.winfo_height()
    rx, ry = root.winfo_x(), root.winfo_y()
    dw, dh = 300, 150
    dx = rx + (rw - dw) // 2
    dy = ry + (rh - dh) // 2
    dialog.geometry(f"{dw}x{dh}+{dx}+{dy}")

    # --- Outer border (orange) ---
    border_frame = tk.Frame(dialog, bg="#FF914D", bd=2)
    border_frame.pack(fill="both", expand=True)

    # --- Inner content ---
    inner = tk.Frame(border_frame, bg=content_bg)
    inner.pack(fill="both", expand=True)

    # Title bar
    top = tk.Frame(inner, bg=title_bg, height=30)
    top.pack(fill="x")
    tk.Label(top, text="Save Config", bg=title_bg, fg=text_color,
             font=("Segoe UI", 10, "bold")).pack(side="left", padx=8)

    # Body
    body = tk.Frame(inner, bg=content_bg)
    body.pack(expand=True, fill="both", padx=15, pady=15)

    tk.Label(body, text="Enter config name:", bg=content_bg, fg=text_color,
             font=("Segoe UI", 10)).pack(anchor="w")

    entry = tk.Entry(body, bg="#FFA500", fg="black", insertbackground="black",
                     relief="flat", font=("Segoe UI", 11), width=25)
    entry.pack(pady=8)

    result = {"value": None}

    def confirm():
        val = entry.get().strip()
        if val:
            result["value"] = val
        dialog.destroy()

    def cancel():
        dialog.destroy()

    btn_frame = tk.Frame(body, bg=content_bg)
    btn_frame.pack(pady=5)

    tk.Button(btn_frame, text="Save", command=confirm,
              bg="#FF914D", fg="#2A2A2A", relief="flat", padx=10, pady=2).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Cancel", command=cancel,
              bg=title_bg, fg="#FFFFFF", relief="flat", padx=10, pady=2).pack(side="left", padx=5)

    entry.focus_set()
    dialog.wait_window()
    return result["value"]

def save_config(filename=None):
    if not filename:
        filename = config_dropdown.get()
        if filename == "New Config...":
            filename = ask_config_name()
            if not filename:
                return
            filename = filename + ".json"

    data = {
        "hotkeys": hotkeys,
        "cheats": {
            "Godmode": do_health.get(),
            "Inf Soul": do_soul.get(),
            "Better Flight": superfly.get(),
            "No Losing Items": do_save_items.get(),
        }
    }
    with open(os.path.join(docs_path, filename), "w") as f:
        json.dump(data, f, indent=4)
    refresh_dropdown()
    config_dropdown.set(filename)


def load_config(filename=None):
    global hotkeys
    if not filename:
        filename = config_dropdown.get()
    if filename == "New Config...":
        return

    path = os.path.join(docs_path, filename)
    if not os.path.exists(path):
        return

    with open(path, "r") as f:
        data = json.load(f)

    # --- restore cheats ---
    cheats = data.get("cheats", {})
    do_health.set(cheats.get("Godmode", False))
    do_soul.set(cheats.get("Inf Soul", False))
    superfly.set(cheats.get("Better Flight", False))
    do_save_items.set(cheats.get("No Losing Items", False))

    # --- restore hotkeys ---
    # First, clear existing hotkeys
    for hk in list(hotkeys.values()):
        if hk:
            try: kb.remove_hotkey(hk)
            except: pass
    hotkeys = {}

    saved_hotkeys = data.get("hotkeys", {})
    for cheat_name, key in saved_hotkeys.items():
        hotkeys[cheat_name] = key
        if not key:
            continue
        action = cheat_actions.get(cheat_name)
        if isinstance(action, tk.BooleanVar):
            kb.add_hotkey(key, lambda v=action: v.set(not v.get()))
        elif callable(action):
            kb.add_hotkey(key, action)

    # Update hotkey buttons text
    for widget in hotkey_frame.winfo_children():
        if isinstance(widget, tk.Button) and "Hotkey" in widget.cget("text"):
            cheat = widget.grid_info()["row"]  # row index
            cheat_name = list(cheat_actions.keys())[cheat]
            key = hotkeys.get(cheat_name)
            widget.config(text=f"Hotkey: {key}" if key else "No Hotkey")


# Refresh dropdown
def refresh_dropdown():
    configs = list_configs()
    configs.append("New Config...")
    config_dropdown["values"] = configs
    if configs:
        config_dropdown.set(configs[0])

# --- addresses ---
rosary_base = mono_dll + 0x00A024E8
rosary_offsets = [0x350, 0x10, 0x60, 0x0, 0xD8, 0xB8, 0x23C]
health_base = mono_dll + 0x007632B8
health_offsets = [0x278,0xB40,0x1F0,0x0,0x68,0x110,0x21C]
shards_base = mono_dll + 0x00A030B8
shards_offsets = [0x138, 0x1A8, 0x10, 0x60, 0x0, 0x110, 0x908]
soul_base = mono_dll + 0x00739138
soul_offsets = [0x78,0xB40,0x430,0x10,0x68,0x110,0x240]
y_base = unity_dll + 0x01F41DB8
y_offsets = [0xA90,0x608,0x18,0x48,0x60,0x330]
x_base = unity_dll + 0x01F6BFA0
x_offsets = [0x118, 0x80,0x620,0x0,0x380,0x10,0x42C]

# --- Superfly patch address ---
superfly_addr = unity_dll + 0xEBB8AA
superfly_orig_bytes = None

# --- movement settings ---
x_spd = 1

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
do_health = tk.BooleanVar(value=False)
do_soul = tk.BooleanVar(value=False)
do_save_items = tk.BooleanVar(value=False)
superfly = tk.BooleanVar(value=False)
superfly_orig_bytes = None

# --- Hotkey storage ---
hotkeys = {
    "Inf Rosary": None,
    "Inf Shell Shards": None,
    "Godmode": None,
    "Inf Soul": None,
    "No Clip": None,
    "No Item Loss": None,
}

def get_controller_direction():
    dx, dy = 0, 0
    deadzone = 0.2

    for joystick in joysticks:
        # Left stick
        axis_x = joystick.get_axis(0)
        axis_y = joystick.get_axis(1)

        if abs(axis_x) > deadzone:
            dx += axis_x * x_spd * 5
        if abs(axis_y) > deadzone:
            dy -= axis_y * x_spd * 5  # invert if needed

        # D-pad (hat)
        hat_x, hat_y = joystick.get_hat(0)
        dx += hat_x * x_spd * 5
        dy += hat_y * x_spd * 5

    return dx, dy

def set_hotkey(cheat_name, btn, action):
    def capture_keyboard():
        btn.config(text="Press a key…")
        # Only listen to keyboard events, ignore controllers
        while True:
            event = kb.read_event(suppress=True)
            if event.event_type == kb.KEY_DOWN:
                if event.name == "esc":
                    hotkeys[cheat_name] = None
                    btn.config(text="No Hotkey")
                    break
                hotkeys[cheat_name] = {"type": "keyboard", "key": event.name}
                btn.config(text=f"Hotkey: {event.name}")
                break
    threading.Thread(target=capture_keyboard, daemon=True).start()


rosarys = 0
shells = 0
def save_things_ad():
    global rosarys, shells

    health = pm.read_int(resolve_pointer_chain(pm, health_base, health_offsets))
    if health <= 0:
        pm.write_int(resolve_pointer_chain(pm, rosary_base, rosary_offsets), rosarys)
        pm.write_int(resolve_pointer_chain(pm, shards_base, shards_offsets), shells)
        return
    
    rosarys = pm.read_int(resolve_pointer_chain(pm, rosary_base, rosary_offsets))
    shells = pm.read_int(resolve_pointer_chain(pm, shards_base, shards_offsets))


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

        # Keyboard input
        if kb.is_pressed("left"):  cx -= .45
        if kb.is_pressed("right"): cx += .45
        if kb.is_pressed("up"):    cy += .45
        if kb.is_pressed("down"):  cy -= .45

        # Controller input
        dx, dy = get_controller_direction()
        cx += dx*.10
        cy += dy*.10

        pm.write_float(x_addr, cx)
        pm.write_float(y_addr, cy)
    except Exception as e:
        print("Superfly error:", e)


def write_rosary():
    try:
        cur_rosarys = pm.read_int(resolve_pointer_chain(pm, rosary_base, rosary_offsets))
        new_rosarys = cur_rosarys + 150 
        pm.write_int(resolve_pointer_chain(pm, rosary_base, rosary_offsets), new_rosarys)
    except: pass

def write_shards():
    try:
        cur_shards = pm.read_int(resolve_pointer_chain(pm, shards_base, shards_offsets))
        new_shards = cur_shards + 50 
        pm.write_int(resolve_pointer_chain(pm, shards_base, shards_offsets), new_shards)
    except:pass

def _cheat_loop():
    try:
        if do_health.get():
            try: pm.write_int(resolve_pointer_chain(pm, health_base, health_offsets), 10)
            except: pass
        if do_soul.get():
            try: pm.write_int(resolve_pointer_chain(pm, soul_base, soul_offsets), 18)
            except Exception as e:
                print("Soul error:", e)
        if superfly.get():
            _do_superfly()
        if do_save_items.get():
            save_things_ad()
    except: 
        pass
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

add_rosarys = tk.Button(content_frame, text="+150 Rosary Beads", command=write_rosary, 
                     relief="flat", background="#FF914D", foreground="#2A2A2A")
add_rosarys.place(relx=0.2, rely=0.7, anchor="center")
add_shards = tk.Button(content_frame, text="+50 Shell Shards", command=write_shards, 
                     relief="flat", background="#FF914D", foreground="#2A2A2A")
add_shards.place(relx=0.55, rely=0.7, anchor="center")
make_check("Godmode", do_health, "Sets your health to max constantly", 1, 0)
make_check("Inf Soul", do_soul, "Gives infinite Soul", 1, 1)
make_check("Better Fly", superfly, "Fly + move fast (NOP applied) Sometimes breaks when going through objects", 3, 0)
make_check("No Losing Items", do_save_items, "Saves rosary beads and shell shards after death",3, 1 )
# --- Hotkey frame ---
hotkey_frame = tk.Frame(outer, bg=dark_frame_bg)
hotkey_frame.pack(side="right", fill="y", padx=5, pady=5)

cheat_actions = {
    "Add Rosary Beads": write_rosary,
    "Add Shell Shards": write_shards,
    "Godmode": do_health,
    "Inf Soul": do_soul,
    "Better Flight": superfly
}

for i, (cheat, action) in enumerate(cheat_actions.items()):
    lbl = tk.Label(hotkey_frame, text=cheat, bg=dark_frame_bg, fg=text_color, font=("Segoe UI", 10, "bold"))
    lbl.grid(row=i, column=0, sticky="w", pady=2)
    btn = tk.Button(hotkey_frame, text="Set Hotkey", bg=title_bg, fg="#FFFFFF", bd=0)
    btn.grid(row=i, column=1, pady=2, padx=3)
    btn.config(command=lambda c=cheat, b=btn, a=action: set_hotkey(c, b, a))

    

style = ttk.Style()
style.theme_use("default")

style.configure(
    "CustomCombobox.TCombobox",
    fieldbackground="#FFA500", 
    background="#FFA500",   
    foreground="black",         
    arrowcolor="black",         
    borderwidth=0,
    relief="flat",
    selectbackground="#FF8C00",   
    selectforeground="black",   
    padding=4
)

config_dropdown = ttk.Combobox(content_frame, state="readonly", style="CustomCombobox.TCombobox")
config_dropdown.place(relx=0.06, rely=0.9, anchor="w", width=150)
config_dropdown.bind("<<ComboboxSelected>>", lambda e: load_config())


save_btn = tk.Button(content_frame, text="Save", command=lambda: save_config(), 
                     relief="flat", background="#FF914D", foreground="#2A2A2A")
save_btn.place(relx=0.65, rely=0.9, anchor="center")

load_btn = tk.Button(content_frame, text="Load", command=lambda: load_config(), 
                     relief="flat", background="#FF914D", foreground="#2A2A2A")
load_btn.place(relx=0.8, rely=0.9, anchor="center")

# Initialize dropdown
refresh_dropdown()


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
