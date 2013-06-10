import base64
import json
import logging
import time
import urllib
import urllib2

__author__ = 'uzix'

log = logging.getLogger(__name__)


class Alert(object):
    STATUS_OK = 0
    STATUS_ERROR = 1

    def __init__(self, name, conf):
        self.name = name
        self.target = conf['target']
        self.threshold = conf['threshold']
        self.diff = conf['diff']
        self.agents = conf['agents']

        self.last_ts = 0
        self.last_value = 0
        self.status = Alert.STATUS_OK
        self.status_ts = 0
        self.status_value = 0
        self.needs_alert = False


class Plumbago(object):
    def __init__(self, config):
        self._running = False
        self._alerts = {}
        self._agents = {}
        self.configure(config)

    def configure(self, config_data):
        self._config_data = config_data
        self._config = config_data['config']

        _log = self._config.get('logging')
        if _log is not None:
            logging.basicConfig()
            rlog = logging.getLogger()
            if _log.get('debug'):
                rlog.setLevel(logging.DEBUG)
            else:
                rlog.setLevel(logging.INFO)

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
            klass = _get_class(ag['class'])
            agent = klass(**ag)
            agents[name] = agent
        self._agents = agents

    def _fetch_data(self):
        try:
            targets = []
            for alert in self._alerts:
                targets.append(urllib.quote_plus(self._alerts[alert].target))
            targets = '&target=%s' % '&target='.join(targets)

            url = '%s?from=-5minutes&until=-&format=json%s' % (self._config['render'], targets)
            log.debug('url = %s', url)
            request = urllib2.Request(url)
            username = self._config.get('username')
            if username is not None:
                password = self._config.get('password')
                base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
                request.add_header("Authorization", "Basic %s" % base64string)
            result = urllib2.urlopen(request)
            data = result.read()

            # log.debug("results: %s", data)
            return data
        except Exception as e:
            log.error('Error fetching data from graphite api, error: %s', e)
            return None

    def _parse_data(self, data):
        try:
            data = json.loads(data)
            for _alert in data:
                target = _alert['target'].lower()
                alert = self._alerts[target]
                points = _alert.get('datapoints')
                if points is not None and len(points):
                    #run from end to find last viable datapoint (not null)
                    points.reverse()
                    point = None
                    for p in points:
                        if p[0] is not None:
                            point = p
                            break

                    if point is None:
                        log.warn('Unable to find non null data point for %s', target)
                        continue

                    if point[1] > alert.last_ts:
                        alert.last_value = point[0]
                        alert.last_ts = point[1]

                        if point[0] >= alert.threshold and alert.status == Alert.STATUS_OK:
                            #we are moving from OK to ALERT
                            alert.status = Alert.STATUS_ERROR
                            alert.status_value = point[0]
                            alert.status_ts = point[1]
                            alert.needs_alert = True
                        elif point[0] >= alert.threshold and alert.status == Alert.STATUS_ERROR:
                            #another tp inside alert lets see if we need to resend the alert
                            if alert.status_ts + alert.diff <= point[1]:
                                alert.status_value = point[0]
                                alert.status_ts = point[1]
                                alert.needs_alert = True
                        elif point[0] < alert.threshold and alert.status == Alert.STATUS_ERROR:
                            #move back from alert to ok status
                            alert.status = Alert.STATUS_OK
                            alert.status_value = point[0]
                            alert.status_ts = point[1]
                            #needs_alert is True cause we need to know it returned to normal...
                            alert.needs_alert = True

        except Exception as e:
            log.error('Error parsing data, error: %s', e)

    def _check_alerts(self):
        for alert_target in self._alerts:
            alert = self._alerts[alert_target]
            if alert.needs_alert:
                for ag in alert.agents:
                    agent = self._agents.get(ag)
                    if agent is None:
                        log.warning('Unable to find agent %s for alert %s', ag, alert.name)
                        continue
                    msg = agent.format_message(alert)
                    agent.alert(msg, alert)
                alert.needs_alert = False

    def run(self):
        self._running = True
        while self._running:
            data = self._fetch_data()
            if data is not None:
                self._parse_data(data)
                self._check_alerts()
            time.sleep(self._config.get('interval', 60))
