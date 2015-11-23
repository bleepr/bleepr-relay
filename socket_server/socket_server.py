#!/usr/bin/python
import json
import redis
from ws4py.client.threadedclient import WebSocketClient

r = redis.StrictRedis(host="localhost", port=6379, db=0)

class SocketClient(WebSocketClient):
    def opened(self):
        # Subscribe to channel - JSON inside JSON, WTF is this library Snowden!
        print("opening")
        self.send(json.dumps({
            "command": "subscribe",
            "identifier": "{\"channel\":\"ButtonsChannel\"}"
        }))

    def closed(self, code, reason=None):
        print("Socket closed: {}, {}".format(code, reason))

    def received_message(self, message):
        message = str(message)
        data = json.loads(message)
        data["device"] = "20:C3:8F:F6:5E:CE" # Temp hack, MAC should come from server

        mac_address = data["device"]
        r.append(mac_address, "{0},".format(message))

def run_socket():
    ws = SocketClient("ws://burger.bleepr.io/websocket")
    ws.connect()
    ws.run_forever()

if __name__ == "__main__":
    run_socket()
