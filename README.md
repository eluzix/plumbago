plumbago
========

Simple (very!) alerting system for graphite.
Why not use [seyren][https://github.com/scobal/seyren]? well its too heavy for us (java + Mongodb) so we wrote something to fit our needs.
Plumbago has no ui, nor fancy dashboard but its light, easy to use and easy to customize.

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
  logging:
    debug: no
    #add the file argument to stop writing to stdout and start writing to a file (all log levels)
    #file: pl.log

agents:
  - name: hipchat
    class: plumbago.agents.HipchatAgent
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

alerts:
  example_alert:
    #graphite target
    target: diffSeries(servers.DBMaster.memory.MemFree,servers.DBMaster.memory.MemTotal)
    threshold: 17494441984
    #seconds to wait between alarms
    diff: 600
    #list of agents
    agents:
      - hipchat
```


Custom Agents
-------------
At the moment Plumbago support only Hipchat as agent but its fairly easy to create one of your own.

```python
from plumbago.agents import BaseAgent
class CustomAgent(BaseAgent):
    def alert(self, message, alert):
        pass
```

The `alert` method will receive the formatted message and also the alert object.