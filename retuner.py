from collections import namedtuple
from contextlib import contextmanager
import json
import os
import sys
from time import sleep

from pygame import midi


class UserError(Exception):
    pass


Settings = namedtuple("Settings", "input_name, output_name")


def main():
    config = read_settings()
    with midi_inited(), \
         open_midi_device(config.input_name, "in") as midi_in, \
         open_midi_device(config.output_name, "out") as midi_out:
        run(midi_in, midi_out)


def read_settings():
    settings_dir = os.path.join(os.environ["HOME"], ".config", "retuner")
    os.makedirs(settings_dir, exist_ok=True)
    with open(os.path.join(settings_dir, "settings.json"), "rt") as f:
        return Settings(**json.load(f))


@contextmanager
def midi_inited():
    midi.init()
    try:
        yield
    finally:
        midi.quit()


@contextmanager
def open_midi_device(device_name, direction):
    assert direction in ["in", "out"]
    index = find_midi_device(device_name, direction)
    constructor = midi.Input if direction == "in" else midi.Output
    try:
        midi_device = constructor(index)
    except midi.MidiException as e:
        raise UserError("Could not open {} device \"{}\": {}".format(direction.upper(), device_name, str(e)))
    try:
        yield midi_device
    finally:
        midi_device.close()


def find_midi_device(device_name, direction):
    for index in range(midi.get_count()):
        _, name, is_input, is_output, _ = midi.get_device_info(index)
        name = name.decode("utf8")
        if name == device_name:
            if ((is_input and direction == "in") or
                (is_output and direction == "out")):
                return index
    raise UserError("Could not find {} device \"{}\"".format(direction.upper(), device_name))


def run(midi_in, midi_out):
    channel = 0
    while True:
        events = midi_in.read(1)
        for event in events:
            [status, data1, data2, data3], ts = event
            if status & 0xE0 == 0x80:  # down or up
                channel = data1 % 12
                if channel == 9:
                    channel = 12
                event[0][0] = (status & 0xF0) | channel
            if status & 0xF0 == 0x90:  # down
                if data1 % 12 == 11:
                    bend = -2048
                else:
                    bend = 0
                midi_out.pitch_bend(bend, channel)
            midi_out.write([event])
        sleep(0.001)


if __name__ == "__main__":
    try:
        main()
    except UserError as e:
        print(e)
        sys.exit(1)
