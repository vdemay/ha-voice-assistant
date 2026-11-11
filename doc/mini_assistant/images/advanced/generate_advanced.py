#!/usr/bin/env python3
"""Generate the "advanced" 360x360 PNG set straight from the source web page.

Renders esp32-cat-eyes-360x360-pngs.html (kept next to this script) in headless
Chrome, extracts every gallery canvas as a data URL, and saves it as
<name>.png in this folder — the exact pixels the page shows, no PIL port to
keep aligned.

Requires Chrome/Chromium (override with the CHROME_BIN env var). Without a
browser, open the HTML page and click its per-image Download buttons instead.
Run:  python3 generate_advanced.py
"""
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "esp32-cat-eyes-360x360-pngs.html")

# Injected before </body>: re-render every gallery entry at full 360x360 and
# dump name -> dataURL as JSON. `order`, `W`, `H`, `prep`, `draws` come from the
# page's own top-level script.
HARNESS = """
<pre id="out"></pre>
<script>
window.addEventListener('load', () => {
  const out = {};
  for (const name of order) {
    const cv = document.createElement('canvas'); cv.width = W; cv.height = H;
    const c = cv.getContext('2d'); prep(c); draws[name](c);
    out[name] = cv.toDataURL('image/png');
  }
  document.getElementById('out').textContent = 'JSONSTART' + JSON.stringify(out) + 'JSONEND';
});
</script>
</body>"""


def chrome_bin():
    env = os.environ.get("CHROME_BIN")
    if env:
        return env
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    sys.exit("Chrome/Chromium not found — set CHROME_BIN, or open the HTML page "
             "and use its Download buttons.")


def main():
    src = open(PAGE).read()
    with tempfile.TemporaryDirectory() as td:
        harness = os.path.join(td, "harness.html")
        with open(harness, "w") as f:
            f.write(src.replace("</body>", HARNESS))
        dom = subprocess.run(
            [chrome_bin(), "--headless=new", "--disable-gpu", "--no-sandbox",
             "--hide-scrollbars", f"--user-data-dir={td}/profile",
             "--virtual-time-budget=5000", "--dump-dom", "file://" + harness],
            capture_output=True, text=True, timeout=120,
        ).stdout
    m = re.search(r"JSONSTART(.*?)JSONEND", dom, re.S)
    if not m:
        sys.exit("could not extract rendered PNGs from the page DOM")
    for name, url in json.loads(m.group(1)).items():
        png = base64.b64decode(url.split(",", 1)[1])
        path = os.path.join(HERE, name + ".png")
        with open(path, "wb") as f:
            f.write(png)
        shrink(path)
        print(f"{name:15s} {os.path.getsize(path):6d} bytes")


def shrink(path):
    """Round-trip to RGB565 (exactly what the display shows anyway), then save
    as a 256-color palette PNG: ~6x smaller on disk, zero visual change on
    the device (these images use <256 distinct RGB565 colors)."""
    im = Image.open(path).convert("RGB")
    r = im.getchannel("R").point(lambda v: (v >> 3) << 3)
    g = im.getchannel("G").point(lambda v: (v >> 2) << 2)
    b = im.getchannel("B").point(lambda v: (v >> 3) << 3)
    im = Image.merge("RGB", (r, g, b))
    im.quantize(colors=256, method=Image.Quantize.MEDIANCUT,
                dither=Image.Dither.NONE).save(path, optimize=True)


if __name__ == "__main__":
    main()
