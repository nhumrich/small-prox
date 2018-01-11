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
    # Pull the local address from the environment
    addr = os.environ.get('LOCAL_ADDRESS')
    if addr:
        return addr
    resolver = dns.resolver.Resolver()
    try:
        resolver.query('docker.for.mac.localhost')
        return 'docker.for.mac.localhost'
    except:
        # must be on linux, get host ip
        result = os.popen('ip r').read()
        ip = re.match('default via (.*?)\s', result).groups(1)[0]
        return ip


def _get_remote_mapping(port_mapping):
    local_host, remote_host = port_mapping.split('=')

    return local_host + f'=0', remote_host


def main():
    config = {}
    if os.getenv('DEBUG') == 'true':
        logger.setLevel('DEBUG')

    loop = asyncio.get_event_loop()
    local_ports = os.getenv('LOCAL_PORTS', [])
    local_ports = local_ports and [port.strip() for port in local_ports.split(',')]
    remote_ports = os.getenv('REMOTE_PORTS', [])
    remote_ports = remote_ports and [port.strip() for port in remote_ports.split(',')]

    for port in remote_ports:
        mapping, ip = _get_remote_mapping(port)
        add_container(None, mapping, config, ip=ip)

    config['_local_ports'] = local_ports
    config['_local_address'] = _get_local_address()

    logger.debug('Current container map: %s', config)

    server = HTTPServer(loop, config)
    loop.run_until_complete(server.start())
    loop.create_task(update_config(config))
    loop.run_forever()
