#!/usr/bin/env python

'''
    Capture raw ADC samples from KatADC wideband revision
'''

import time, struct, sys, logging, socket
import katcp_wrapper, log_handlers
import argparse


bitstream = 'katadc_zdok1_snap_2016_Aug_18_1351.bof.gz'
siggen_addr = ('10.32.127.103', 5025)


class attrdict(dict):
    def __init__(self, **kwargs):
        dict.__init__(self, **kwargs)
        self.__dict__ = self


roach = '10.0.0.24'
katcp_port = 7147

opts = attrdict(
            )



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

def sg_command(sock, cmd):
	sock.sendall(cmd if cmd[-1] == '\n' else cmd + '\n')


def sg_query(sock, cmd):
	sg_command(sock, cmd)
	resp = ''
	while len(resp) == 0 or resp[-1] != '\n':
		resp = resp + sock.recv(1024)
	return resp[:-1]





#START OF MAIN:

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

        # Connect to signal generater
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(siggen_addr)

        start_freq = 10
        stop_freq = 2000
        step = 1

        freq = start_freq
        while freq <= stop_freq:
            sg_command(sock, ":FREQ %dMHz" % freq)
            #time.sleep(0.5)
            print(sg_query(sock, ":FREQ?"))
            pol0 = fpga.snapshot_get('pol0', man_trig=True, man_valid=True)
            fname = "%04d.dat" % freq
            with open(fname, 'w') as f:
                f.write(pol0['data'])
            freq = freq + step

    except KeyboardInterrupt:
        exit_clean()
    except Exception as e:
        exit_fail(e)
    finally:
        exit_clean()
