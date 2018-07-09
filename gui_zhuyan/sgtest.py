import socket

siggen_addr = ('10.32.127.103', 5025)

def sg_command(sock, cmd):
	sock.sendall(cmd if cmd[-1] == '\n' else cmd + '\n')

def sg_query(sock, cmd):
	sg_command(sock, cmd)
	resp = ''
	while len(resp) == 0 or resp[-1] != '\n':
		resp = resp + sock.recv(1024)
	return resp[:-1]

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(siggen_addr)
print(sg_query(sock, '*IDN?'))
sg_command(sock, ':FREQ 123MHz')
print(sg_query(sock, ':FREQ?'))
sock.close()

