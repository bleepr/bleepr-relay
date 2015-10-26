from gattlib import DiscoveryService

allowed_addresses = ["EC:D3:58:F9:BB:49"]

def discover(device, timeout):
    service = DiscoveryService(device)
    devices = service.discover(timeout)

    found_bleeprs = []
    for address, name in devices.items():
        if address in allowed_addresses:
            found_bleeprs.append(address)

    return found_bleeprs

if __name__ == "__main__":
    print(discover("hci0", 2))
