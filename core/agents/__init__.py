import logging
from core import Alert
import hipchat

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
