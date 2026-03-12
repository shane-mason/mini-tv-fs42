#!/usr/bin/env python3
"""
Rotary Encoder Reader for Raspberry Pi 5
Reads an EC11 rotary encoders and sends control commands to FS42 in response.

Wiring:
  Encoder 1 (3-pin side):
    - GND -> Pi GND
    - CLK (A) -> GPIO17
    - DT (B) -> GPIO18
  Encoder 1 (2-pin side):
    - SW -> GPIO27
    - GND -> Pi GND

  Encoder 2 (3-pin side):
    - GND -> Pi GND
    - CLK (A) -> GPIO22
    - DT (B) -> GPIO23
  Encoder 2 (2-pin side):
    - SW -> GPIO24
    - GND -> Pi GND
"""
import json
import os
from signal import pause
import subprocess
import urllib.request
import urllib.error

# Configure lgpio backend for Pi 5 compatibility
from gpiozero import Device
from gpiozero.pins.lgpio import LGPIOFactory
Device.pin_factory = LGPIOFactory()

from gpiozero import RotaryEncoder, Button

FS42_HOST = os.getenv('FS42_HOST', '127.0.0.1')
FS42_PORT = os.getenv('FS42_PORT', '4242')
FS42_BASE_URL = f"http://{FS42_HOST}:{FS42_PORT}"

# GPIO pin assignments
ENCODER1_CLK = 17
ENCODER1_DT = 18
ENCODER1_SW = 27

ENCODER2_CLK = 22
ENCODER2_DT = 23
ENCODER2_SW = 24

# Create encoder and button objects
encoder1 = RotaryEncoder(ENCODER1_CLK, ENCODER1_DT, max_steps=0)
button1 = Button(ENCODER1_SW, pull_up=True, bounce_time=0.05)

encoder2 = RotaryEncoder(ENCODER2_CLK, ENCODER2_DT, max_steps=0)
button2 = Button(ENCODER2_SW, pull_up=True, bounce_time=0.05)

# Track positions
position1 = 0
position2 = 0
SYSTEMCTL_TO_TOGGLE = [
    'fs42.service',           # Field Player
]

USE_SYSTEMCTL = True

def toggle_services():
    """Toggle FieldStation42 services on/off"""

    try:
        # Check if fs42.service is active to determine current state
        result = subprocess.run(
            ['systemctl', '--user', 'is-active', 'fs42.service'],
            capture_output=True,
            text=True,
            timeout=5
        )

        services_active = result.stdout.strip() == 'active'

        if services_active:
            # Services are running, stop them
            for service in SYSTEMCTL_TO_TOGGLE:
                try:

                    subprocess.Popen(
                        ['systemctl', '--user', 'stop', service],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    print(f"Stopping {service}")
                except Exception as e:
                    print(f"Error stopping {service}: {e}")
        else:
            # Services are not running, start them
            for service in SYSTEMCTL_TO_TOGGLE:
                try:

                    subprocess.Popen(
                        ['systemctl', '--user', 'start', service],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    print(f"Starting {service}")
                except Exception as e:
                    print(f"Error starting {service}: {e}")

    except subprocess.TimeoutExpired:
        print("Error: systemctl command timed out")
    except Exception as e:
        print(f"Error toggling services: {e}")


def channel_up():
    """Change to next channel"""
    try:
        url = f"{FS42_BASE_URL}/player/channels/up"
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=2) as response:
            result = json.loads(response.read().decode())
            print(f"Channel: {result.get('command', 'up')}")
    except urllib.error.URLError as e:
        print(f"Channel up failed: {e}")
    except Exception as e:
        print(f"Channel up error: {e}")


def channel_down():
    """Change to previous channel"""
    try:
        url = f"{FS42_BASE_URL}/player/channels/down"
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=2) as response:
            result = json.loads(response.read().decode())
            print(f"Channel: {result.get('command', 'down')}")
    except urllib.error.URLError as e:
        print(f"Channel down failed: {e}")
    except Exception as e:
        print(f"Channel down error: {e}")


