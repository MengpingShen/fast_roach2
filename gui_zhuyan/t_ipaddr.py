#!/usr/bin/env python

'''
    Testing ipaddr generate block
'''

import time
import struct
import socket
import logging
import argparse

import log_handlers
import katcp_wrapper


bitstream = 't_ipaddr2_2016_Nov_23_1553.bof.gz'
roach = 'r1510'
katcp_port = 7147


# Generate network addresses
mac_base = (2<<40) + (2<<32)
xgbe_devices = (0, 1, 2, 3)

fabric_ip_string = {}
fabric_ip = {}
fabric_port = {}
for i in xgbe_devices:
    fabric_ip_string[i] = '10.0.%d.227' % (i+1)
    fabric_ip[i] = struct.unpack('!L',socket.inet_aton(fabric_ip_string[i]))[0]  # convert ip to long
    fabric_port[i] = 33333


dest_ip_string = {}
dest_ip = {}
dest_port = 50000
for i in xgbe_devices:
    dest_ip_string[i] = '10.0.%d.127' % (i+1)
    dest_ip[i] = socket.inet_aton(dest_ip_string[i])

ipall = ''
for n in range(16):
    for i in xgbe_devices:
        ipall += dest_ip[i] + struct.pack('!HH', dest_port+n, 0)



def exit_fail(e):
    print('FAILURE DETECTED.')
    print('Exception:')
    print(e)
    print('Log entries:')
    lh.printMessages()
    try:
        fpga.stop()
        sock.close()
    except: pass
    exit()


def exit_clean():
    try:
        fpga.stop()
        sock.close()
    except: pass
    exit()


if __name__ == '__main__':

    try:
        lh = log_handlers.DebugLogHandler()
        logger = logging.getLogger(roach)
        logger.addHandler(lh)
        logger.setLevel(10)

        parser = argparse.ArgumentParser()
        parser.add_argument('-s', '--skip', action='store_true', default=False, help='Skip programming FPGA')
        args = parser.parse_args()

        print('Connecting to server %s on port %i... ' % (roach, katcp_port)),
        fpga = katcp_wrapper.FpgaClient(roach, katcp_port, timeout=10, logger=logger)
        time.sleep(0.1)

        if fpga.is_connected():
            print('ok')
        else:
            print('ERROR connecting to server %s on port %i.\n' % (roach,katcp_port))
            exit_fail()

        print('-' * 20)

        if not args.skip:
            print('Programming FPGA with  %s ... ' % bitstream),
            fpga.progdev(bitstream)
            print('done')

        for i in (0, ):
            xgbe_name = 'ens0p%d' % i
            mac_addr = mac_base + fabric_ip[i]
            print('Initialize %s fabric mac: %s, ip: %s, port: %i ...' %
                (xgbe_name, ':'.join(("%012X" % mac_addr)[i:i+2] for i in range(0, 12, 2)),
                 fabric_ip_string[i], fabric_port[i])),
            fpga.tap_start(xgbe_name, xgbe_name + '_core', mac_addr, fabric_ip[i], fabric_port[i])
            print('done')

        print('Filling destnation IP address pool ... '),
        fpga.write('ipaddr_pool', ipall)
        print('done')

        print('Issue reset signal...'),
        fpga.write_int('reset', 0)
        fpga.write_int('reset', 1)
        print('done')

        while True:
            print(bin(fpga.read_uint('tx_overflow')))
            time.sleep(1)

    except KeyboardInterrupt:
        exit_clean()
    except Exception as e:
        exit_fail(e)
    finally:
        exit_clean()
