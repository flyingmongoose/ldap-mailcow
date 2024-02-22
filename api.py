import random
import string
import sys
import requests
import vobject
import time
import json

def __post_request(url, json_data):
    api_url = f"{api_host}/{url}"
    headers = {'X-API-Key': api_key, 'Content-type': 'application/json'}
    req = requests.post(api_url, headers=headers, json=json_data)

    if req.content != b'':
        rsp = req.json()
    else:
        req.close()
        return

    req.close()

    if isinstance(rsp, list):
        rsp = rsp[0]

    if not "type" in rsp or not "msg" in rsp:
        sys.exit(f"API {url}: got response without type or msg from Mailcow API")

    if rsp['type'] != 'success':
        sys.exit(f"API {url}: {rsp['type']} - {rsp['msg']}")

def add_user(email, name, active):
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
    json_data = {
        'local_part': email.split('@')[0],
        'domain': email.split('@')[1],
        'name': name,
        'password': password,
        'password2': password,
        "active": 1 if active else 0
    }

    __post_request('api/v1/add/mailbox', json_data)

def edit_user(email, active=None, name=None):
    attr = {}

    # vcard create
    vcard = vobject.vCard()

    o = vcard.add('email')
    o.type_param = 'INTERNET'
    o.value = email

    if (active is not None):
        attr['active'] = 1 if active else 0
    if (name is not None):
        attr['name'] = name
        o = vcard.add('fn')
        o.value = name

    json_data = {
        'items': [email],
        'attr': attr
    }
    __post_request('api/v1/edit/mailbox', json_data)

if __name__ == '__main__':
    pass
