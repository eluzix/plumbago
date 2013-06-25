#from yaml import load
import logging
import signal
import sys
import yaml
import os
from plumbago import Plumbago

__author__ = 'uzix'

log = logging.getLogger()

def main():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-p", "--pid-file", dest="pid", default='plumbago.pid', help="Plumbago pid file", metavar="PID_FILE")
    parser.add_option("-c", "--config-file", dest="config", default='config.yaml', help="Plumbago config file", metavar="CONFIG_FILE")
    (options, args) = parser.parse_args()

    pidfile=open(options.pid, 'w')
    pidfile.write(str(os.getpid()))
    pidfile.close()

    config = yaml.load(open(options.config, 'r'))
    server = Plumbago(config)

    def handler(signum, frame):
        if signum == signal.SIGUSR1:
            config = yaml.load(open(options.config, 'r'))
            server.configure(config)
        elif signum == signal.SIGUSR2:
            server.dump_status()
        elif signum == signal.SIGTERM:
            log.info('Received SIGTERM gracefully stopping in next runloop')
            server._running = False
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGUSR1, handler)
    signal.signal(signal.SIGUSR2, handler)

    server.run()

if __name__ == "__main__":
    main()
