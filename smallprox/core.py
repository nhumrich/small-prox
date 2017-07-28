import asyncio
import os

from .server import HTTPServer
from .mapper import update_config, add_container



def main():
    config = {}
    loop = asyncio.get_event_loop()
    local_ports = os.getenv('LOCAL_PORTS', [])
    local_ports = local_ports and local_ports.split(',')
    for port in local_ports:
        add_container('local', port, config)

    server = HTTPServer(loop, config)
    loop.run_until_complete(server.start())
    loop.create_task(update_config(config))
    loop.run_forever()
