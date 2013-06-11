#from yaml import load
import logging
import signal
import sys
import yaml
from plumbago import Plumbago

__author__ = 'uzix'

log = logging.getLogger()

def main():
    config_file = 'config.yaml'
    if len(sys.argv) > 1:
        config_file = sys.argv[1]

    config = yaml.load(open(config_file, 'r'))
    server = Plumbago(config)

    def handler(signum, frame):
        if signum == signal.SIGUSR1:
            config = yaml.load(open(config_file, 'r'))
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