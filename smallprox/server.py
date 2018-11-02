import asyncio
import os
import logging
import traceback
from http import HTTPStatus
from collections import namedtuple
from ssl import SSLContext

from .mapper import get_host_and_port

from httptools import HttpRequestParser, HttpParserError, parse_url


logger = logging.getLogger('small-prox')

Response = namedtuple('Response', 'status body headers')


class ClientConnection(asyncio.Protocol):
    __slots__ = ('parent', 'loop', 'transport')

    def __init__(self, parent, loop):
        self.parent = parent
        self.loop = loop
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def send(self, data):
        if not self.transport:
            print('race')
        else:
            self.transport.write(data)

    def data_received(self, data):
        self.parent.send_raw(data)

    def connection_lost(self, exc):
        pass

    def close(self):
        pass


class HTTPServer:
    def __init__(self, loop, config):
        self._loop = loop
        self.config = config
        self._server = None
        self._redirect_server = None

    async def start(self):
        ssl = None
        port = 80
        if os.path.isfile('/certs/fullchain.pem'):
            context = SSLContext()
            context.load_cert_chain('/certs/fullchain.pem', '/certs/privkey.pem')
            ssl = context

            self._redirect_server = await self._loop.create_server(
                lambda: _HTTPServerProtocol(loop=self._loop,
                                            config=self.config,
                                            ssl_forward=True),
                host='0.0.0.0',
                port=port
            )
            port = 443

        self._server = await self._loop.create_server(
            lambda: _HTTPServerProtocol(loop=self._loop, config=self.config),
            host='0.0.0.0',
            port=port,
            ssl=ssl
        )
        print(f'Listening on port {port}')


class _HTTPServerProtocol(asyncio.Protocol):
    """ HTTP Protocol handler.
        Should only be used by HTTPServerTransport
    """
    __slots__ = ('_transport', 'data', 'http_parser',
                 'client', '_headers', '_url', 'config', 'ssl_forward')

    def __init__(self, *, loop, config, ssl_forward=False):
        self.config = config
        self._transport = None
        self.data = None
        self.http_parser = HttpRequestParser(self)
        self.client = None
        self._loop = loop
        self._url = None
        self._headers = None
        self.ssl_forward = ssl_forward

    """ The next 3 methods are for asyncio.Protocol handling """
    def connection_made(self, transport):
        self._transport = transport
        self.client = None
        self.data = b''

    def connection_lost(self, exc):
        if self.client:
            self.client.close()

    def data_received(self, data):
        try:
            self.data += data
            self.http_parser.feed_data(data)
            self.send_data_to_client()
        except HttpParserError as e:
            traceback.print_exc()
            self.send_response(Response(status=HTTPStatus.BAD_REQUEST,
                                        body=b'invalid HTTP',
                                        headers={}))

    """ 
    The following methods are for HTTP parsing (from httptools)
    """
    def on_message_begin(self):
        self._headers = {}

    def on_header(self, name, value):
        key = name.decode('ASCII').lower()
        val = value.decode()
        self._headers[key] = val

    def on_headers_complete(self):
        host = self._headers['host']
        host = host.split(':')[0]
        url = parse_url(self._url)

        if self.ssl_forward:
            self.send_response(Response(HTTPStatus.MOVED_PERMANENTLY,
                                        body=b'Redirect to https',
                                        headers={'Location': 'https://' + host + self._url.decode()}))
            return
        logger.debug('Request from %s and path %s', host, url.path.decode())
        ssl = False
        ip, port = get_host_and_port(host, url.path.decode(), self.config)
        if port == '0':
            if ip.startswith('https://'):
                port = 443
                ip = ip[8:]
                ssl = True
            else:
                port = 80
                ip = ip[7:]
            self._headers['old_host'] = self._headers['host']
            self._headers['host'] = ip
            self._headers.pop('referer', None)
        if ip is None:
            self.send_response(Response(HTTPStatus.SERVICE_UNAVAILABLE,
                                        body=b'service unavailable',
                                        headers={}))
            return
        self.client = ClientConnection(self, self._loop)
        coro = self._loop.create_connection(
            lambda: self.client, ip, port=int(port), ssl=ssl)
        task = self._loop.create_task(coro)
        task.add_done_callback(self.send_data_to_client)

    def on_url(self, url):
        self._url = url

    """
    End parsing methods
    """

    def send_data_to_client(self, future=None):
        if self.client and self.client.transport:
            old_host = self._headers.get('old_host')
            if old_host:
                data = self.data.replace(f'\r\nHost: {old_host}\r\n'.encode(),
                                         f'\r\nHost: {self._headers["host"]}\r\n'.encode())
            else:
                data = self.data
            self.client.send(data)
            self.data = b''

    def send_raw(self, data):
        self._transport.write(data)

    def send_response(self, response):
        headers = 'HTTP/1.1 {status_code} {status_message}\r\n'.format(
            status_code=response.status.value,
            status_message=response.status.phrase,
        )
        headers += 'Connection: close\r\n'

        if response.body:
            headers += 'Content-Type: text/plain\r\n'
            headers += 'Content-Length: {}\r\n'.format(len(response.body))
        else:
            headers += 'Content-Length: {}\r\n'.format(0)

        if response.headers:
            for header, value in response.headers.items():
                headers += '{header}: {value}\r\n'.format(header=header,
                                                          value=value)

        result = headers.encode('ASCII') + b'\r\n'
        if response.body:
            result += response.body

        self.send_raw(result)
