#!/usr/bin/env python

import logging
import signal
import yaml
import os
import time
import json
from plumbago import Plumbago

__author__ = 'uzix'

log = logging.getLogger()


class colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    GRAY = '\033[90m'
    YELLOW = '\033[93m'
    DEF = '\033[0m'

    def disable(self):
        self.GREEN = ''
        self.RED = ''
        self.GRAY = ''
        self.YELLOW = ''
        self.DEF = ''


def createDaemon():
    try:
        pid = os.fork()
    except OSError, e:
        raise Exception, "%s [%d]" % (e.strerror, e.errno)

    if pid == 0:
        os.setsid()
        try:
            pid = os.fork()
        except OSError, e:
            raise Exception, "%s [%d]" % (e.strerror, e.errno)

        if pid != 0:
            os._exit(0)
    else:
        os._exit(0)

    return


def getPlumbagoPid(pidFile):
    try:
        return int(open(pidFile, 'r').readline())
    except:
        print "Could not open Plumbago pidfile", pidFile
        exit(1)


def getAlertStatus(alertName):
    time.sleep(1)
    statusfile = open('/tmp/plumbago.status', 'r')
    alerts = json.load(statusfile)
    if alertName == 'all':
        for alert in alerts:
            if alert['status'] == 'OK':
                print alert['name'] + ': ' + colors.GREEN + alert['status'] + colors.DEF
            elif alert['status'] == 'DISABLED':
                print alert['name'] + ': ' + colors.GRAY + alert['status'] + colors.DEF
            elif alert['status'] == 'UNKNOWN':
                print alert['name'] + ': ' + colors.YELLOW + alert['status'] + colors.DEF
            else:
                print alert['name'] + ': ' + colors.RED + alert['status'] + colors.DEF
    elif alertName == 'error':
        for alert in alerts:
            if alert['status'] == 'ERROR':
                print alert['name'] + ': ' + colors.RED + alert['status'] + colors.DEF
    elif alertName == 'disabled':
        for alert in alerts:
            if alert['status'] == 'DISABLED':
                print alert['name'] + ': ' + colors.GRAY + alert['status'] + colors.DEF
    elif alertName == 'unknown':
        for alert in alerts:
            if alert['status'] == 'UNKNOWN':
                print alert['name'] + ': ' + colors.YELLOW + alert['status'] + colors.DEF
    else:
        found = False
        for alert in alerts:
            if alert['name'] == alertName:
                found = True
                print "\nName: " + alert['name']
                print "Target: " + alert['target']
                print "Value: " + str(alert['value'])
                print "Threshold: " + str(alert['threshold'])
                if alert['status'] == 'OK':
                    print 'Status: ' + colors.GREEN + alert['status'] + colors.DEF
                elif alert['status'] == 'ERROR':
                    print 'Status: ' + colors.RED + alert['status'] + colors.DEF
                elif alert['status'] == 'DISABLED':
                    print 'Status: ' + colors.GRAY + alert['status'] + colors.DEF
                else:
                    print 'Status: ' + colors.YELLOW + alert['status'] + colors.DEF
                break
        if not found:
            print "\nNo alert exists with that name. Try -t all to see the complete list of alerts\n"
    os.remove('/tmp/plumbago.status')


def enableAlert(alertName, config, configFile):
    pidFile = config['config']['pidfile']
    logFile = config['config']['logging']['file']

    try:
        config = yaml.load(open(configFile, 'r'))
    except:
        print 'Could not open config file', configFile
        return

    if alertName == 'all':
        for alert in config['alerts']:
            try:
                if not config['alerts'][alert]['enabled']:
                    config['alerts'][alert]['enabled'] = True
            except:
                continue
    else:
        try:
            config['alerts'][alertName]
        except:
            print "\nNo alert exists with that name. Try -t all to see the complete list of alerts\n"
            return

        try:
            if config['alerts'][alertName]['enabled']:
                print "Alert is already enabled"
                return
            else:
                config['alerts'][alertName]['enabled'] = True
        except:
            print "Alert is already enabled"
            return

    yaml.dump(config, open(configFile, 'w'))
    config['config']['pidfile'] = pidFile
    config['config']['logging']['file'] = logFile
    reloadConfig(config['config']['pidfile'])


