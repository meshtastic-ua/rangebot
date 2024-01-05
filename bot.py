#!/usr/bin/env python3

import time

from haversine import haversine, Unit
from humanize import intcomma
from meshtastic import serial_interface as serial
from pubsub import pub

class RangeBot:
    def __init__(self, port=None):
        self.interface = serial.SerialInterface()

    @property
    def my_id(self):
        #self.interface.getMyNodeInfo().get('user', {}).get('id')
        #hex(self.interface.localNode.nodeNum).replace('0x', '!')
        #hex(self.interface.myInfo.my_node_num).replace('0x', '!')
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
        if not message.lower() in ['ping', 'test']:
            return
        distance = 0
        try:
            distance = self.distance(node_id)
        except Exception as exc:
            print(repr(exc), node_id)
            return

        msg=f'pong at {intcomma(distance)}m'
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

    def onConnection(self, interface, topic=pub.AUTO_TOPIC): # called when we (re)connect to the radio
        print('Connected to device')
        # self.interface.sendText("hello mesh")

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
