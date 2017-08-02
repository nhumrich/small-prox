import asyncio
import os
import logging

from .server import HTTPServer
from .mapper import update_config, add_container


logger = logging.getLogger('small-prox')


def main():
    config = {}
    loop = asyncio.get_event_loop()
    local_ports = os.getenv('LOCAL_PORTS', [])
    local_ports = local_ports and local_ports.split(',')
    for port in local_ports:
        add_container('local', port, config)

    if os.getenv('DEBUG') == 'true':
        logger.setLevel('DEBUG')

    server = HTTPServer(loop, config)
    loop.run_until_complete(server.start())
    loop.create_task(update_config(config))
    loop.run_forever()