def disableAlert(alertName, config, configFile):
    pidFile = config['config']['pidfile']
    logFile = config['config']['logging']['file']

    try:
        config = yaml.load(open(configFile, 'r'))
    except:
        print 'Could not open config file', configFile
        return

    if alertName == 'all':
        for alert in config['alerts']:
            config['alerts'][alert]['enabled'] = False
    else:
        try:
            config['alerts'][alertName]['enabled'] = False
        except:
            print "\nNo alert exists with that name. Try -t all to see the complete list of alerts\n"
            return

    yaml.dump(config, open(configFile, 'w'))
    config['config']['pidfile'] = pidFile
    config['config']['logging']['file'] = logFile
    reloadConfig(config['config']['pidfile'])


def reloadConfig(pidFile):
    try:
        os.kill(getPlumbagoPid(pidFile), signal.SIGUSR1)
        print "Reloading Plumbago configuration..."
    except:
        print "Plumbago server not running!"
        exit(1)


def terminateServer(pidFile):
    try:
        os.kill(getPlumbagoPid(pidFile), signal.SIGTERM)
        print "Killing Plumbago server..."
    except:
        print "Plumbago server not running!"
        exit(1)


def startServer(config, configFileOpt):
    print "Starting server..."
    createDaemon()

    pidfile = open(config['config']['pidfile'], 'w')
    pidfile.write(str(os.getpid()))
    pidfile.close()

    server = Plumbago(config)

    def handler(signum, frame):
        if signum == signal.SIGUSR1:
            config = yaml.load(open(configFileOpt, 'r'))
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
    os.remove(config['config']['pidfile'])
    return


def definePidFile(config):
    try:
        return config['config']['pidfile']
    except:
        return './plumbago.pid'


def defineLogFile(config):
    try:
        return config['config']['logging']['file']
    except:
        return './plumbago.log'


def main():
    from optparse import OptionParser

    server_running = False

    parser = OptionParser()
    parser.add_option("-p", "--pid-file", dest="pid", help="Plumbago pid file", metavar="PID_FILE")
    parser.add_option("-c", "--config-file", dest="config", default='./config.yaml', help="Plumbago config file",
                      metavar="CONFIG_FILE")
    parser.add_option("-l", "--log-file", dest="log", help="Plumbago log file", metavar="LOG_FILE")
    parser.add_option("-s", "--server", dest="server", action="store_true", default=False, help="Run Plumbago Server")
    parser.add_option("-d", "--disable", dest="disable", help="Disable alert [alert_name|all]",
                      metavar="ALERT_NAME")
    parser.add_option("-e", "--enable", dest="enable", help="Enable alert [alert_name|all]",
                      metavar="ALERT_NAME")
    parser.add_option("-k", "--kill", dest="kill", action="store_true", default=False, help="Kill Plumbago server")
    parser.add_option("-r", "--reload", dest="reload", action="store_true", default=False,
                      help="Reload Plumbago configuration")
    parser.add_option("-t", "--status", dest="status",
                      help="Show alerts statuses [alert_name|all|error|disabled|unknown]", metavar="ALERT_NAME")
    (options, args) = parser.parse_args()

    if not options.reload and not options.status and not options.kill and not options.enable and not options.disable and not options.server:
        print "\nNothing to do..."
        parser.print_usage()
        return

    try:
        config = yaml.load(open(options.config, 'r'))
    except:
        print "Could not load configuration file", options.config
        return

    if not options.pid :
        config['config']['pidfile'] = definePidFile(config)
    else:
        config['config']['pidfile'] = options.pid

    if not options.log:
        config['config']['logging']['file'] = defineLogFile(config)
    else:
        config['config']['logging']['file'] = options.log

    if os.path.exists(config['config']['pidfile']):
        server_running = True

    if options.server:
        if not server_running:
            options.reload = False
            options.status = False
            options.kill = False
            options.enable = False
            options.disable = False
            startServer(config, options.config)
        else:
            print "Plumbago server already running!"

    if server_running:
        if options.kill:
            options.reload = False
            options.status = False
            options.enable = False
            options.disable = False
            terminateServer(config['config']['pidfile'])

        if options.reload:
            pidFile = config['config']['pidfile']
            logFile = config['config']['logging']['file']
            reloadConfig(config['config']['pidfile'])
            config['config']['pidfile'] = pidFile
            config['config']['logging']['file'] = logFile

        if options.status:
            os.kill(getPlumbagoPid(config['config']['pidfile']), signal.SIGUSR2)
            getAlertStatus(options.status)

        if options.enable:
            enableAlert(options.enable, config, options.config)

        if options.disable:
            disableAlert(options.disable, config, options.config)
    elif not options.server:
        print "Plumbago server not running!"


if __name__ == "__main__":
    main()