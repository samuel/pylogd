#!/usr/bin/env python

import os
import sys
import cPickle as pickle
import logging
import logging.config
import logging.handlers
import socket
import struct

class LogRecordSocketReceiver(object):
    allow_reuse_address = True

    def __init__(self, host='0.0.0.0', port=logging.handlers.DEFAULT_UDP_LOGGING_PORT):
        self.logname = None
        self.timeout = 1
        self.socket = socket.socket(socket.SOCK_DGRAM, socket.AF_INET)
        self.socket.bind((host, port))

    def handle_message(self, msg):
        slen = struct.unpack(">L", msg[:4])[0]
        if len(msg) != slen+4:
            print "Invalid size. Expected %d got %d" % (slen+4, len(msg))
        obj = pickle.loads(msg[4:])
        record = logging.makeLogRecord(obj)
        self.handle_log_record(record)

    def handle_log_record(self, record):
        # if a name is specified, we use the named logger rather than the one
        # implied by the record.
        name = self.logname or record.name
        logger = logging.getLogger(name)
        logger.handle(record)

    def serve_until_stopped(self):
        abort = False
        while not abort:
            msg, sender = self.socket.recvfrom(1024*10)
            self.handle_message(msg)

def become_daemon(our_home_dir='.', out_log='/dev/null',
                  err_log='/dev/null', umask=022):
    "Robustly turn into a UNIX daemon, running in our_home_dir."
    # First fork
    try:
        if os.fork() > 0:
            sys.exit(0)     # kill off parent
    except OSError, e:
        sys.stderr.write("fork #1 failed: (%d) %s\n" % (e.errno, e.strerror))
        sys.exit(1)
    os.setsid()
    os.chdir(our_home_dir)
    os.umask(umask)

    # Second fork
    try:
        if os.fork() > 0:
            os._exit(0)
    except OSError, e:
        sys.stderr.write("fork #2 failed: (%d) %s\n" % (e.errno, e.strerror))
        os._exit(1)

    si = open('/dev/null', 'r')
    so = open(out_log, 'a+', 0)
    se = open(err_log, 'a+', 0)
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())
    # Set custom file descriptors so that they get proper buffering.
    sys.stdout, sys.stderr = so, se

def main():
    logging.config.fileConfig("pylogd.conf")
    # logging.basicConfig(
    #     format="%(asctime)s %(name)s %(levelname)s %(message)s")
    if len(sys.argv) > 1 and sys.argv[1] == '-d':
        become_daemon()
    tcpserver = LogRecordSocketReceiver()
    tcpserver.serve_until_stopped()

if __name__ == "__main__":
    main()
