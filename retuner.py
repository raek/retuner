from collections import namedtuple
from contextlib import contextmanager
import json
import os
from time import sleep

from pygame import midi


Settings = namedtuple("Settings", "input_name, output_name")


def main():
    midi.init()
    try:
        config = read_settings()
        with open_midi_device(config.input_name, "in") as midi_in, \
             open_midi_device(config.output_name, "out") as midi_out:
            run(midi_in, midi_out)
    finally:
        midi.quit()


def read_settings():
    settings_dir = os.path.join(os.environ["HOME"], ".config", "retuner")
    os.makedirs(settings_dir, exist_ok=True)
    with open(os.path.join(settings_dir, "settings.json"), "rt") as f:
        return Settings(**json.load(f))


@contextmanager
def open_midi_device(device_name, direction):
    index = None
    for i in range(midi.get_count()):
        _, name, is_input, is_output, _ = midi.get_device_info(i)
        name = name.decode("utf8")
        if is_input and direction == "in" and name == device_name:
            index = i
            break
        elif is_output and direction == "out" and name == device_name:
            index = i
            break
    else:
        raise Exception("Could not find {} device: {}".format(direction, device_name))
    midi_device = midi.Input(index) if direction == "in" else midi.Output(index)
    try:
        yield midi_device
    finally:
        midi_device.close()


def run(midi_in, midi_out):
    channel = 0
    while True:
        events = midi_in.read(1)
        for event in events:
            [status, data1, data2, data3], ts = event
            if status & 0xF0 == 0x90:  # down
                channel = status & 0x0F
                if data1 % 12 == 11:
                    bend = -2048
                else:
                    bend = 0
                midi_out.pitch_bend(bend, channel)
            midi_out.write([event])
        sleep(0.001)


if __name__ == "__main__":
    main()