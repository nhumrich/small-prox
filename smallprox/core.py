import asyncio
import os
import logging

import dns.resolver

from .server import HTTPServer
from .mapper import update_config, add_container


logger = logging.getLogger('small-prox')


def _get_local_address():
    resolver = dns.resolver.Resolver()
    try:
        resolver.query('docker.for.mac.localhost')
    except:
        # must be on linux
        return 'local'
    else:
        return 'macos'


def main():
    config = {}
    loop = asyncio.get_event_loop()
    local_ports = os.getenv('LOCAL_PORTS', [])
    local_ports = local_ports and local_ports.split(',')
    local_address = _get_local_address()
    for port in local_ports:
        add_container(local_address, port, config)

    if os.getenv('DEBUG') == 'true':
        logger.setLevel('DEBUG')

    server = HTTPServer(loop, config)
    loop.run_until_complete(server.start())
    loop.create_task(update_config(config))
    loop.run_forever()
