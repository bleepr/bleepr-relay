import requests
import json
import iso8601
import datetime
import pytz

endpoint = "http://burger.bleepr.io"

def get_table_id(mac_address):
    r = requests.get("{}/bleeprs/{}".format(endpoint, mac_address))

    if r.status_code != 200:
        return None

    bleepr = json.loads(r.text)
    return bleepr["table_id"]

def table_available(table_id, customer_id):
    r = requests.get("{}/tables/{}/occupancies/bookings".format(endpoint,
        table_id))

    available = True
    bookings = json.loads(r.text)
    for booking in bookings:
        start_timestamp = iso8601.parse_date(booking["start"])
        end_timestamp = iso8601.parse_date(booking["end"])
        current_timestamp = pytz.utc.localize(datetime.datetime.utcnow())
        if current_timestamp > start_timestamp and\
            current_timestamp < end_timestamp and\
            booking["customer_id"] != customer_id:
            available = False

    return available

def get_customer_id(card_id):
    r = requests.get("{}/cards/{}".format(endpoint, card_id))

    if r.status_code == 404:
        return None

    card = json.loads(r.text)
    return card["customer_id"]

def get_occupancy(table_id):
    r = requests.get("{}/tables/{}/occupancies/bookings".format(endpoint,
        table_id))

    bookings = json.loads(r.text)
    for booking in bookings:
        start_timestamp = iso8601.parse_date(booking["start"])
        end_timestamp = iso8601.parse_date(booking["end"])
        current_timestamp = pytz.utc.localize(datetime.datetime.utcnow())
        if current_timestamp > start_timestamp and\
            current_timestamp < end_timestamp:
            return booking["id"]

    return None

def set_occupied(table_id, occupancy):
    r = requests.put("{}/tables/{}/occupancies/{}".format(endpoint, table_id,
        occupancy), data=json.dumps({"occupancy": {"occupied": True}}),
            headers={'content-type': 'application/json'})

def create_new_occupancy(table_id, customer_id):
    r = requests.post("{}/tables/{}/occupancies/".format(endpoint, table_id),
            data=json.dumps({"occupancy": {
                "prebooked": False,
                "start": datetime.datetime.now().isoformat(),
                "occupied": True,
                "customer_id": customer_id,
                "table_id": table_id
            }}),
            headers={'content-type': 'application/json'})

def request_bill(table_id):
    r = requests.post("{}/tables/{}/request_bill".format(endpoint, table_id))

def call_waiter(table_id):
    r = requests.post("{}/tables/{}/call_waiter".format(endpoint, table_id))

def leave_table(table_id):
    r = requests.post("{}/tables/{}/leave_table".format(endpoint, table_id))

def get_order_status(table_id):
    r = requests.get("{}/tables/{}/orders".format(endpoint, table_id))

    orders = json.loads(r.text)
    status_counts = {}
    for order in orders:
        if order["status"] not in status_counts:
            status_counts[order["status"]] = 1
        else:
            status_counts[order["status"]] += 1

    parts = []
    for status in status_counts.keys():
        parts.append("{} {}".format(status_counts[status], status))

    return ", ".join(parts)

if __name__ == "__main__":
    print(get_order_status(45))
