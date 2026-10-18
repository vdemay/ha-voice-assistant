#!/usr/bin/env python3
"""
LED light pattern like Google Home
Controlled by linux-voice-assistant WebSocket events
"""

import asyncio
import json
import time
import threading
import websockets

try:
    import queue as Queue
except ImportError:
    import Queue as Queue

from apa102_pi.driver import apa102


class Pixels:
    PIXELS_N = 3

    def __init__(self):
        self.basis = [0] * 3 * self.PIXELS_N
        self.basis[0] = 2
        self.basis[3] = 1
        self.basis[4] = 1
        self.basis[7] = 2

        self.colors = [0] * 3 * self.PIXELS_N
        self.dev = apa102.APA102(num_led=self.PIXELS_N)

        self.next = threading.Event()
        self.queue = Queue.Queue()
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()

    def wakeup(self, direction=0):
        def f():
            self._wakeup(direction)
        self.next.set()
        self.queue.put(f)

    def listen(self):
        self.next.set()
        self.queue.put(self._listen)

    def think(self):
        self.next.set()
        self.queue.put(self._think)

    def speak(self):
        self.next.set()
        self.queue.put(self._speak)

    def off(self):
        self.next.set()
        self.queue.put(self._off)

    def _run(self):
        while True:
            func = self.queue.get()
            func()

    def _wakeup(self, direction=0):
        for i in range(1, 25):
            colors = [i * v for v in self.basis]
            self.write(colors)
            time.sleep(0.01)
        self.colors = colors

    def _listen(self):
        for i in range(1, 25):
            colors = [i * v for v in self.basis]
            self.write(colors)
            time.sleep(0.01)
        self.colors = colors

    def _think(self):
        colors = self.colors
        self.next.clear()
        while not self.next.is_set():
            colors = colors[3:] + colors[:3]
            self.write(colors)
            time.sleep(0.2)
        t = 0.1
        for i in range(0, 5):
            colors = colors[3:] + colors[:3]
            self.write([(v * (4 - i) / 4) for v in colors])
            time.sleep(t)
            t /= 2
        self.colors = colors

    def _speak(self):
        colors = self.colors
        gradient = -1
        position = 24
        self.next.clear()
        while not self.next.is_set():
            position += gradient
            self.write([(v * position / 24) for v in colors])
            if position == 24 or position == 4:
                gradient = -gradient
                time.sleep(0.2)
            else:
                time.sleep(0.01)
        while position > 0:
            position -= 1
            self.write([(v * position / 24) for v in colors])
            time.sleep(0.01)

    def _off(self):
        self.write([0] * 3 * self.PIXELS_N)

    def write(self, colors):
        for i in range(self.PIXELS_N):
            self.dev.set_pixel(
                i,
                int(colors[3 * i]),
                int(colors[3 * i + 1]),
                int(colors[3 * i + 2]),
            )
        self.dev.show()


pixels = Pixels()


async def main():
    uri = "ws://localhost:6055"
    print("Connecting to LVA…")

    async with websockets.connect(uri) as ws:
        print("Connected")
        async for raw in ws:
            msg = json.loads(raw)
            event = msg.get("event")
            print(f"→ {event}")

            if event == "wake_word_detected":
                pixels.wakeup()
            elif event == "listening":
                pixels.listen()
            elif event == "thinking":
                pixels.think()
            elif event == "tts_speaking":
                pixels.speak()
            elif event in ("idle", "tts_finished", "error"):
                pixels.off()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped")
    finally:
        pixels.off()
        time.sleep(0.2)
