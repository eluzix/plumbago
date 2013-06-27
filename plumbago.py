import logging
import signal
import yaml
import os
import time
import json
from plumbago import Plumbago

__author__ = 'uzix'

log = logging.getLogger()


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


def getPlumbagoPid(pidFileOpt):
    try:
        pidFile = open(pidFileOpt, 'r')
    except:
        print "Could not open Plumbago pidfile", pidFileOpt
        exit(1)

    return int(pidFile.readline())


def getAlertStatus(alertName):
    time.sleep(1)
    statusfile = open('/tmp/plumbago.status', 'r')
    alerts = json.load(statusfile)
    if alertName == 'all':
        for alert in alerts:
            if alert['status'] == 'OK':
                print alert['name'] + ': \033[92m' + alert['status'] + '\033[0m'
            elif alert['status'] == 'DISABLED':
                print alert['name'] + ': \033[90m' + alert['status'] + '\033[0m'
            else:
                print alert['name'] + ': \033[91m' + alert['status'] + '\033[0m'
    elif alertName == 'error':
        for alert in alerts:
            if alert['status'] == 'ERROR':
                print alert['name'] + ': \033[91m' + alert['status'] + '\033[0m'
    elif alertName == 'disabled':
        for alert in alerts:
            if alert['status'] == 'DISABLED':
                print alert['name'] + ': \033[90m' + alert['status'] + '\033[0m'
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
                    print 'Status: \033[92m' + alert['status'] + '\033[0m\n'
                elif alert['status'] == 'ERROR':
                    print 'Status: \033[91m' + alert['status'] + '\033[0m\n'
                else:
                    print 'Status: \033[90m' + alert['status'] + '\033[0m\n'
                break
        if not found:
            print "\nNo alert exists with that name. Try -s all to see the complete list of alerts\n"
    os.remove('/tmp/plumbago.status')


def enableAlert(alertName, configFile, pidFile):
    config = yaml.load(open(configFile, 'r'))
    if alertName == 'all':
        for alert in config['alerts']:
            try:
                config['alerts'][alert]['enabled']
            except:
                continue
            if config['alerts'][alert]['enabled'] == False:
                config['alerts'][alert]['enabled'] = True
        yaml.dump(config, open(configFile, 'w'))
        reloadConfig(pidFile)
        return
    try:
        config['alerts'][alertName]
    except:
        print "\nNo alert exists with that name. Try -s all to see the complete list of alerts\n"
        return
    try:
        config['alerts'][alertName]['enabled']
    except:
        print "Alert is already enabled"
        return
    if config['alerts'][alertName]['enabled'] == True:
        print "Alert is already enabled"
        return
    else:
        config['alerts'][alertName]['enabled'] = True
        yaml.dump(config, open(configFile, 'w'))
        reloadConfig(pidFile)


def disableAlert(alertName, configFile, pidFile):
    config = yaml.load(open(configFile, 'r'))
    if alertName == 'all':
        for alert in config['alerts']:
            config['alerts'][alert]['enabled'] = False
        yaml.dump(config, open(configFile, 'w'))
        reloadConfig(pidFile)
        return
    try:
        config['alerts'][alertName]
    except:
        print "\nNo alert exists with that name. Try -s all to see the complete list of alerts\n"
        return
    config['alerts'][alertName]['enabled'] = False
    yaml.dump(config, open(configFile, 'w'))
    reloadConfig(pidFile)


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


def startServer(configFileOpt, pidFileOpt):
    try:
        configFile = open(configFileOpt, 'r')
    except:
        print "Could not load configuration file", configFileOpt
        exit(1)
    if os.path.exists(pidFileOpt):
        print "Pid file exists... Maybe plumbago is already running?"
        exit(0)

    print "Starting server..."
    createDaemon()

    pidfile = open(pidFileOpt, 'w')
    pidfile.write(str(os.getpid()))
    pidfile.close()

    config = yaml.load(configFile)
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
    os.remove(pidFileOpt)


def definePidFile(configFileOpt):
    try:
        configFile = open(configFileOpt, 'r')
    except:
        print "Could not load configuration file", configFileOpt
        exit(1)

    config = yaml.load(configFile)
    try:
        config['config']['pidfile']
        return config['config']['pidfile']
    except:
        return './plumbago.pid'


def defineLogFile(configFileOpt):
    try:
        configFile = open(configFileOpt, 'r')
    except:
        print "Could not load configuration file", configFileOpt
        exit(1)

    config = yaml.load(configFile)
    try:
        config['config']['logging']['file']
        return config['config']['logging']['file']
    except:
        return './plumbago.log'


def main():
    from optparse import OptionParser

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
    parser.add_option("-t", "--status", dest="status", help="Show alerts statuses [alert_name|all|error|disabled]",
                      metavar="ALERT_NAME")
    (options, args) = parser.parse_args()

    if not options.reload and not options.status and not options.kill and not options.enable and not options.disable and not options.server:
        print "\nNothing to do..."
        parser.print_usage()
        exit(0)

    if not options.pid:
        options.pid = definePidFile(options.config)

    if not options.log:
        options.log = defineLogFile(options.config)

    if options.server:
        options.reload = False
        options.status = False
        options.kill = False
        options.enable = False
        options.disable = False
        startServer(options.config, options.pid)

    if options.kill:
        options.reload = False
        options.status = False
        options.enable = False
        options.disable = False
        terminateServer(options.pid)

    if options.reload:
        reloadConfig(options.pid)

    if options.status:
        os.kill(getPlumbagoPid(options.pid), signal.SIGUSR2)
        getAlertStatus(options.status)

    if options.enable:
        enableAlert(options.enable, options.config, options.pid)

    if options.disable:
        disableAlert(options.disable, options.config, options.pid)


if __name__ == "__main__":
    main()
