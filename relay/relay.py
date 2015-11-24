import pygatt
import time
import json
import redis
import uuid
import requests
import pexpect
import api
from discovery import discover
from multiprocessing import Process, Queue

r = redis.StrictRedis(host="localhost", port=6379, db=0)

def start():
    workers = {}
    devices = discover(2)
    for mac_address in devices:
        if mac_address not in workers\
            or not workers[mac_address]["process"].is_alive():
            workers[mac_address] = {}
            workers[mac_address]["queue"] = Queue()
            workers[mac_address]["process"] = Process(target=device_worker,
                args=(workers[mac_address]["queue"], mac_address))
            workers[mac_address]["process"].start()

# def communication_loop():
#     workers = {}
#     while True:
#         devices = discover(2)
#         for mac_address in devices:
#             if mac_address not in workers\
#                 or not workers[mac_address]["process"].is_alive():
#                 workers[mac_address] = {}
#                 workers[mac_address]["queue"] = Queue()
#                 workers[mac_address]["process"] = Process(target=device_worker,
#                     args=(workers[mac_address]["queue"], mac_address))
#                 workers[mac_address]["process"].start()
#         time.sleep(30)
#         # Kill all workers before rescanning
#         any_alive = True
#         while any_alive:
#             any_alive = False
#             for mac_address in workers:
#                 if workers[mac_address]["process"].is_alive():
#                     workers[mac_address]["queue"].put("stop")
#                     any_alive = True

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

def handle_device_message(dev, mac_address, message):
    # This is a bodge to ignore the random crap spewed out by the Arduino on
    # boot - Need to have proper messages coming from the device

    print("Received message from {}: {}".format(mac_address, message))

    message_parts = message.split(",")
    if (message_parts[0] == "card_scan"):
        handle_card_scan(dev, mac_address, message[1])
    elif (message_parts[0] == "request_bill"):
        request_bill(dev, mac_address)
    elif (message_parts[0] == "call_waiter"):
        call_waiter(dev, mac_address)
    elif (message_parts[0] == "leave_table"):
        leave_table(dev, mac_address)

def handle_card_scan(dev, mac_address, card_id):
    table_id = api.get_table_id(mac_address)
    customer_id = api.get_customer_id(card_id)
    table_available = api.table_available(table_id, customer_id)

    if customer_id and table_available:
        # If the table already has an occupancy, update it to set as occupied
        # if not create a new one
        occupancy = api.get_occupancy(table_id)
        if occupancy:
            api.set_occupied(table_id, occupancy)
        else:
            api.create_new_occupancy(table_id, customer_id)

    response = b"access1\x00" if table_available and customer_id\
        else b"access0\x00"
    dev.char_write(0x0012, bytearray(response))

def request_bill(dev, mac_address):
    table_id = api.get_table_id(mac_address)
    api.request_bill(table_id)

    dev.char_write(0x0012, bytearray(b"ok\x00"))

def call_waiter(dev, mac_address):
    table_id = api.get_table_id(mac_address)
    api.call_waiter(table_id)

    dev.char_write(0x0012, bytearray(b"ok\x00"))

def leave_table(dev, mac_address):
    table_id = api.get_table_id(mac_address)
    api.leave_table(table_id)

    dev.char_write(0x0012, bytearray(b"ok\x00"))

def get_order_status(dev, mac_address):
    table_id = api.get_table_id(mac_address)
    order_status = api.get_order_status(table_id)

    dev.char_write(0x0012, bytearray(order_status.encode("utf-8") + "\x00"))

def device_worker(queue, mac_address):
    try:
        dev = pygatt.pygatt.BluetoothLEDevice(mac_address,
            app_options="-t random")

        bluetooth_connect(dev, mac_address, 5)

        def callback(_, message):
            try:
                handle_device_message(dev, mac_address,
                    message.decode("utf-8").strip())
            except UnicodeDecodeError:
                print("Could not understand message from device")

        dev.subscribe("0000ffe1-0000-1000-8000-00805f9b34fb", callback)

        # Do the same as the library's run method but make it be
        # possible to stop!
        while dev.running:
            # This allowes the parent to stop the process
            if not queue.empty():
                queue_entry = queue.get()
                if queue_entry == "stop":
                    print("Killing worker")
                    return
            with dev.connection_lock:
                try:
                    dev._expect("fooooooo", timeout=.1)
                except pygatt.exceptions.BluetoothLEError:
                    pass
            # TODO need some delay to avoid aggresively grabbing the lock,
            # blocking out the others. worst case is 1 second delay for async
            # not received as a part of another request
            time.sleep(.001)

        # while True:
        #     print("working")
        #     time.sleep(0.1)
        #     # Atomically get and delete the latest messages for this device
        #     pipe = r.pipeline()
        #     messages = pipe.get(mac_address)
        #     pipe.delete(mac_address)
        #     messages, _ = pipe.execute()
        #
        #     if messages:
        #         # Remove trailing comma, wrap in [] then decode as JSON
        #         messages = json.loads("[{}]".format(messages[:-1]))
        #         for message in messages:
        #             if "message" in message and \
        #                 type(message["message"]) == dict:
        #                 process_message(dev, message["message"])

            # # Read data from device and make POST requests as required
            # value = dev.char_read_hnd(0x0e)
            # # If button is pressed,send request
            # if value == [0x01]:
            #     requests.post("http://burger.bleepr.io/buttons/{}".format(
            #         uuid.uuid4()))
            #     dev.char_write(0x0e, bytearray([0x00]))

    except pygatt.exceptions.BluetoothLEError as ex:
        print("Bluetooth error ({}), killing worker for {}".format(str(ex),
            mac_address))
        return

def process_message(dev, message):
    print(message)
    displaytext = message["button"] + "\x00"
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
