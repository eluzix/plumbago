import json
import logging
import time
from subprocess import call

import requests


log = logging.getLogger(__name__)


class Alert(object):

    STATUS_OK = 0
    STATUS_ERROR = 1
    STATUS_DISABLED = 2
    STATUS_UNKNOWN = 3

    def __init__(self, name, conf):
        self.name = name
        self.target = conf['target']
        self.threshold = conf['threshold']
        self.reverse = conf.get('reverse', False)
        self.enabled = conf.get('enabled', True)
        self.error_cycles = conf.get('error_cycles', 1)
        self.diff = conf['diff']
        self.action = conf.get('action', False)
        self.agents = conf['agents']
        self.comment = conf.get('comment', False)

        self.last_ts = 0
        self.last_value = 0
        self.status = Alert.STATUS_UNKNOWN
        self.status_ts = 0
        self.status_value = 0
        self.status_cycle = 0
        self.needs_alert = False
        self.tried_action = False
        self.data_fetched = False


class Plumbago(object):

    def __init__(self, config):
        self._running = False
        self._alerts = {}
        self._agents = {}
        try:
            self.configure(config)
        except Exception as e:
            log.error('[Core] Misconfiguration. Error parsing %s', e)

    def configure(self, config_data):
        log.info('[Core] Loading configurations...')
        self._config_data = config_data
        self._config = config_data['config']

        if not self._running:
            _log = self._config.get('logging')
            if _log is not None:
                logging.basicConfig()
                logging.getLogger("requests").setLevel(logging.ERROR)
                rlog = logging.getLogger()
                rlog.handlers[0].formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s",
                                                           "%Y-%m-%d %H:%M:%S")
                if _log.get('debug'):
                    rlog.setLevel(logging.DEBUG)
                else:
                    rlog.setLevel(logging.INFO)
                log_file = _log.get('file')
                if log_file is not None:
                    #remove all other handlers
                    handler = logging.FileHandler(log_file)
                    handler.setLevel(rlog.getEffectiveLevel())
                    handler.setFormatter(rlog.handlers[0].formatter)
                    for h in rlog.handlers:
                        rlog.removeHandler(h)
                    rlog.addHandler(handler)

        _alerts = config_data['alerts']
        alerts = {}
        for alert_name in _alerts:
            a = Alert(alert_name, _alerts[alert_name])
            alerts[a.target.lower()] = a
        self._alerts = alerts

        def _get_class(kls):
            parts = kls.split('.')
            module = ".".join(parts[:-1])
            m = __import__(module)
            for comp in parts[1:]:
                m = getattr(m, comp)
            return m

        _agents = config_data['agents']
        agents = {}
        for ag in _agents:
            name = ag['name']
            # We add the graphite url, username and password so the email agent can send a nice graph
            ag['render'] = self._config['render']

            try:
                ag['graphuser'] = self._config['username']
                ag['graphpass'] = self._config['password']
            except:
                ag['graphuser'] = None
                ag['graphpass'] = None

            klass = _get_class(ag['class'])
            agent = klass(**ag)
            agents[name] = agent
        self._agents = agents

    def _fetch_data(self, target=None):
        try:
            targets = []
            if target is None:
                for alert in self._alerts:
                    targets.append(self._alerts[alert].target)
            else:
                targets.append(target)
            targets = '&target=%s' % '&target='.join(targets)

            url = '%s?from=-5minutes&until=-&format=json%s' % (self._config['render'], targets)
            log.debug('[Core] url = %s', url)
            username = self._config.get('username')
            if username is not None:
                password = self._config.get('password')
                data = requests.get(url, auth=(username, password)).content
            else:
                data = requests.get(url).content

            return data
        except Exception as e:
            log.error('[Core] Error fetching data from graphite api, error: %s', e)
            return None

    def _handle_single_alert(self, alert, points):
        if not alert.enabled:
            alert.status = Alert.STATUS_DISABLED
            return
        if points is not None and len(points):
            #run from end to find last viable datapoint (not null)
            points.reverse()
            point = None
            for p in points:
                if p[0] is not None:
                    point = p
                    break

            if point is None:
                alert.status = Alert.STATUS_UNKNOWN
                log.warn('[Core] Unable to find non null data point for %s', alert.target)
                return

            if point[1] > alert.last_ts:
                alert.last_value = point[0]
                alert.last_ts = point[1]

                if alert.reverse:
                    threshold_crossed = point[0] < alert.threshold
                else:
                    threshold_crossed = point[0] >= alert.threshold

                if threshold_crossed and alert.status == Alert.STATUS_OK:
                    alert.status_cycle += 1
                    if alert.status_cycle >= alert.error_cycles:
                        #we are moving from OK to ALERT
                        alert.status_value = point[0]
                        alert.status_ts = point[1]
                        if alert.action and not alert.tried_action:
                            self._execute_action(alert)
                        else:
                            alert.status = Alert.STATUS_ERROR
                            alert.needs_alert = True
                elif threshold_crossed and alert.status == Alert.STATUS_ERROR:
                    #another tp inside alert lets see if we need to resend the alert
                    if alert.status_ts + alert.diff <= point[1]:
                        alert.status_value = point[0]
                        alert.status_ts = point[1]
                        alert.needs_alert = True
                elif not threshold_crossed and alert.status == Alert.STATUS_ERROR:
                    #move back from alert to ok status
                    alert.status = Alert.STATUS_OK
                    alert.tried_action = False
                    alert.status_value = point[0]
                    alert.status_ts = point[1]
                    alert.status_cycle = 0
                    #needs_alert is True cause we need to know it returned to normal...
                    alert.needs_alert = True
                else:
                    alert.status = Alert.STATUS_OK
                    alert.status_value = point[0]
                    alert.status_ts = point[1]
                    alert.status_cycle = 0

    def _execute_action(self, alert):
        try:
            call(alert.action, shell=True)
            log.info('[Core] Executed %s for alert %s' % (alert.action, alert.name))
        except Exception as e:
            log.error('[Core] Impossible to execute %s. Error: %s', alert.action, e)
        alert.tried_action = True

    def _parse_data(self, data):
        try:
            data = json.loads(data)
            for _alert in data:
                target = _alert['target'].lower()
                alert = self._alerts.get(target)
                if alert is None:
                    continue

                points = _alert.get('datapoints')
                self._handle_single_alert(alert, points)
                alert.data_fetched = True
        except Exception as e:
            log.error('[Core] Error parsing data, error: %s', e)

    def _check_alerts(self):
        for alert_target in self._alerts:
            alert = self._alerts[alert_target]
            if alert.needs_alert:
                for ag in alert.agents:
                    agent = self._agents.get(ag)
                    if agent is None:
                        log.warning('[Core] Unable to find agent %s for alert %s', ag, alert.name)
                        continue
                    if alert.comment:
                        msg = '%s\n%s' % (agent.format_message(alert), alert.comment)
                    else:
                        msg = agent.format_message(alert)
                    agent.alert(msg, alert)
                    log.info('[Alert!] %s', msg)
                alert.needs_alert = False

    def run(self):
        self._running = True
        while self._running:
            data = self._fetch_data()
            if data is not None:
                #mark all alerts as need to parse
                for a in self._alerts:
                    self._alerts[a].data_fetched = False

                self._parse_data(data)

                for a in self._alerts:
                    alert = self._alerts[a]
                    if not alert.data_fetched and alert.enabled:
                        data = self._fetch_data(alert.target)
                        if data is None:
                            log.info('[Core] Unable to find target %s for single fetch', alert.target)
                            continue
                        try:
                            data = json.loads(data)
                            if not len(data):
                                log.info('[Core] Graphite sent no data for target: %s', alert.target)
                                continue
                        except Exception as e:
                            log.error('[Core] Could not read url for target: %s', alert.target)
                            continue
                        points = data[0].get('datapoints')
                        self._handle_single_alert(alert, points)
                    elif not alert.enabled:
                        alert.status = Alert.STATUS_DISABLED
                self._check_alerts()
            time.sleep(self._config.get('interval', 60))

    def dump_status(self):
        data = []
        for name in self._alerts:
            alert = self._alerts[name]
            data.append({'name': alert.name,
                         'target': alert.target,
                         'status': alert.status,
                         'enabled': str(alert.enabled),
                         'value': alert.status_value,
                         'threshold': alert.threshold,
                         'action': alert.action,
                         'reverse': str(alert.reverse),
                         'cycles': alert.error_cycles,
                         'comment': alert.comment})
        with open('/tmp/plumbago.status', 'w') as filedump:
            filedump.write(json.dumps(data, indent=1))