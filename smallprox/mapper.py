import asyncio

import aiodocker


async def update_config(config: dict):
    docker = aiodocker.Docker()
    events = docker.events
    subscriber = events.subscribe()

    asyncio.ensure_future(events.run())

    for container in (await docker.containers.list()):
        expose_label = container._container.get('Labels').get('localproxy_expose')
        if expose_label:
            add_container(container, expose_label, config)

    while True:
        event = await subscriber.get()
        status = event.get('status')
        if status in ('start', 'die') and event.get('Type') == 'container':
            print(event)
            expose = event.get('Actor', {}).get('Attributes', {}).get('localproxy_expose')
            if not expose:
                # no expose label. Ignore container
                continue
            con = (await docker.containers.get(
                event.get('Actor', {}).get('ID')))

            if status == 'start':
                add_container(con, expose, config)
            elif status == 'die':
                remove_container(con, expose, config)


def add_container(container, expose_label, config):
    print(container)
    print(expose_label)

    if container == 'local':
        ip = '127.0.0.1'
    else:
        networks = container._container.get('NetworkSettings').get('Networks')
        ip = networks.get('bridge').get('IPAddress')

    host, path, port = parse_expose_label(expose_label)
    host_dict = config.get(host, {})
    host_dict[path] = f'{ip}:{port}'
    config[host] = host_dict


def remove_container(container, expose_label, config):
    host, path, port = parse_expose_label(expose_label)
    host_dict = config.get(host)
    if len(host_dict) == 1:
        del config[host]
    else:
        del host_dict[path]


def parse_expose_label(expose_label):
    url, port = expose_label.split('=')
    if url.startswith('/'):
        # url is only a path
        host = '*'
        path = 'url'
    else:
        # url contains a host
        url_portions = url.split('/')
        host = url_portions[0]
        if len(url_portions) > 1:
            path = url_portions[1]
        else:
            path = ''
    return host, path, port


def get_host_and_port(host, path, config):
    host_dict = config.get(host, {})
    all_hosts_dict = config.get('*', {})
    host_string = host_dict.get(path)
    if not host_string:
        host_string = all_hosts_dict.get(path)
    if not host_string:
        host_string = host_dict.get('')
    if not host_string:
        return None, None
    else:
        ip, port = host_string.split(':')
        return ip, port
