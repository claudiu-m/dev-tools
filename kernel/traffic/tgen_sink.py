# SPDX-License-Identifier:  GPL-2.0-or-later
# Copyright 2019 claudiu-m <claudiu.manoil@gmail.com>
import sys
import time
import socket

host = sys.argv[1]
port_base = int(sys.argv[2])
port_range = int(sys.argv[3])

ports = range(port_base, port_base + port_range)

sockets = []
for port in ports:
    s = socket.socket()
    s.bind(('', 0))
    s.connect((host, port))
    sockets.append(s)

last = time.time()
start = last
record = []
try:
    while 1:
        recv = 0
        for s in sockets:
            buf = s.recv(8<<20) # 8MB
            recv += len(buf)
        now = time.time()
        record.append(recv / (now - last))
        if len(record) > 256:
            record.pop(0)
        last = now
        print('\r{:.1f}: rate {:.1f} MB/s'.format(now - start, sum(record) / len(record) / (1024*1024)), end='')
            
except KeyboardInterrupt:
    print('Test Cancelled')
