# -*- coding: utf-8 -*-

"""
Chat Server
===========

This simple application uses WebSockets to run a primitive chat server.
"""

import os
import logging
import redis
import gevent
import mosquitto
from flask import Flask, render_template
from flask_sockets import Sockets
#from mqtt import mqtt
import threading
import json

REDIS_CHAN = 'mqtt'

app = Flask(__name__)
app.debug = 'DEBUG' in os.environ
from logging import StreamHandler
file_handler = StreamHandler()
app.logger.setLevel(logging.DEBUG)  # set the desired logging level here
app.logger.addHandler(file_handler)
redis = redis.from_url('redis://localhost:6379')

sockets = Sockets(app)
MQTTCLIENTS = {}
clients = list()

def on_connect(mosq, obj, rc):
    app.logger.debug("mosquito connect: "+str(rc))
    if rc==0:
        MQTTCLIENTS[obj].subscribe('public/thingfabric/#', 0)

def on_disconnect(mosq, obj, rc):
    app.logger.debug("mosquito disconnect: "+str(rc))

def send(client, data):
        """Send given data to the registered client.
        Automatically discards invalid connections."""
        try:
            app.logger.debug("send")
            client.send(data)
        except Exception:
            app.logger.debug("except")
            clients.remove(client)

def on_message(mosq, obj, msg):
    app.logger.debug(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
    for client in clients:
        parsedMsg = parse(msg)
        if (parsedMsg!="0"):
            client.send(parse(msg))

def on_publish(mosq, obj, mid):
    app.logger.debug("mid: " + str(mid))

def on_log(mosq, obj, level, string):
    app.logger.debug("Log:"+string)

def mqtt(url):
    app.logger.debug("start mqtt")
    mqttc = mosquitto.Mosquitto('qwerr')
    mqttc.on_message = on_message
    mqttc.on_connect = on_connect
    mqttc.on_disconnect = on_disconnect
    mqttc.on_publish = on_publish
    mqttc.user_data_set('qwerr')

    #print("username: "+username+"   password: "+password);

    #if username:
    #     if password:
    #         logging.info("Setting Username: "+username+"; Password="+password)
    #         mqttc.username_pw_set(username, password)
    #     else:
    #         logging.info("Setting Username (Only): "+username)
    #         mqttc.username_pw_set(username)

    #if username:
    #    mqttc._username = username
    #if password:
    #    mqttc._password = password

    mqttc.connect(url, int('1883'), keepalive=30)
    MQTTCLIENTS['qwerr'] = mqttc

    rc = 0
    while rc == 0:
        #print "loop"
        try:
            rc = mqttc.loop()
        except Exception:
            app.logger.debug("mqtt error")
            mqttc.connect(url, int('1883'), keepalive=30)


def parse(message):
  try:
    stuff = message.topic.split('/')[1]
    thing = message.topic.split('/')[2]
    return json.dumps({
      'stuff': stuff,
      'thing': thing,
      'message': message.payload
    })
  except Exception:
    return "0"



download_thread = threading.Thread(target=mqtt, args=["q.mq.tt"])
download_thread.start()


@app.route('/')
def hello():
    return render_template('index.html')


@sockets.route('/submit')
def inbox(ws):
    """Receives incoming chat messages, inserts them into Redis."""
    while ws.socket is not None:
        # Sleep to prevent *contstant* context-switches.
        gevent.sleep(0.1)
        message = ws.receive()
        #app.logger.info("submit")
        if message:
            app.logger.info(u'Inserting message: {}'.format(message))
            redis.publish(REDIS_CHAN, message)

@sockets.route('/receive')
def outbox(ws):
    """Sends outgoing chat messages, via `ChatBackend`."""
    clients.append(ws)
    #app.logger.info("receive")
    while ws.socket is not None:
        # Context switch while `ChatBackend.start` is running in the background.
        gevent.sleep()



