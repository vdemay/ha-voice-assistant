#!/usr/bin/env python3
"""Generate the status images for with_images_touch_sound.yaml (360x360 PNG).

Simple cat style: white eyes on black with vertical slit pupils.
Drawn at 4x supersampling, then downscaled with LANCZOS for smooth edges.

Phases: idle (3 animated frames: sleeping closed eyes + crescent moon + Zzz)
/ listening / thinking / replying / error / loading.
The 3 idle frames are cycled at runtime by the yaml (idle_frame global).
Run:  python3 generate_images.py
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

SIZE = 360
SS = 4  # supersample factor
OUT = os.path.dirname(os.path.abspath(__file__))

INK = (242, 242, 242)      # soft white
PUPIL = (17, 17, 17)       # near-black
ACCENT = (53, 200, 255)    # cyan (thought dot / spinner dot only)
ERROR = (255, 107, 107)    # soft red

# eye geometry in 360-space
EYE_Y = 150
EX_L, EX_R = 118, 242

# Zzz frames: (x, y, font size, color) per frame — rising and fading,
# first Z bigger than the second, etc. Cluster centered above the eyes.
ZZZ_FRAMES = [
    [(166, 106, 54, INK), (194, 78, 38, INK), (218, 54, 26, INK)],
    [(170, 84, 46, (208, 208, 208)), (196, 58, 32, (208, 208, 208)), (218, 36, 22, (208, 208, 208))],
    [(174, 62, 38, (168, 168, 168)), (198, 40, 26, (168, 168, 168)), (218, 22, 18, (168, 168, 168))],
]


def canvas():
    img = Image.new("RGB", (SIZE * SS, SIZE * SS), (0, 0, 0))
    return img, ImageDraw.Draw(img)


def P(x, y):
    return (x * SS, y * SS)


def B(x, y, rx, ry):
    return (x - rx) * SS, (y - ry) * SS, (x + rx) * SS, (y + ry) * SS


def dot(d, x, y, r, fill):
    d.ellipse([(x - r) * SS, (y - r) * SS, (x + r) * SS, (y + r) * SS], fill=fill)


def line(d, x0, y0, x1, y1, w, fill):
    """Thick line with round caps."""
    d.line([P(x0, y0), P(x1, y1)], fill=fill, width=int(w * SS))
    r = w / 2
    dot(d, x0, y0, r, fill)
    dot(d, x1, y1, r, fill)


def arc(d, x, y, rx, ry, a0, a1, w, fill):
    """Thick arc with round caps. Angles in degrees, 0 = 3 o'clock, clockwise."""
    d.arc(B(x, y, rx, ry), a0, a1, fill=fill, width=int(w * SS))
    for a in (a0, a1):
        rad = math.radians(a)
        px, py = x + rx * math.cos(rad), y + ry * math.sin(rad)
        dot(d, px, py, w / 2, fill)


def ellipse(d, x, y, rx, ry, fill):
    d.ellipse(B(x, y, rx, ry), fill=fill)


def finish(img, name):
    img = img.resize((SIZE, SIZE), Image.LANCZOS)
    path = os.path.join(OUT, name)
    img.save(path, optimize=True)
    print(f"{name:15s} {os.path.getsize(path):6d} bytes")


def cat_eyes(d, rx=46, ry=54, slit_dy=0):
    """White eyes with vertical slit pupils (cat style)."""
    for ex in (EX_L, EX_R):
        ellipse(d, ex, EYE_Y, rx, ry, INK)
        ellipse(d, ex, EYE_Y + slit_dy, 7, 20, PUPIL)  # slit pupil


def closed_eyes(d):
    """Sleeping closed happy eyes (cap shapes)."""
    for ex in (EX_L, EX_R):
        arc(d, ex, EYE_Y + 14, 46, 44, 180, 360, 13, INK)


def moon(d, x=72, y=72, r=28):
    """Crescent (semi) moon, upper-left corner."""
    ellipse(d, x, y, r, r, INK)
    ellipse(d, x + int(r * 0.55), y - int(r * 0.3), int(r * 0.92), int(r * 0.92), (0, 0, 0))


def zzz(d, frame):
    """Zzz cluster for an animation frame: big Z first, smaller ones after."""
    for x, y, s, fill in ZZZ_FRAMES[frame]:
        d.text(P(x, y), "z", font=ImageFont.load_default(size=int(s * SS)), fill=fill)


def img_idle(frame, name):
    """Sleeping mode: closed eyes + crescent moon + animated Zzz frame."""
    img, d = canvas()
    closed_eyes(d)
    moon(d)
    zzz(d, frame)
    finish(img, name)


def img_listening():
    """Wide open cat eyes — listening."""
    img, d = canvas()
    cat_eyes(d, rx=50, ry=64)
    finish(img, "listening.png")


def img_thinking():
    """Slit pupils looking up, raised brows, thought dots."""
    img, d = canvas()
    cat_eyes(d, slit_dy=-12)
    for ex in (EX_L, EX_R):  # raised brows
        line(d, ex - 34, EYE_Y - 76, ex + 30, EYE_Y - 90, 9, INK)
    dot(d, 282, 96, 6, INK)
    dot(d, 302, 70, 8, INK)
    dot(d, 320, 40, 10, ACCENT)
    finish(img, "thinking.png")


def img_replying():
    """Open cat eyes plus a big smile — talking."""
    img, d = canvas()
    cat_eyes(d, ry=52)
    arc(d, 180, 232, 78, 46, 15, 165, 13, INK)  # smile (cup shape)
    finish(img, "replying.png")


def img_error():
    """X eyes and a zigzag mouth in soft red."""
    img, d = canvas()
    for ex in (EX_L, EX_R):
        m = 30
        line(d, ex - m, EYE_Y - m, ex + m, EYE_Y + m, 13, ERROR)
        line(d, ex - m, EYE_Y + m, ex + m, EYE_Y - m, 13, ERROR)
    pts = [(128, 252), (156, 240), (184, 254), (212, 240), (236, 252)]
    d.line([P(*p) for p in pts], fill=ERROR, width=int(11 * SS), joint="curve")
    finish(img, "error.png")


def img_loading():
    """Spinner ring with a gap and a bright dot at the leading edge."""
    img, d = canvas()
    arc(d, 180, 180, 92, 92, 25, 335, 17, INK)
    rad = math.radians(25)
    dot(d, 180 + 92 * math.cos(rad), 180 + 92 * math.sin(rad), 15, ACCENT)
    finish(img, "loading.png")


if __name__ == "__main__":
    img_idle(0, "idle.png")
    img_idle(1, "idle2.png")
    img_idle(2, "idle3.png")
    img_listening()
    img_thinking()
    img_replying()
    img_error()
    img_loading()
