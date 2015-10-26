import pygatt
import time
from discovery import discover
from multiprocessing import Process, Queue

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

def device_worker(queue, mac_address):
    try:
        dev = pygatt.pygatt.BluetoothLEDevice(mac_address,
            app_options="-t random")
        dev.connect()
        while True:
            led_status = dev.char_read_hnd(0x0e)
            if led_status[0] == 0x00:
                dev.char_write(0x0e, bytearray([0x01]))
            elif led_status[0] == 0x01:
                dev.char_write(0x0e, bytearray([0x00]))

            # This allowes the parent to stop the process
            if not queue.empty():
                queue_entry = queue.get()
                if queue_entry == "stop":
                    print("Killing worker")
                    return
    except pygatt.exceptions.BluetoothLEError:
        print("Bluetooth error, killing worker for {}".format(mac_address))
        return
