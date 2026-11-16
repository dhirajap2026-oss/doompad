"""
main.py - KMK firmware for a custom 9-key macropad
Hardware: Seeed Studio XIAO RP2040 + 3x3 key matrix + EC11 rotary encoder
          w/ push-switch + 0.91" 128x32 I2C OLED (SSD1306)

All hardware pin assignments were read directly from the KiCad schematic.
Keep them together here so the rest of the file never needs touching if
the PCB doesn't change.
"""

import time

import board
import busio

from kmk.kmk_keyboard import KMKKeyboard
from kmk.keys import KC
from kmk.scanners import DiodeOrientation
from kmk.modules import Module
from kmk.modules.encoder import EncoderHandler

import adafruit_ssd1306

# ---------------------------------------------------------------------------
# HARDWARE PIN MAP  (from schematic — edit only if the PCB changes)
# ---------------------------------------------------------------------------
# Key matrix
MATRIX_ROW_PINS = (board.D0, board.D1, board.D2)     # R1, R2, R3
MATRIX_COL_PINS = (board.D3, board.D9, board.D10)    # C1, C2, C3
DIODE_ORIENTATION = DiodeOrientation.ROW2COL         # diode cathode -> column bus

# Rotary encoder (EC11 + push switch)
# Confirmed by tracing wires on the schematic: D6 -> A, D7 -> B,
# D8 -> switch (S1). Encoder common (C) and S2 both tie to GND directly,
# not a GPIO.
ENCODER_PIN_A = board.D6
ENCODER_PIN_B = board.D7
ENCODER_BTN_PIN = board.D8

# OLED (0.91" 128x32, I2C) -- SDA/SCL match the schematic's OLED_SDA/SCL nets
OLED_SDA = board.SDA   # = D4 on the schematic
OLED_SCL = board.SCL   # = D5 on the schematic
OLED_WIDTH = 128
OLED_HEIGHT = 32
OLED_I2C_ADDR = 0x3C

# ---------------------------------------------------------------------------
# KEYBOARD / MATRIX SETUP
# ---------------------------------------------------------------------------
keyboard = KMKKeyboard()

keyboard.col_pins = MATRIX_COL_PINS
keyboard.row_pins = MATRIX_ROW_PINS
keyboard.diode_orientation = DIODE_ORIENTATION

# ---------------------------------------------------------------------------
# ROTARY ENCODER
# ---------------------------------------------------------------------------
encoder_handler = EncoderHandler()

# Each entry: (pin_a, pin_b, button_pin_or_None, is_inverted)
# Passing a button pin here makes KMK automatically append ONE extra
# "virtual" key to the end of every keymap layer for the switch press.
encoder_handler.pins = (
    (ENCODER_PIN_A, ENCODER_PIN_B, ENCODER_BTN_PIN, False),
)

# Per-layer (CW, CCW) behaviour for each encoder. The button itself is
# handled through the keymap (see the 10th key below), NOT here.
encoder_handler.map = [
    ((KC.VOLU, KC.VOLD),),   # layer 0: clockwise = volume up, CCW = volume down
]

keyboard.modules.append(encoder_handler)

# ---------------------------------------------------------------------------
# KEYMAP
# ---------------------------------------------------------------------------
# 3x3 grid read left-to-right, top-to-bottom (SW1..SW9), plus the encoder
# push-button automatically appended as the 10th entry.
#
# Placeholder keys are KC.N1-KC.N9 so each switch is trivially verifiable
# by typing into any text field. Swap these for real macros/shortcuts later
# -- the grid positions won't change.
keyboard.keymap = [
    [
        KC.N1, KC.N2, KC.N3,
        KC.N4, KC.N5, KC.N6,
        KC.N7, KC.N8, KC.N9,
        KC.MUTE,   # encoder push-switch
    ],
]

# ---------------------------------------------------------------------------
# OLED STATUS DISPLAY (lightweight, non-blocking)
# ---------------------------------------------------------------------------
i2c = busio.I2C(OLED_SCL, OLED_SDA)
oled = adafruit_ssd1306.SSD1306_I2C(
    OLED_WIDTH, OLED_HEIGHT, i2c, addr=OLED_I2C_ADDR
)


class OledStatus(Module):
    """Minimal status screen: shows 'MACROPAD' plus the last key pressed.

    Redraws are throttled (max ~10/sec) and only happen when something
    actually changed, so this never stalls matrix scanning.
    """

    def __init__(self):
        self.last_key = "--"
        self.last_draw = 0.0
        self.dirty = True

    def during_bootup(self, keyboard):
        self._draw()

    def before_matrix_scan(self, keyboard):
        return

    def after_matrix_scan(self, keyboard):
        return

    def process_key(self, keyboard, key, is_pressed, int_coord):
        if is_pressed:
            self.last_key = str(key)
            self.dirty = True
        return key

    def before_hid_send(self, keyboard):
        return

    def after_hid_send(self, keyboard):
        now = time.monotonic()
        if self.dirty and (now - self.last_draw) > 0.1:
            self._draw()
            self.dirty = False
            self.last_draw = now

    def on_powersave_enable(self, keyboard):
        return

    def on_powersave_disable(self, keyboard):
        return

    def _draw(self):
        oled.fill(0)
        oled.text("MACROPAD", 24, 2, 1)
        oled.text("Key: {}".format(self.last_key), 0, 18, 1)
        oled.show()


keyboard.modules.append(OledStatus())

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    keyboard.go()
