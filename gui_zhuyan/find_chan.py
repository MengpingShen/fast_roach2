
samp_freq = 2200.	# in MHz
samp_bw = samp_freq / 2.
nchan = 64
chan_bw = samp_bw / nchan

#target_freq = 256. / 1024 * samp_bw
target_freq = 89

global_index = target_freq / chan_bw + 0.5
print(target_freq, chan_bw, global_index)
int_index = int(global_index)
lane = (int_index >> 1) & 1		# int_index / 2 % 2
local_index = (int_index+1) / 2 + (global_index - int_index)
print(lane, int_index, local_index)