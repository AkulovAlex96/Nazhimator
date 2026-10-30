"""MCP-сервер Nazhimator: нажатие кнопок через ESP32-C3 и снимок экрана с камеры.

Переменные окружения:
  SERIAL_PORT   необязательно, порт ESP32-C3 (иначе ищется по VID Espressif)
  CAMERA_SOURCE индекс USB-камеры или URL (телефон), см. camera.py (по умолчанию 0)
  CROP          необязательно, "x,y,w,h" - область экрана на кадре
"""

import os
import threading
import time
from typing import Literal

import cv2
import serial
from mcp.server.fastmcp import FastMCP, Image

import camera
from ports import find_port

CROP = os.environ.get("CROP")
MAX_SIDE = 1600
SETTLE_S =0.4  # пауза после нажатия, пока экран обновится

mcp = FastMCP("nazhimator")
_lock = threading.Lock()
_ser: serial.Serial | None = None

Button = Literal["esc", "up", "down", "enter"]


def _serial() -> serial.Serial:
    global _ser
    if _ser is None or not _ser.is_open:
        s = serial.Serial()
        s.port = find_port()
        s.baudrate = 115200
        s.timeout = 1
        # DTR/RTS на USB-CDC ESP32-C3 перезагружают плату
        s.dtr = False
        s.rts = False
        s.open()
        _ser = s
    return _ser


def _send(line: str) -> str:
    with _lock:
        s = _serial()
        s.reset_input_buffer()
        s.write((line + "\n").encode())
        return s.readline().decode().strip()


def _grab() -> bytes:
    frame = camera.grab()
    if CROP:
        x, y, w, h = (int(v) for v in CROP.split(","))
        frame = frame[y : y + h, x : x + w]
    scale = MAX_SIDE / max(frame.shape[:2])
    if scale < 1:  # фото телефона слишком большое для передачи ИИ
        frame = cv2.resize(frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        raise RuntimeError("failed to encode frame")
    return buf.tobytes()


@mcp.tool()
def press(button: Button, ms: int = 100) -> str:
    """Нажать кнопку устройства на ms миллисекунд (макс. 3000)."""
    reply = _send(f"PRESS {button} {ms}")
    if reply != "OK":
        raise RuntimeError(f"device replied: {reply or 'nothing'}")
    return f"pressed {button} for {ms} ms"


@mcp.tool()
def release_all() -> str:
    """Отпустить все кнопки."""
    return _send("RELEASE")


@mcp.tool()
def screenshot() -> Image:
    """Сделать снимок экрана устройства с камеры."""
    return Image(data=_grab(), format="jpeg")


@mcp.tool()
def press_and_look(button: Button, ms: int = 100) -> Image:
    """Нажать кнопку, подождать обновления экрана и вернуть снимок."""
    press(button, ms)
    time.sleep(ms / 1000 + SETTLE_S)
    return Image(data=_grab(), format="jpeg")


if __name__ == "__main__":
    mcp.run()
