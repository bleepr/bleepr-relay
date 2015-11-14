from pygatt.util import lescan, reset_bluetooth_controller

allowed_addresses = ["20:C3:8F:F6:5B:B1"]

def discover(timeout):
    print("Discovering devices...")
    reset_bluetooth_controller()
    devices = lescan(timeout=timeout)
    found_bleeprs = []
    for device in devices:
        if device["address"] in allowed_addresses:
            found_bleeprs.append(device["address"])

    return found_bleeprs

if __name__ == "__main__":
    print(discover(2))
