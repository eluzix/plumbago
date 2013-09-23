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

An example config.yaml can be found as config.yaml.orig

Agents
------
* Hipchat

It will send a text message through the hipchat api to the specified room. You can use the @tags to tag people and
make sure they get the message.

* E-mail

It will send an e-mail to the specified e-mail addresses and besides the normal or error template and the optional
comment, it will attach a graph of the alerted target for the last hour.

* PagerDuty

It will trigger a new incident, using the alert name as key, so as long as the alert stays in ERROR status, it will
keep adding new events to the same incident. When the alert goes back to OK status, a resolve incident is triggered.

* OpsGenie

It will open a new alert, using the alert name as an alias. When the alert goes back to OK status it will close the
alert but not delete it, so you can use it to track down what's been going on later. It supports sending notifications
to a specific user or group.

* Flowdock

It will send a text message to the flow chat specified with the api argument. You can user @tags in the message
to tag people and make sure they receive the message. It will also add the alert name as a tag.

* LoggerAgent

Used for testing. It will output the normal or error messages and optional comment to the log file.

* Custom Agents

At the moment Plumbago supports Hipchat, PagerDuty, OpsGenie, FlowDock and E-mail as agents but its fairly easy to
create one of your own if you think that's not enough.

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

```
usage: plumbago [-h] [--server] [--reload] [--kill]
                [--config CONFIG_FILE] [-a ALERT_NAME AGENT]
                [-c ALERT_NAME INT] [-d ALERT_NAME] [-e ALERT_NAME]
                [-f ALERT_NAME SECONDS] [-l ALERT_NAME THRESHOLD]
                [-m ALERT_NAME COMMENT] [-r ALERT_NAME] [-s ALERT_NAME]
                [-t ALERT_NAME TARGET] [-x ALERT_NAME ACTION]
                [-z ALERT_NAME MINUTES] [-u ALERT_NAME]

optional arguments:
  -h, --help            show this help message and exit

Server:
  --server              Run Plumbago Server
  --reload              Reload Plumbago configuration
  --kill                Kill Plumbago server

Files:
  Define where core files are or go

  --config CONFIG_FILE  Plumbago config file

Alerts:
  See and modify alerts

  -a ALERT_NAME AGENT, --agent ALERT_NAME AGENT
                        Change notification agent for an alert
                        [alert_name|all|error]
  -c ALERT_NAME INT, --cycles ALERT_NAME INT
                        Modify alert cycles before alerting [alert_name|all]
  -d ALERT_NAME, --disable ALERT_NAME
                        Disable alert [alert_name|all]
  -e ALERT_NAME, --enable ALERT_NAME
                        Enable alert [alert_name|all]
  -f ALERT_NAME SECONDS, --diff ALERT_NAME SECONDS
                        Modify time between alerts [alert_name|all]
  -l ALERT_NAME THRESHOLD, --threshold ALERT_NAME THRESHOLD
                        Modify alert threshold
  -m ALERT_NAME COMMENT, --comment ALERT_NAME COMMENT
                        Modify alert comment
  -r ALERT_NAME, --reverse ALERT_NAME
                        Reverse alert check [alert_name|error]
  -s ALERT_NAME, --status ALERT_NAME
                        Show alerts statuses
                        [alert_name|all|error|disabled|unknown]
  -t ALERT_NAME TARGET, --target ALERT_NAME TARGET
                        Modify alert target
  -x ALERT_NAME ACTION, --action ALERT_NAME ACTION
                        Modify alert action
  -z ALERT_NAME MINUTES, --snooze ALERT_NAME MINUTES
                        Snooze alert by MINUTES
  -u ALERT_NAME, --unsnooze ALERT_NAME
                        Unsnooze previously snoozed alert
```