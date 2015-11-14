import pygatt
import time
import json
import redis
import uuid
import requests
import pexpect
from discovery import discover
from multiprocessing import Process, Queue

r = redis.StrictRedis(host="localhost", port=6379, db=0)

def communication_loop():
    workers = {}
    while True:
        devices = discover(2)
        for mac_address in devices:
            if mac_address not in workers\
                or not workers[mac_address]["process"].is_alive():
                workers[mac_address] = {}
                workers[mac_address]["queue"] = Queue()
                workers[mac_address]["process"] = Process(target=device_worker,
                    args=(workers[mac_address]["queue"], mac_address))
                workers[mac_address]["process"].start()
        time.sleep(10)
        # Kill all workers before rescanning
        any_alive = True
        while any_alive:
            any_alive = False
            for mac_address in workers:
                if workers[mac_address]["process"].is_alive():
                    workers[mac_address]["queue"].put("stop")
                    any_alive = True

# Need to make out own connect method, library one doesn't pass MAC address to
# connect command which causes connection to fail
def bluetooth_connect(dev, mac_address, timeout):
    """Connect to the device."""
    dev._logger.info('Connecting with timeout=%s', timeout)
    try:
        with dev.connection_lock:
            dev.con.sendline('connect {}'.format(mac_address))
            dev.con.expect(r'Connection successful.*\[LE\]>', timeout)
    except pexpect.TIMEOUT:
        raise pygatt.exceptions.BluetoothLEError(
            "Timed-out connecting to device after %s seconds." % timeout)

def device_worker(queue, mac_address):
    try:
        dev = pygatt.pygatt.BluetoothLEDevice(mac_address,
            app_options="-t random")

        bluetooth_connect(dev, mac_address, 5)

        while True:
            print("working")
            time.sleep(0.1)
            # Atomically get and delete the latest messages for this device
            pipe = r.pipeline()
            messages = pipe.get(mac_address)
            pipe.delete(mac_address)
            messages, _ = pipe.execute()

            if messages:
                # Remove trailing comma, wrap in [] then decode as JSON
                messages = json.loads("[{}]".format(messages[:-1]))
                for message in messages:
                    if "message" in message and \
                        type(message["message"]) == dict:
                        process_message(dev, message["message"])

            # # Read data from device and make POST requests as required
            # value = dev.char_read_hnd(0x0e)
            # # If button is pressed,send request
            # if value == [0x01]:
            #     requests.post("http://burger.bleepr.io/buttons/{}".format(
            #         uuid.uuid4()))
            #     dev.char_write(0x0e, bytearray([0x00]))

            # This allowes the parent to stop the process
            if not queue.empty():
                queue_entry = queue.get()
                if queue_entry == "stop":
                    print("Killing worker")
                    return
    except pygatt.exceptions.BluetoothLEError as ex:
        print("Bluetooth error ({}), killing worker for {}".format(str(ex),
            mac_address))
        return

def process_message(dev, message):
    print(message)
    displaytext = message["button"] + "~"
    dev.char_write(0x0012, bytearray(displaytext.encode("UTF-8")))
    # if message["button"] == "ledon":
    #     dev.char_write(0x0e, bytearray([0x00]))
    # elif message["button"] == "ledoff":
    #     dev.char_write(0x0e, bytearray([0x01]))


    # try:
    #     dev = pygatt.pygatt.BluetoothLEDevice(mac_address,
    #         app_options="-t random")
    #     dev.connect()
    #     while True:
    #         led_status = dev.char_read_hnd(0x0e)
    #         if led_status[0] == 0x00:
    #             dev.char_write(0x0e, bytearray([0x01]))
    #         elif led_status[0] == 0x01:
    #             dev.char_write(0x0e, bytearray([0x00]))
    #
    #         # This allowes the parent to stop the process
    #         if not queue.empty():
    #             queue_entry = queue.get()
    #             if queue_entry == "stop":
    #                 print("Killing worker")
    #                 return
    # except pygatt.exceptions.BluetoothLEError:
    #     print("Bluetooth error, killing worker for {}".format(mac_address))
    #     return
