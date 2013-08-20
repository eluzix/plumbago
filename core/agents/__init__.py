import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import logging
import json

import requests
import hipchat

from core import Alert


__author__ = 'uzix & dembar'

log = logging.getLogger(__name__)


class BaseAgent(object):
    def __init__(self, **kwargs):
        self.normal_template = kwargs['normal_template']
        self.error_template = kwargs['error_template']

    def format_message(self, alert):
        template = self.normal_template
        if alert.status == Alert.STATUS_ERROR:
            template = self.error_template

        #todo: format the template...
        template = template.replace('$name', alert.name)
        template = template.replace('$target', alert.target)
        template = template.replace('$ts', str(alert.status_ts))
        template = template.replace('$threshold', str(alert.threshold))
        template = template.replace('$value', str(alert.status_value))
        return template


class LoggerAgent(BaseAgent):
    def alert(self, message, alert):
        log.error('[Logger] message: %s', message)


class HipchatAgent(BaseAgent):
    def __init__(self, **kwargs):
        super(HipchatAgent, self).__init__(**kwargs)

        self.api_key = kwargs['api_key']
        self.room_id = kwargs['room_id']
        self.from_ = kwargs['from']
        self.format = kwargs['format']
        self.notify = kwargs['notify']
        self.normal_color = kwargs['normal_color']
        self.error_color = kwargs['error_color']

    def alert(self, message, alert):
        try:
            hipster = hipchat.HipChat(token=self.api_key)
            params = {'room_id': self.room_id, 'from': self.from_, 'message': message, 'message_format': self.format, 'notify': self.notify,
                      'color': self.error_color if alert.status == Alert.STATUS_ERROR else self.normal_color}

            log.debug('[HipchatAgent] message: %s', message)
            hipster.method(url='rooms/message', method="POST", parameters=params)
        except Exception as ex:
            log.error('[HipchatAgent] Error sending alert message to hipchat. Message: %s. Error: %s', message, ex)


class EmailAgent(BaseAgent):
    def __init__(self, **kwargs):
        super(EmailAgent, self).__init__(**kwargs)

        self.host = kwargs['host']
        self.port = kwargs['port']
        self.tls = kwargs['use_tls']
        self.user = kwargs['username']
        self.pass_ = kwargs['password']

        self.from_ = kwargs['from']
        self.to = kwargs['to']
        self.subject = kwargs['subject']

        self.graphurl = kwargs['render']
        self.graphuser = kwargs['graphuser']
        self.graphpass = kwargs['graphpass']

    def alert(self, message, alert):

        # Get a graph from graphite for the alert, authenticating if necessary
        url = '%s?from=-1hour&until=-&target=%s&target=threshold(%s,"Threshold",red)&bgcolor=black&fgcolor=white&fontBold=true&height=300&width=600&lineWidth=3&colorList=blue,red' % (self.graphurl, alert.target, str(alert.threshold))

        if self.graphuser is not None:
            graph = requests.get(url, auth=(self.graphuser, self.graphpass)).content
        else:
            graph = requests.get(url).content

        log.debug('[EmailAgent] Getting graph from graphite with url: %s', url)

        # Prepare the header
        msg = MIMEMultipart()
        msg['From'] = self.from_
        msg['Subject'] = self.subject

        # Prepare html and text alternatives
        text = message
        html = '''\
            <html>
                <head></head>
                <body>
                    <p>%s</p>
                    <hr><hr>
                </body>
            </html>''' % message

        # Attach as MIME objects
        msg.attach(MIMEText(text, 'plain'))
        msg.attach(MIMEText(html, 'html'))
        msg.attach(MIMEImage(graph))

        # Loop through the e-mail addresses and send the e-mail to all of them
        for to in self.to.split(','):
            msg['To'] = to
            try:
                smtp_server = smtplib.SMTP(self.host, self.port)
                if self.tls:
                    smtp_server.starttls()
                if self.user and self.pass_:
                    smtp_server.login(self.user, self.pass_)
                smtp_server.sendmail(self.from_, to, msg.as_string())
                log.debug('[EmailAgent] to: %s. MIME Message: %s',to, msg)
            except Exception as ex:
                log.error('[EmailAgent] Error sending alert e-mail message to %s. Message: %s. Error: %s', to, message, ex)


class PagerDutyAgent(BaseAgent):
    def __init__(self, **kwargs):
        super(PagerDutyAgent, self).__init__(**kwargs)

        self.api = kwargs['api']

    def alert(self, message, alert):
        url = 'https://events.pagerduty.com/generic/2010-04-15/create_event.json'

        headers = {'content-type': 'application/json'}

        if alert.status == Alert.STATUS_ERROR:
            payload = {'service_key': self.api,
                       'incident_key': alert.name,
                       'event_type': 'trigger',
                       'description': message}
        else:
            payload = {'service_key': self.api,
                       'incident_key': alert.name,
                       'event_type': 'resolve',
                       'description': message}
        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers)
            log.debug('[PagerDutyAgent] message: %s. PagerDuty Response: %s', message, response.content)
        except Exception as ex:
            log.error('[PagerDutyAgent] Error sending alert to PagerDuty. Error: %s', ex)


class OpsGenieAgent(BaseAgent):
    def __init__(self, **kwargs):
        super(OpsGenieAgent, self).__init__(**kwargs)

        self.api = kwargs['api']
        self.dest = kwargs['dest']

    def alert(self, message, alert):

        if alert.status == Alert.STATUS_ERROR:
            url = 'https://api.opsgenie.com/v1/json/alert'
            payload = {'customerKey': self.api,
                       'message': message,
                       'recipients': self.dest,
                       'alias': alert.name}
        else:
            url = 'https://api.opsgenie.com/v1/json/alert/close'
            payload = {'customerKey': self.api,
                       'note': message,
                       'notify': self.dest,
                       'alias': alert.name}

        headers = {'content-type': 'application/json'}

        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers)
            log.debug('[OpsGenieAgent] message: %s. OpsGenie Response: %s', message, response.content)
        except Exception as ex:
            log.error('[OpsGenieAgent] Error sending alert to OpsGenie. Error: %s', ex)


class FlowdockAgent(BaseAgent):
    def __init__(self, **kwargs):
        super(FlowdockAgent, self).__init__(**kwargs)

        self.api = kwargs['api']
        self.from_ = kwargs['from']

    def alert(self, message, alert):
        url = 'https://api.flowdock.com/v1/messages/chat/%s' % self.api

        headers = {'content-type': 'application/json'}

        payload = {'tags': alert.name,
                   'external_user_name': self.from_,
                   'content': message}

        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers)
            log.debug('[FlowdockAgent] message: %s. Flowdock Response: %s', message, response.content)
        except Exception as ex:
            log.error('[FlowdockAgent] Error sending alert to Flowdock. Error: %s', ex)