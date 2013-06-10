#from yaml import load
import logging
import signal
import yaml
from plumbago import Plumbago

__author__ = 'uzix'

log = logging.getLogger()

def main():
    config = yaml.load(open('config.yaml', 'r'))
    server = Plumbago(config)

    def handler(signum, frame):
        if signum == signal.SIGUSR1:
            config = yaml.load(open('config.yaml', 'r'))
            server.configure(config)
        elif signum == signal.SIGTERM:
            log.info('Received SIGTERM gracefully stopping in next runloop')
            server._running = False
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGUSR1, handler)

    server.run()

if __name__ == "__main__":
    main()