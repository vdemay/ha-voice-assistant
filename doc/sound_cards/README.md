commit/push# Sound Cards

The voice assistant Pi uses two separate audio devices:

Role               | Device                                                                    | Notes
------------------ | ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Output (speaker)   | KEYESTUDIO ReSpeaker 2 Mic Pi Hat V1.0                                    | HAT for Raspberry Pi 4 / Zero / Zero W / 3B / 2B / B+. Used here for playback through its 3.5mm speaker jack. [Amazon FR](https://www.amazon.fr/dp/B07H3T8SQY?ref=ppx_yo2ov_dt_b_fed_asin_title)
Input (microphone) | USB conference microphone (Jieli Technology "UACDemoV1.0" USB audio chip) | Cheap desktop conference mic. Works, but the Jieli chip is picky under PipeWire -- see the [troubleshooting section](#troubleshooting-the-jieli-usb-microphone) below. [Amazon FR](https://www.amazon.fr/dp/B0FY38DKFD?ref=ppx_yo2ov_dt_b_fed_asin_title)

The devices as they appear on the system (`lsusb`, `wpctl status`):

- The USB mic shows up as `Bus 001 Device 004: ID 4c4a:4155 Jieli Technology UACDemoV1.0`.
- Under PipeWire it appears as source `UACDemoV1.0 Mono`.

# Quick sanity check

Confirm both devices are visible and set as defaults:

```bash
lsusb
wpctl status
```

- Under **Sinks**: the ReSpeaker output should be the default (marked `*`).
- Under **Sources**: `UACDemoV1.0 Mono` should be the default (marked `*`).

If not, set the defaults with the numeric IDs shown by `wpctl status`:

```bash
wpctl set-default <sink-id>    # output
wpctl set-default <source-id>  # input
```

Test playback and capture:

```bash
# playback through the ReSpeaker
speaker-test -t wav -c 1

# capture 8 s from the USB mic
timeout 8 pw-record --rate 48000 --channels 1 --format s16 /tmp/test.wav; echo exit:$?

# play it back to confirm it is not silence
aplay /tmp/test.wav
```

`pw-record` should exit before the 8 s timeout. If it hangs until the timeout kills it (`exit:124`), see below.

# Troubleshooting the Jieli USB microphone

Symptom: `pw-record` hangs forever (killed only by `timeout`, exit code 124) even though the mic works with raw ALSA. The Jieli UACDemo chip misbehaves with PipeWire's default ALSA tuning. The fix that made it work reliably:

## 1\. Reset the USB device with the correct bus/device numbers

`usbreset` needs the numbers from `lsusb`, not a guessed value:

```bash
lsusb
# Bus 001 Device 004: ID 4c4a:4155 Jieli Technology UACDemoV1.0
sudo usbreset 001/004
```

## 2\. Tune ALSA parameters for this card via WirePlumber

Create a WirePlumber override so PipeWire opens the Jieli device with conservative ALSA parameters (no mmap, small periods, no auto-suspend):

```bash
mkdir -p ~/.config/wireplumber/wireplumber.conf.d

cat > ~/.config/wireplumber/wireplumber.conf.d/51-uacdemo.conf << 'EOF'
monitor.alsa.rules = [
  {
    matches = [
      { device.name = "~alsa_card.usb-Jieli_Technology_UACDemoV1.0*" }
    ]
    actions = {
      update-props = {
        api.alsa.period-size   = 512
        api.alsa.period-num    = 4
        api.alsa.headroom      = 512
        api.alsa.disable-mmap  = true
        session.suspend-timeout-seconds = 0
      }
    }
  }
]
EOF
```

## 3\. Restart the audio stack and re-select the mic

```bash
systemctl --user restart wireplumber pipewire pipewire-pulse
sleep 3

wpctl status | grep -A 6 "Sources:"
# note the new ID of "UACDemoV1.0 Mono", then:
wpctl set-default <new-id>
```

## 4\. Retest capture

```bash
timeout 8 pw-record --rate 48000 --channels 1 --format s16 /tmp/test.wav; echo exit:$?
aplay /tmp/test.wav   # confirm the recording is real audio, not silence
```

It can take a USB reset (step 1) plus a service restart before the first capture succeeds. Once `pw-record` returns before the timeout and the playback contains audio, the problem is solved.

## 5\. Verify the path used by the assistant

The assistant talks to PulseAudio/PipeWire (via the `soundcard` library), so also confirm the PulseAudio-compatible entry point works:

```bash
timeout 8 arecord -D pulse -d 5 -r 48000 -f S16_LE -c 1 /tmp/test-arecord.wav
aplay /tmp/test-arecord.wav
```

If both `arecord -D pulse` and the assistant run correctly, audio setup is complete.

## If it still hangs

- Watch kernel errors while testing: run `sudo dmesg -w` in one terminal and the failing `pw-record` in another; look for `usb`, `xhci`, `snd`, or `bandwidth` messages.
- Try a different USB port -- ideally a direct USB 2 port, not a hub.
- Fall back to plain PulseAudio (also supported by the project):

  ```bash
  systemctl --user stop wireplumber pipewire pipewire-pulse
  sudo apt install --reinstall pulseaudio pulseaudio-utils
  systemctl --user enable --now pulseaudio
  # then retest with arecord -D pulse
  ```

- If nothing helps, this Jieli dongle is likely just unreliable with PipeWire on the Pi; a different USB mic (or a ReSpeaker HAT mic) is the pragmatic fix.
