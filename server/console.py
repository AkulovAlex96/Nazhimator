"""Ручная консоль Nazhimator: нажимай кнопки устройства с клавиатуры.

  ↑ ↓      up / down
  Enter    enter
  Esc      esc
  1-9      длительность нажатия (1=50мс ... 9=2с), по умолчанию 200мс
  p        PING
  q        выход (Ctrl+C тоже)

Порт ищется автоматически по VID Espressif; SERIAL_PORT задаёт его явно.
Не запускай одновременно с MCP-сервером, если он держит порт.
"""

import os
import select
import sys
import termios
import time
import tty

import serial

from ports import find_port


PORT = find_port()
DURATIONS = {"1": 50, "2": 100, "3": 200, "4": 300, "5": 500, "6": 800, "7": 1000, "8": 1500, "9": 2000}

KEYS = {"\x1b[A": "up", "\x1b[B": "down", "\r": "enter", "\n": "enter"}


def read_key() -> str:
    # os.read вместо sys.stdin.read: буфер Python прячет байты от select
    fd = sys.stdin.fileno()
    seq = os.read(fd, 1).decode(errors="ignore")
    if seq != "\x1b":
        return seq
    # одиночный Esc или начало последовательности стрелки
    while select.select([fd], [], [], 0.05)[0]:
        seq += os.read(fd, 8).decode(errors="ignore")
    # стрелки бывают в виде ESC [ A или ESC O A (application mode)
    return seq.replace("\x1bO", "\x1b[")


GAP_S = 0.15  # пауза между нажатиями, иначе плата склеивает их в одно


def press(ser: serial.Serial, name: str, ms: int) -> str:
    """Нажать и дождаться отпускания + паузы: нажатия не склеиваются и не теряются."""
    reply = send(ser, f"PRESS {name} {ms}")
    time.sleep(ms / 1000 + GAP_S)
    return reply


def send(ser: serial.Serial, line: str) -> str:
    ser.reset_input_buffer()
    ser.write((line + "\n").encode())
    return ser.readline().decode().strip() or "(нет ответа)"


def main() -> None:
    ser = serial.Serial()
    ser.port, ser.baudrate, ser.timeout = PORT, 115200, 1
    ser.dtr = ser.rts = False  # иначе USB-CDC ESP32-C3 перезагружается
    ser.open()

    ms = 200
    print(f"{PORT}: {send(ser, 'PING')}\r")
    print("↑ ↓ Enter Esc - нажать | 1-9 длительность | p ping | q выход\r")

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while True:
            key = read_key()
            if key in ("q", "\x03"):
                break
            if key in DURATIONS:
                ms = DURATIONS[key]
                print(f"длительность {ms} мс\r")
            elif key == "p":
                print(f"PING -> {send(ser, 'PING')}\r")
            elif key == "\x1b":
                print(f"esc -> {press(ser, 'esc', ms)}\r")
            elif key in KEYS:
                name = KEYS[key]
                print(f"{name} -> {press(ser, name, ms)}\r")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        send(ser, "RELEASE")
        ser.close()


if __name__ == "__main__":
    main()
