#!/bin/env python

import sys
import argparse
from valon_synth import Synthesizer, SYNTH_A, SYNTH_B

_VERBOSE = False

parser = argparse.ArgumentParser(description='Set Frequency of Valon Synthesizer')
parser.add_argument('dev', help='The device file of Valon, usally /dev/ttyUSBn')
parser.add_argument('port', choices=['A', 'B'], help='Port of Valon, A or B')
parser.add_argument('freq', type=int, help='Desired frequency in MHz')
parser.add_argument('-l', '--level', type=int, choices=[-4, -1, 2, 5], help='RF output level in dBm')
parser.add_argument('-s', '--store', action='store_true')
opts = parser.parse_args()

if _VERBOSE:
	print('Device:    ' + opts.dev)
	print('Port:      ' + opts.port)
	print('Frequency: %dMHz' % opts.freq)
	print('Out level: %ddBm' % opts.level)

if opts.port == 'A':
	synth = SYNTH_A
else:
	synth = SYNTH_B

syn = Synthesizer(opts.dev)
syn.set_frequency(synth, opts.freq)

print(syn.get_frequency(synth))

if opts.level != None:
	syn.set_rf_level(synth, opts.level)
print(syn.get_rf_level(synth))

if opts.store:
	print('Storing into flash memory ... '),
	syn.flash()
	print('Done.')

