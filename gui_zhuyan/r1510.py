import sys
import time
import os.path
import katcp_wrapper

roach_board, ext = os.path.splitext(os.path.basename(sys.argv[0]))
fpga = katcp_wrapper.FpgaClient(roach_board)
time.sleep(0.1)
if fpga.is_connected():
	print('Connected to %s:%d' % fpga.bindaddr)
