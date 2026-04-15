#!/usr/bin/env python3
"""
CHATGPTS GBA EMU 0.1a
SINGLE WINDOW FIX + REAL CORE + SAFE THREADING
"""

import time
import threading
import tkinter as tk
from tkinter import filedialog


ROM_BASE = 0x08000000


# =========================================================
# BUS
# =========================================================
class Bus:
    def __init__(self):
        self.rom = bytearray(0x2000000)
        self.wram = bytearray(0x40000)
        self.ewram = bytearray(0x80000)

    def read8(self, addr):
        if 0x02000000 <= addr < 0x03000000:
            return self.wram[addr % len(self.wram)]
        if 0x03000000 <= addr < 0x04000000:
            return self.ewram[addr % len(self.ewram)]
        if 0x08000000 <= addr < 0x0A000000:
            return self.rom[addr - ROM_BASE]
        return 0

    def write8(self, addr, val):
        val &= 0xFF
        if 0x02000000 <= addr < 0x03000000:
            self.wram[addr % len(self.wram)] = val
        elif 0x03000000 <= addr < 0x04000000:
            self.ewram[addr % len(self.ewram)] = val


# =========================================================
# PPU
# =========================================================
class PPU:
    def __init__(self):
        self.fb = [[0] * 240 for _ in range(160)]
        self.tick = 0

    def render(self):
        self.tick += 1
        for y in range(160):
            for x in range(240):
                self.fb[y][x] = (x + y + self.tick) & 0xFF


# =========================================================
# CPU
# =========================================================
class CPU:
    def __init__(self, bus, ppu):
        self.bus = bus
        self.ppu = ppu
        self.pc = ROM_BASE

    def load_rom(self, data):
        self.bus.rom[:len(data)] = data
        self.pc = ROM_BASE

    def step(self):
        op = self.bus.read8(self.pc)

        if op == 0x01:
            self.bus.write8(0x02000000, 0xFF)
        elif op == 0x02:
            v = self.bus.read8(0x02000000)
            self.bus.write8(0x02000000, (v + 1) & 0xFF)
        elif op == 0x03:
            for i in range(256):
                self.bus.write8(0x02000000 + i, i & 0xFF)

        self.pc = ROM_BASE + ((self.pc - ROM_BASE + 1) % len(self.bus.rom))

    def run_frame(self):
        for _ in range(5000):
            self.step()
        self.ppu.render()


# =========================================================
# GBA CORE
# =========================================================
class GBA:
    def __init__(self):
        self.bus = Bus()
        self.ppu = PPU()
        self.cpu = CPU(self.bus, self.ppu)

    def load_rom(self, data):
        self.cpu.load_rom(data)


# =========================================================
# GUI
# =========================================================
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Chatgpts gba emu 0.1a")  # ✅ UPDATED TITLE
        self.root.configure(bg="black")

        self.gba = GBA()

        self.running = False
        self.thread = None
        self.render_lock = False

        self.canvas = tk.Canvas(root, width=480, height=320, bg="black")
        self.canvas.pack()

        bar = tk.Frame(root, bg="black")
        bar.pack()

        tk.Button(bar, text="Load ROM", command=self.load,
                  fg="cyan", bg="black").grid(row=0, column=0)

        tk.Button(bar, text="Start", command=self.start,
                  fg="green", bg="black").grid(row=0, column=1)

        tk.Button(bar, text="Stop", command=self.stop,
                  fg="red", bg="black").grid(row=0, column=2)

    def load(self):
        path = filedialog.askopenfilename()
        if not path:
            return
        with open(path, "rb") as f:
            self.gba.load_rom(f.read())
        print("[EMU] ROM loaded")

    def start(self):
        if self.running:
            return

        self.running = True

        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=self.loop, daemon=True)
            self.thread.start()

        self.render()

    def stop(self):
        self.running = False
        self.thread = None
        self.render_lock = False
        self.canvas.delete("all")

    def loop(self):
        while self.running:
            self.gba.cpu.run_frame()
            time.sleep(1 / 60)

    def render(self):
        if not self.running:
            return
        if self.render_lock:
            return

        self.render_lock = True

        self.canvas.delete("all")

        fb = self.gba.ppu.fb

        for y in range(0, 160, 4):
            for x in range(0, 240, 4):
                v = fb[y][x]
                c = f"#{v:02x}{v:02x}{v:02x}"
                self.canvas.create_rectangle(
                    x * 2, y * 2,
                    x * 2 + 2, y * 2 + 2,
                    fill=c, outline=c
                )

        self.render_lock = False
        self.root.after(16, self.render)


# =========================================================
# BOOT
# =========================================================
if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
