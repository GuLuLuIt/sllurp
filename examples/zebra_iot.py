"""Minimal Zebra IoT Connector Local REST example.

Set ZEBRA_READER, ZEBRA_USER, and ZEBRA_PASSWORD before running this example.
The reader must have its Local REST management/control interfaces enabled.
"""

import os

from sllurp.zebra_iot import ZebraIoTConnectorClient


reader = os.environ["ZEBRA_READER"]
username = os.environ["ZEBRA_USER"]
password = os.environ["ZEBRA_PASSWORD"]

client = ZebraIoTConnectorClient(
    reader,
    username=username,
    password=password,
)
client.login()

print(client.get_version())
print(client.get_hostname())
print(client.get_mode(verbose=True))
