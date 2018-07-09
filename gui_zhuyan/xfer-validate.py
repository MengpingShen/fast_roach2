
import numpy as np
import struct
import time
import katcp_wrapper

nbins = 1 * 1024

fpga = katcp_wrapper.FpgaClient('r1510')
time.sleep(0.1)
print(fpga.is_connected())

passband = np.arange(0, nbins, dtype=np.int32)
for pol in ('A', 'B', 'C', 'D'):
    fpga.write('x8_vacc_passband_' + pol, struct.pack('>%di'%nbins, *passband))

for pol in ('A', 'B', 'C', 'D'):
	snap = fpga.snapshot_get('x8_vacc_scope_' + pol)
	np.array(struct.unpack('>%di'%nbins, snap['data'])).tofile('x8_vacc_scope_' + pol, sep='\n', format='%d')

fpga.stop()
