import sys
import os.path
import katcp_wrapper

roach_board, ext = os.path.splitext(os.path.basename(sys.argv[0]))
fpga = katcp_wrapper.FpgaClient(roach_board)
fpga.is_connected()

