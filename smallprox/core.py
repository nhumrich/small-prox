import asyncio
import os
import logging
import re

import dns.resolver

logging.basicConfig()

from .server import HTTPServer
from .mapper import update_config, add_container

logger = logging.getLogger('small-prox')


def _get_local_address():
    resolver = dns.resolver.Resolver()
    try:
        resolver.query('docker.for.mac.localhost')
        return 'docker.for.mac.localhost'
    except:
        # must be on linux, get host ip
        result = os.popen('ip r').read()
        ip = re.match('default via (.*?)\s', result).groups(1)[0]
        return ip


def main():
    config = {}
    if os.getenv('DEBUG') == 'true':
        logger.setLevel('DEBUG')

    loop = asyncio.get_event_loop()
    local_ports = os.getenv('LOCAL_PORTS', [])
    local_ports = local_ports and [port.strip() for port in local_ports.split(',')]

    config['_local_ports'] = local_ports
    config['_local_address'] = _get_local_address()

    logger.debug('Current container map: %s', config)

    server = HTTPServer(loop, config)
    loop.run_until_complete(server.start())
    loop.create_task(update_config(config))
    loop.run_forever()