def volume_up():
    """Increase volume"""
    try:
        url = f"{FS42_BASE_URL}/player/volume/up"
        req = urllib.request.Request(url, method='POST')
        with urllib.request.urlopen(req, timeout=2) as response:
            result = json.loads(response.read().decode())
            print(f"Volume: {result.get('volume', 'unknown')}")
    except urllib.error.URLError as e:
        print(f"Volume up failed: {e}")
    except Exception as e:
        print(f"Volume up error: {e}")


def volume_down():
    """Decrease volume"""
    try:
        url = f"{FS42_BASE_URL}/player/volume/down"
        req = urllib.request.Request(url, method='POST')
        with urllib.request.urlopen(req, timeout=2) as response:
            result = json.loads(response.read().decode())
            print(f"Volume: {result.get('volume', 'unknown')}")
    except urllib.error.URLError as e:
        print(f"Volume down failed: {e}")
    except Exception as e:
        print(f"Volume down error: {e}")


def volume_mute():
    """Toggle mute"""
    try:
        url = f"{FS42_BASE_URL}/player/volume/mute"
        req = urllib.request.Request(url, method='POST')
        with urllib.request.urlopen(req, timeout=2) as response:
            result = json.loads(response.read().decode())
            print(f"Mute: {result.get('volume', 'toggled')}")
    except urllib.error.URLError as e:
        print(f"Mute failed: {e}")
    except Exception as e:
        print(f"Mute error: {e}")


def make_rotate_handler(encoder_num):
    def on_rotate_cw():
        global position1, position2
        if encoder_num == 1:
            position1 += 1
            print(f"Encoder 1: {position1:4d}  [CW ->]")
            channel_up()
        else:
            position2 += 1
            print(f"Encoder 2: {position2:4d}  [CW ->]")
            volume_up()

    def on_rotate_ccw():
        global position1, position2
        if encoder_num == 1:
            position1 -= 1
            print(f"Encoder 1: {position1:4d}  [<- CCW]")
            channel_down()
        else:
            position2 -= 1
            print(f"Encoder 2: {position2:4d}  [<- CCW]")
            volume_down()

    return on_rotate_cw, on_rotate_ccw


def make_button_handler(encoder_num):
    def on_press():
        global position1, position2
        if encoder_num == 1:
            print(f"Button 1 pressed! Resetting from {position1} to 0")
            position1 = 0
            toggle_services()
        else:
            print(f"Button 2 pressed! Toggling mute")
            position2 = 0
            volume_mute()

    def on_release():
        print(f"Button {encoder_num} released")

    return on_press, on_release


# Attach callbacks for encoder 1
cw1, ccw1 = make_rotate_handler(1)
press1, release1 = make_button_handler(1)
encoder1.when_rotated_clockwise = cw1
encoder1.when_rotated_counter_clockwise = ccw1
button1.when_pressed = press1
button1.when_released = release1

# Attach callbacks for encoder 2
cw2, ccw2 = make_rotate_handler(2)
press2, release2 = make_button_handler(2)
encoder2.when_rotated_clockwise = cw2
encoder2.when_rotated_counter_clockwise = ccw2
button2.when_pressed = press2
button2.when_released = release2

print("Dual Rotary Encoder Reader")
print("=" * 40)
print(f"Encoder 1: CLK=GPIO{ENCODER1_CLK}, DT=GPIO{ENCODER1_DT}, SW=GPIO{ENCODER1_SW}")
print(f"  - Rotate: Channel up/down")
print(f"  - Press: Toggle FS42 services")
print(f"Encoder 2: CLK=GPIO{ENCODER2_CLK}, DT=GPIO{ENCODER2_DT}, SW=GPIO{ENCODER2_SW}")
print(f"  - Rotate: Volume up/down")
print(f"  - Press: Toggle mute")
print(f"FS42 Server: {FS42_BASE_URL}")
print("Press Ctrl+C to exit")
print("=" * 40)

if __name__ == '__main__':
    try:
        pause()
    except KeyboardInterrupt:
        print("\nExiting...")