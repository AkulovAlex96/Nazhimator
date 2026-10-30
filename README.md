# Nazhimator

ИИ нажимает кнопки устройства (ESP32-C3 замыкает их на землю) и видит экран через камеру.

## Подключение

Общая земля ESP32-C3 и устройства обязательна. Каждый пин паяется к «горячему» контакту кнопки.

| Кнопка | GPIO |
|--------|------|
| esc    | 7    |
| up     | 4    |
| down   | 5    |
| enter  | 6    |

Пины меняются в [firmware/src/main.cpp](firmware/src/main.cpp). GPIO2, 8, 9 не использовать (strapping).

## Прошивка

```
cd firmware && pio run -t upload
pio device monitor     # проверка: PING -> PONG, PRESS up 200 -> OK
```

Протокол: `PRESS <esc|up|down|enter> [ms]`, `RELEASE`, `PING`.

## MCP-сервер

```
cd server
python -m venv .venv && .venv/bin/pip install -r requirements.txt
claude mcp add nazhimator -e CAMERA_SOURCE=0 -- $PWD/.venv/bin/python $PWD/mcp_server.py
```

Инструменты: `press`, `release_all`, `screenshot`, `press_and_look`.
Опциональная переменная `CROP="x,y,w,h"` обрезает кадр до экрана.

## Камера

`CAMERA_SOURCE` (или `--source` в `camera_setup.py`) — одно из:
- индекс USB-камеры: `0`
- URL снимка с телефона: `http://192.168.1.50:8080/shot.jpg`
- MJPEG-поток: `http://192.168.1.50:8080/video`

- `adb` (или `adb:<serial>`) — штатная камера телефона по USB: сервер открывает камеру, нажимает спуск
  и забирает новое фото из `/sdcard/DCIM/Camera`. Нужны включённая отладка по USB и `adb` на ПК.
  Пакет камеры задаётся `ADB_CAMERA_PKG` (по умолчанию `com.oplus.camera`). Каждый кадр остаётся в галерее
  телефона, живого просмотра нет (только `snap` и `crop`).

Телефон по Wi-Fi: на Android приложение «IP Webcam» (Start server), телефон и ПК в одной Wi-Fi-сети.
Заблокируй фокус и экспозицию в приложении, поставь телефон на штатив и подключи питание.

## Настройка камеры

```
.venv/bin/python camera_setup.py snap -o frame.jpg   # сырой кадр в файл
.venv/bin/python camera_setup.py live                # живое окно (q - выход)
.venv/bin/python camera_setup.py crop                # выделить экран мышью -> CROP="x,y,w,h"
```

Полученное значение `CROP` передай в `claude mcp add` через `-e CROP=x,y,w,h`.

Доступ к порту на Linux: `sudo usermod -aG dialout $USER`.
