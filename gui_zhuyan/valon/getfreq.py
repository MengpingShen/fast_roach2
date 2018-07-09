#!/bin/env python

import sys
import argparse
from valon_synth import Synthesizer, SYNTH_A, SYNTH_B

parser = argparse.ArgumentParser(description='Get Frequency of Valon Synthesizer')
parser.add_argument('dev', help='The device file of Valon, usally /dev/ttyUSBn')
opts = parser.parse_args()

syn = Synthesizer(opts.dev)
print('A: %f %d' % (syn.get_frequency(SYNTH_A), syn.get_rf_level(SYNTH_A)))
print('B: %f %d' % (syn.get_frequency(SYNTH_B), syn.get_rf_level(SYNTH_B)))
