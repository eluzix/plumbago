import logging
import smtplib

import hipchat

from core import Alert


__author__ = 'uzix'

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
        log.error(message)


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
            log.error('Error sending alert message to hipchat, message: %s, error: %s', message, ex)

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

    def alert(self, message, alert):

        msg = 'From: %s\r\n', self.from_
        msg += 'To: %s\r\n', self.to.split()
        msg += 'Subject: %s\r\n\r\n', self.subject
        msg += '%s', message

        try:
            smtp_server = smtplib.SMTP(self.host, self.port)
            if self.tls:
                smtp_server.starttls()
            smtp_server.login(self.user, self.pass_)
            smtp_server.sendmail(self.from_, self.to, msg)
            log.debug('[EmailAgent] message: %s', message)
        except Exception as ex:
            log.error('Error sending alert e-mail message, message: %s, error: %s', message, ex)