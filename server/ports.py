"""Поиск порта ESP32-C3: номер ttyACM меняется при переподключении USB."""

import os

from serial.tools import list_ports

ESPRESSIF_VID = 0x303A


def find_port() -> str:
    """SERIAL_PORT из окружения, иначе первое устройство Espressif."""
    if os.environ.get("SERIAL_PORT"):
        return os.environ["SERIAL_PORT"]
    for p in list_ports.comports():
        if p.vid == ESPRESSIF_VID:
            return p.device
    raise RuntimeError("ESP32 (VID 303a) не найдена, подключи плату или задай SERIAL_PORT")
