from discovery import discover
from gattlib import GATTRequester

def communication_loop():
    while True:
        devices = discover("hci0", 1)
        for mac_address in devices:
            sync_device(mac_address)

def sync_device(mac_address):
    print("Syncing device: {}".format(mac_address))

    req = GATTRequester(mac_address)
    print(req.read_by_handle(0x0e))
