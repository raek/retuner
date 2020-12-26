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


# We use pitch bend to retune the individual 12 notes, so then need to be
# in their own channels (pitch bend acts on a whole channel).
NOTE_TO_CHANNEL = list(range(0, 12))
# MIDI Channel 10 (9 in protocol) is reserved for drums, so use 13 instead (12 in protocol).
NOTE_TO_CHANNEL[9] = 12

# A tuning is a mapping from note to difference from 12-TET in cents
RAST_TUNING = [0] * 12
RAST_TUNING[11] = -50

BAYATI_TUNING = [0] * 12
BAYATI_TUNING[2] = -50
BAYATI_TUNING[9] = 50

# Pythagorean tuning with D as base note
PYTHAGOREAN_TUNING = [
    -3.91,
    9.78,
    0,
    -9.78,
    3.91,
    -5.87,
    7.82,
    -1.96,
    11.73,
    1.96,
    -7.82,
    5.87,
]


def run(midi_in, midi_out):
    apply_tuning(midi_out, PYTHAGOREAN_TUNING)
    while True:
        events = midi_in.read(1)
        for in_event in events:
            out_event = remap_channel(in_event)
            midi_out.write([out_event])
        sleep(0.001)


def apply_tuning(midi_out, tuning):
    for note, diff in enumerate(tuning):
        channel = NOTE_TO_CHANNEL[note]
        bend = round((diff * 4096) / 100)
        midi_out.pitch_bend(bend, channel)


def remap_channel(in_event):
    [in_status, data1, data2, data3], ts = in_event
    if in_status & 0xE0 == 0x80:  # down or up
        channel = NOTE_TO_CHANNEL[data1 % 12]
        out_status = (in_status & 0xF0) | channel
    else:
        out_status = in_status
    return [[out_status, data1, data2, data3], ts]


if __name__ == "__main__":
    try:
        main()
    except UserError as e:
        print(e)
        sys.exit(1)
