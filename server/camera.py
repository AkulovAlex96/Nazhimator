"""Источник кадров: USB-камера (индекс), MJPEG-поток или URL снимка (телефон).

CAMERA_SOURCE (или устаревшая CAMERA_INDEX):
  0                                 USB-камера с индексом 0
  http://192.168.1.50:8080/shot.jpg URL одиночного снимка (IP Webcam на Android)
  http://192.168.1.50:8080/video    MJPEG-поток
  adb  или  adb:<serial>            штатная камера телефона по adb (ADB_CAMERA_PKG, по умолчанию com.oplus.camera)
"""

import os
import subprocess
import time
import urllib.request
from collections.abc import Iterator

import cv2
import numpy as np

ADB_CAMERA_PKG = os.environ.get("ADB_CAMERA_PKG", "com.oplus.camera")
DEFAULT_SOURCE =os.environ.get("CAMERA_SOURCE") or os.environ.get("CAMERA_INDEX", "0")


def _is_adb(source: str) -> bool:
    return source == "adb" or source.startswith("adb:")


def _is_snapshot(source: str) -> bool:
    return source.startswith("http") and source.split("?")[0].lower().endswith((".jpg", ".jpeg"))


def _fetch_snapshot(url: str) -> np.ndarray:
    with urllib.request.urlopen(url, timeout=5) as r:
        data = r.read()
    frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise RuntimeError(f"snapshot {url} is not an image")
    return frame


def _adb(*args: str, serial: str | None = None) -> bytes:
    cmd = ["adb", *(["-s", serial] if serial else []), *args]
    return subprocess.run(cmd, check=True, capture_output=True, timeout=30).stdout


def _adb_snapshot(serial: str | None) -> np.ndarray:
    """Снимок штатной камерой телефона по adb: запустить камеру, нажать спуск, забрать файл."""
    d = "/sdcard/DCIM/Camera"

    def latest() -> str:
        out = _adb("shell", f"ls -t {d} | head -1", serial=serial).decode().strip()
        return out

    before = latest()
    _adb("shell", "input keyevent KEYCODE_WAKEUP", serial=serial)
    focus = _adb("shell", "dumpsys window | grep mCurrentFocus", serial=serial).decode()
    if "camera" not in focus.lower():
        _adb("shell", f"monkey -p {ADB_CAMERA_PKG} -c android.intent.category.LAUNCHER 1", serial=serial)
        time.sleep(3)
    _adb("shell", "input keyevent KEYCODE_CAMERA", serial=serial)
    for _ in range(20):
        time.sleep(0.5)
        name = latest()
        if name and name != before and not name.startswith("."):
            time.sleep(0.5)  # дождаться записи файла
            data = _adb("exec-out", f"cat {d}/{name}", serial=serial)
            frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
            if frame is not None:
                return frame
    raise RuntimeError("phone did not produce a new photo")


def _open(source: str) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(int(source) if source.isdigit() else source)
    if not cap.isOpened():
        raise RuntimeError(f"camera {source} not available")
    return cap


def grab(source: str = DEFAULT_SOURCE) -> np.ndarray:
    """Один кадр (BGR)."""
    if _is_adb(source):
        return _adb_snapshot(source.partition(":")[2] or None)
    if _is_snapshot(source):
        return _fetch_snapshot(source)
    cap = _open(source)
    try:
        for _ in range(5):  # прогрев автоэкспозиции / сброс буфера потока
            cap.read()
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError("failed to read frame")
        return frame
    finally:
        cap.release()


def frames(source: str = DEFAULT_SOURCE) -> Iterator[np.ndarray]:
    """Непрерывный поток кадров для живого просмотра."""
    if _is_adb(source):
        raise RuntimeError("live view is not available for adb source, use snap")
    if _is_snapshot(source):
        while True:
            yield _fetch_snapshot(source)
    cap = _open(source)
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError("failed to read frame")
            yield frame
    finally:
        cap.release()
