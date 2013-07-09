import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import base64
import urllib2

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
            log.error('Error sending alert message to hipchat. Message: %s. Error: %s', message, ex)

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

        url = self.graphurl + '?from=-1hour&until=-&target=' + alert.target + '&target=threshold(' + str(alert.threshold) + ',"Threshold",red)&bgcolor=black&fgcolor=white&fontBold=true&height=300&width=600&lineWidth=3&colorList=blue,red'
        request = urllib2.Request(url)
        username = self.graphuser
        if username is not None:
            password = self.graphpass
            base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
            request.add_header("Authorization", "Basic %s" % base64string)
        result = urllib2.urlopen(request).read()

        try:
            file_ = open('/tmp/img.plum','wb')
            file_.write(result)
            file_.close()
        except Exception as ex:
            log.error('Could not save image. Error: %s', ex)

        msg = MIMEMultipart()
        msg['To'] = to
        msg['From'] = self.from_
        msg['Subject'] = self.subject

        text = message
        html = '''\
            <html>
                <head></head>
                <body>
                    <p>%s</p>
                    <hr><hr>
                </body>
            </html>''' % message

        msg.attach(MIMEText(text, 'plain'))
        msg.attach(MIMEText(html, 'html'))

        try:
            file_ = open('/tmp/img.plum', 'rb')
            img = MIMEImage(file_.read())
            file_.close()
            msg.attach(img)
        except Exception as ex:
            log.error('Could not attach image. Error: %s', ex)

        for to in self.to.split(','):
            try:
                smtp_server = smtplib.SMTP(self.host, self.port)
                if self.tls:
                    smtp_server.starttls()
                if self.user and self.pass_:
                    smtp_server.login(self.user, self.pass_)
                smtp_server.sendmail(self.from_, to, msg.as_string())
            except Exception as ex:
                log.error('Error sending alert e-mail message to %s. Message: %s. Error: %s', to, message, ex)