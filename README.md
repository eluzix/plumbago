plumbago
========

Simple (very!) alerting system for graphite.
Why not use https://github.com/scobal/seyren? Well, it's too heavy for us (java + Mongodb) so we wrote something to fit our own needs.
Plumbago has no ui nor fancy dashboard but it's lightweight, easy to use and easy to customize.

Configuration
-------------
All configuration is done in the config.yaml which contains 3 sections:
    # config: general configuration and logging
    # agents: list of agents (agents are used to write the actual alerts)
    # alert: alerts.

An example config.yaml might be:

```yaml
config:
  #link to the graphite's render script
  render: http://graphite:8080/render
  #if graphite is protected by http simple auth you can provide username/password
  username: admin
  password: supersecretpassword
  #graphite query interval in seconds
  interval: 60 #data fetch interval in seconds
  #(optional, defaults to ./plumbago.pid) where to write plumbago server's pid number
  pidfile: pl.pid
  logging:
    debug: no
    #(optional, defaults to plumbago.log) where to write the log file (all log levels)
    file: pl.log

agents:
  - name: hipchat
    class: core.agents.HipchatAgent
    api_key: HipChat_API_KEY
    room_id: HipChat_ROOM_ID
    from: plumbago
    format: text
    notify: 1
    error_color: red
    normal_color: green
    #template is used to format the message, parameters:
    #   $name: alert name
    #   $target: alert target
    #   $ts: alert timestamp
    #   $threshold: alert threshold
    #   $value: alert value
    normal_template: "OK $name: $target is back to normal $value < $threshold"
    error_template: "ERROR $name: $target is above threshold $value >= $threshold @demian"

  - name: email
    class: core.agents.EmailAgent
    host: smtp.yourserver.com
    port: 25
    # Set to yes if your server requires TLS
    use_tls: no
    username: smtp_user
    password: smtp_pass
    from: plumbago@plumbagoserver
    # Comma separated list of detination e-mails
    to: 'yourmail@domain.com, hismail@domain.com'
    subject: Plumbago alert!
    normal_template: "OK $name: $target is back to normal $value < $threshold"
    error_template: "ERROR $name: $target is above threshold $value >= $threshold"

  - name: pagerduty
    class: core.agents.PagerDutyAgent
    api: yourPagerDutyServiceApi
    normal_template: "OK $name: $target is back to normal $value < $threshold"
    error_template: "ERROR $name: $target is above threshold $value >= $threshold"

alerts:
  example_alert:
    #graphite target
    target: diffSeries(servers.DBMaster.memory.MemFree,servers.DBMaster.memory.MemTotal)
    #limit value before alerting
    threshold: 17494441984
    #(optional, defaults to no) if active it will check if the value goes under the threshold instead of over it
    reverse: no
    #(optional, defaults to yes) whether the alert will be checked or not
    enabled: yes
    #seconds to wait between alarms
    diff: 600
    #(optional, defaults to false) if set, points to a unix command (or script) that will be executed if the value
    #exceeds the threshold. If in the following cycle the value still exceeds, then alerts to the configured agent.
    action: "rm -fr /var/log/*"
    #list of agents
    agents:
      - hipchat
      - email
      - pagerduty
    #(optional, defaults to None) if set, it will be attached to normal and error templates when sending an alert.
    comment: 'This is a test alert, do not panic!'
```

Agents
------
* Hipchat

It will send a text message to through the hipchat api to the specified room. You can use the @tags to tag people and
make sure they get the message.

* E-mail

It will send an e-mail to the specified e-mail addresses and besides the normal or error template and the optional
comment, it will attach a graph of the alerted target for the last hour.

* PagerDuty

It will trigger a new incident, using the alert name as key, so as long as the alert stays in ERROR status, it will
keep adding new events to the same incident. When the alert goes back to OK status, a resolve incident is triggered.

* LoggerAgent

Used for testing. It will output the normal or error messages and optional comment to the log file.

* Custom Agents

At the moment Plumbago only supports Hipchat, PagerDuty and E-mail as agents but its fairly easy to create one of your own.

```python
from plumbago.agents import BaseAgent
class CustomAgent(BaseAgent):
    def alert(self, message, alert):
        pass
```

The `alert` method will receive the formatted message and also the alert object.

How to use it
-------------
Plumbago is a CLI app, just run it with some of it's options:

plumbago [options]

    -c, --config-file [path]: Path to plumbago config file (defaults to ./config.yaml).
    -p, --pid-file [path]: Path where to write plumbago pid file (defaults to ./plumbago.pid).
    -l, --log-file [path]: Path where to write plumbago log file (defaults to ./plumbago.log).
    -s, --server: Start plumbago server.
    -r, --reload: Reload plumbago configuration.
    -k, --kill: Terminate plumbago server.
    -t, --status [alert_name|all|error|disabled]: Shows alert status.
    -d, --disable [alert_name|all]: Disable alert. Implies -r.
    -e, --enable [alert_name|all]: Enable alert. Implies -r.