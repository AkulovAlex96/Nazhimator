// Nazhimator: эмуляция кнопок (замыкание на землю) по командам из USB-serial.
//
// Протокол (строки, \n в конце):
//   PRESS <esc|up|down|enter> [ms]   -> OK | ERR ...   (ms по умолчанию 100, максимум MAX_PRESS_MS)
//   RELEASE                          -> OK             (отпустить все)
//   PING                             -> PONG
//
// Нажатие: пин OUTPUT + LOW. Отпускание: пин INPUT (Hi-Z). HIGH не выставляем никогда.

#include <Arduino.h>

struct Button {
  const char *name;
  uint8_t pin;
  bool pressed;
  uint32_t releaseAt;
};

// Не используем strapping-пины C3: GPIO2, 8, 9.
Button buttons[] = {
    {"esc", 8, false, 0},
    {"up", 7, false, 0},
    {"down", 6, false, 0},
    {"enter", 5, false, 0},
};
const size_t N_BUTTONS = sizeof(buttons) / sizeof(buttons[0]);

const uint32_t DEFAULT_PRESS_MS = 100;
const uint32_t MAX_PRESS_MS = 3000;

void release(Button &b) {
  pinMode(b.pin, INPUT);
  b.pressed = false;
}

void press(Button &b, uint32_t ms) {
  digitalWrite(b.pin, LOW);
  pinMode(b.pin, OUTPUT);
  b.pressed = true;
  b.releaseAt = millis() + ms;
}

Button *find(const String &name) {
  for (auto &b : buttons)
    if (name.equalsIgnoreCase(b.name)) return &b;
  return nullptr;
}

void handle(String line) {
  line.trim();
  if (line.length() == 0) return;

  if (line.equalsIgnoreCase("PING")) {
    Serial.println("PONG");
    return;
  }
  if (line.equalsIgnoreCase("RELEASE")) {
    for (auto &b : buttons) release(b);
    Serial.println("OK");
    return;
  }

  int sp1 = line.indexOf(' ');
  String cmd = sp1 < 0 ? line : line.substring(0, sp1);
  if (!cmd.equalsIgnoreCase("PRESS") || sp1 < 0) {
    Serial.println("ERR unknown command");
    return;
  }

  String rest = line.substring(sp1 + 1);
  rest.trim();
  int sp2 = rest.indexOf(' ');
  String name = sp2 < 0 ? rest : rest.substring(0, sp2);
  uint32_t ms = DEFAULT_PRESS_MS;
  if (sp2 >= 0) {
    long v = rest.substring(sp2 + 1).toInt();
    if (v <= 0) {
      Serial.println("ERR bad duration");
      return;
    }
    ms = min((uint32_t)v, MAX_PRESS_MS);
  }

  Button *b = find(name);
  if (!b) {
    Serial.println("ERR unknown button");
    return;
  }
  press(*b, ms);
  Serial.println("OK");
}

void setup() {
  for (auto &b : buttons) release(b);
  Serial.begin(115200);
}

void loop() {
  static String buf;
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      handle(buf);
      buf = "";
    } else if (buf.length() < 64) {
      buf += c;
    }
  }

  uint32_t now = millis();
  for (auto &b : buttons)
    if (b.pressed && (int32_t)(now - b.releaseAt) >= 0) release(b);
}
