#!/usr/bin/env python3

import configparser
import os
import time

from haversine import haversine, Unit
from humanize import intcomma
from meshtastic import serial_interface as serial, tcp_interface as tcp
from pubsub import pub

class RangeBot:
    def __init__(self, port=None):
        self.config = configparser.RawConfigParser()
        if os.path.exists('config.ini'):
            self.config.read('config.ini')
        else:
            raise RuntimeError('Config file could not be found...')
        devPath = self.config['Meshtastic']['port']
        if devPath == 'auto':
            self.interface = serial.SerialInterface()
        elif devPath.startswith('/dev/'):
            self.interface = serial.SerialInterface(devPath)
        else:
            self.interface = tcp.TCPInterface(hostname=devPath.lstrip('tcp:'))

    @property
    def my_id(self):
        return self.interface.getMyUser().get('id')

    @property
    def my_location(self):
        return self.get_lat_lon(self.my_id)

    def distance(self, node_id):
        return haversine(self.my_location, self.get_lat_lon(node_id), unit=Unit.METERS)

    def onReceive(self, packet, interface): # called when a packet arrives
        decoded = packet.get('decoded')
        node_id = packet.get('fromId')
        if decoded.get('portnum') != 'TEXT_MESSAGE_APP' or node_id == self.my_id:
            return

        message = decoded.get('payload').decode()
        print(message)
        if not message.lower() in ['ping', 'test', 'p', 't']:
            return
        distance = 0
        try:
            distance = int(self.distance(node_id))
        except Exception as exc:
            print(repr(exc), node_id)
            return
        datetime = time.strftime('%y/%m/%d %H:%M:%S')
        msg=f'pong at {datetime} range {intcomma(distance)}m'
        print(msg, node_id)
        self.interface.sendText(msg, destinationId=node_id)

    def get_lat_lon(self, node_id):
        node = self.interface.nodes.get(node_id)
        if not node:
            raise RuntimeError('no node')
        position = node.get('position', {})
        if not position:
            raise RuntimeError('no position')
        latitude = position.get('latitude', -1000)
        longitude = position.get('longitude', -1000)
        if latitude == -1000 or longitude == -1000:
            raise RuntimeError('no lat or lon')
        return latitude, longitude

    def onConnection(self, interface, topic=pub.AUTO_TOPIC):
        print('Connected to device')

    def run(self):
        pub.subscribe(self.onReceive, "meshtastic.receive")
        pub.subscribe(self.onConnection, "meshtastic.connection.established")
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                break
        print('Exiting...')

if __name__ == '__main__':
    bot = RangeBot()
    bot.run()
