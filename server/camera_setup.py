"""Настройка камеры вручную.

  python camera_setup.py snap [-o frame.jpg]   сохранить сырой кадр (без CROP)
  python camera_setup.py live                  живое окно, q - выход
  python camera_setup.py crop                  выделить мышью экран, печатает CROP="x,y,w,h"

Источник: --source (индекс камеры или URL) или переменная CAMERA_SOURCE, см. camera.py.
"""

import argparse

import cv2

import camera


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["snap", "live", "crop"])
    p.add_argument("-o", "--output", default="frame.jpg")
    p.add_argument("--source", default=camera.DEFAULT_SOURCE)
    args = p.parse_args()

    try:
        if args.mode == "snap":
            cv2.imwrite(args.output, camera.grab(args.source))
            print(f"saved {args.output}")
        elif args.mode == "live":
            for frame in camera.frames(args.source):
                cv2.imshow("camera (q to quit)", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        else:
            x, y, w, h = cv2.selectROI("select screen, Enter to confirm", camera.grab(args.source))
            if w and h:
                print(f'CROP="{x},{y},{w},{h}"')
            else:
                print("nothing selected")
    except RuntimeError as e:
        raise SystemExit(str(e))
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
