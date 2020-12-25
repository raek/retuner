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
        with open_input(config.input_name) as midi_in, \
             open_output(config.output_name) as midi_out:
            run(midi_in, midi_out)
    finally:
        midi.quit()


def read_settings():
    settings_dir = os.path.join(os.environ["HOME"], ".config", "retuner")
    os.makedirs(settings_dir, exist_ok=True)
    with open(os.path.join(settings_dir, "settings.json"), "rt") as f:
        return Settings(**json.load(f))


@contextmanager
def open_input(input_name):
    index = None
    for i in range(midi.get_count()):
        _, name, is_input, _, _ = midi.get_device_info(i)
        if is_input and name.decode("utf8") == input_name:
            index = i
            break
    else:
        raise Exception("Could not find input device: " + input_name)
    midi_in = midi.Input(index)
    try:
        yield midi_in
    finally:
        midi_in.close()


@contextmanager
def open_output(output_name):
    index = None
    for i in range(midi.get_count()):
        _, name, _, is_output, _ = midi.get_device_info(i)
        if is_output and name.decode("utf8") == output_name:
            index = i
            break
    else:
        raise Exception("Could not find output device: " + output_name)
    midi_out = midi.Output(index)
    try:
        midi_out.set_instrument(0)
        yield midi_out
    finally:
        midi_out.close()


def run(midi_in, midi_out):
    while True:
        events = midi_in.read(1)
        for event in events:
            [status, data1, data2, data3], ts = event
            if status & 0xE0 == 0x80:
                event[0][1] = 60
            print(status, data1)
        midi_out.write(events)
        sleep(0.001)


if __name__ == "__main__":
    main()