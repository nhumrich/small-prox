import asyncio
import logging

import aiodocker
import sys


logger = logging.getLogger('small-prox')


async def update_config(config: dict):
    docker = aiodocker.Docker()
    events = docker.events
    subscriber = events.subscribe()

    asyncio.ensure_future(events.run())

    for container in (await docker.containers.list()):
        expose_label = container._container.get('Labels').get('proxy_expose')
        if expose_label:
            add_container(container, expose_label, config)

    logger.debug('Current container map: %s', config)

    while True:
        event = await subscriber.get()
        if event is None:
            continue
        status = event.get('status')
        if status in ('start', 'die') and event.get('Type') == 'container':
            expose = event.get('Actor', {}).get('Attributes', {}).get('proxy_expose')
            if not expose:
                # no expose label. Ignore container
                continue
            con = (await docker.containers.get(
                event.get('Actor', {}).get('ID')))

            if status == 'start':
                add_container(con, expose, config)
            elif status == 'die':
                remove_container(con, expose, config)
            logger.debug('Changed config to: %s', config)


def add_container(container, expose_label, config, ip=None):
    if not ip:
        networks = container._container.get('NetworkSettings').get('Networks')
        for net in networks.keys():
            if 'IPAddress' in networks[net] and networks[net]['IPAddress']:
                ip = networks[net]['IPAddress']
                break

    if ip is None:
        container_name = container._container.get('Attributes', {}).get('name')
        print(f'An error happened trying to get '
              f'ip address of container {container_name}', file=sys.stderr)

    for host, path, port in parse_expose_label(expose_label):
        host_dict = config.get(host, {})
        host_dict[path] = f'{ip}:{port}'
        config[host] = host_dict


def remove_container(container, expose_label, config):
    for host, path, port in parse_expose_label(expose_label):
        host_dict = config.get(host)
        if not host_dict:
            # do nothing, already deleted
            pass
        if len(host_dict) == 1:
            del config[host]
        else:
            del host_dict[path]


def parse_expose_label(expose_label):
    logging.debug('Parsing expose label: %s', expose_label)
    sections = expose_label.split(',')
    results = []
    for section in sections:
        try:
            url, port = section.split('=')
        except:
            raise SystemError(f'Error parsing expose label: {expose_label}, at section: {section}')
        if url.startswith('/'):
            # url is only a path
            host = '*'
            path = url
        else:
            # url contains a host
            url_portions = url.split('/', 1)
            host = url_portions[0]
            if len(url_portions) > 1:
                path = url_portions[1].rstrip('/')
            else:
                path = ''
        results.append((host, path, port))
    return results


def get_host_and_port(host, path, config):
    path = path.strip('/')
    host_dict = config.get(host, {})
    all_hosts_dict = config.get('*', {})
    host_string = host_dict.get(_find_path_child(path, host_dict))
    if not host_string:
        host_string = all_hosts_dict.get(_find_path_child(path, all_hosts_dict))
    if not host_string:
        host_string = host_dict.get('')
    if not host_string:
        return None, None
    else:
        ip, port = host_string.split(':')
        return ip, port


def _find_path_child(full_path, path_dict):
    for path in sorted(path_dict.keys(), reverse=True):
        if full_path.startswith(path):
            return path

    return None
