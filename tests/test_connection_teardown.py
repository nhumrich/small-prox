"""Connection-teardown tests.

A proxied request pairs two sockets: the downstream (client <-> small-prox,
held by ``_HTTPServerProtocol._transport``) and the upstream (small-prox <->
backend, held by ``ClientConnection.transport``). Both must be torn down when
either side closes, or small-prox leaks a file descriptor per request and
eventually exhausts its ``ulimit -n`` (the handshake then hangs / accept() fails
with EMFILE). These tests pin the symmetry with fake transports.
"""

import asyncio

from smallprox.server import ClientConnection, _HTTPServerProtocol


class FakeTransport:
    def __init__(self):
        self.closed = False
        self.written = b""

    def write(self, data):
        self.written += data

    def close(self):
        self.closed = True


def _wire_up_proxy_pair():
    """Build a downstream protocol with an established upstream client."""
    loop = asyncio.new_event_loop()
    try:
        downstream = _HTTPServerProtocol(loop=loop, config={})
        downstream_transport = FakeTransport()
        downstream.connection_made(downstream_transport)

        client = ClientConnection(downstream, loop)
        upstream_transport = FakeTransport()
        client.connection_made(upstream_transport)
        downstream.client = client
        return downstream, downstream_transport, client, upstream_transport
    finally:
        loop.close()


def test_downstream_close_tears_down_upstream():
    """Client hangs up -> the upstream backend socket is closed (no leak)."""
    downstream, _, client, upstream_transport = _wire_up_proxy_pair()

    downstream.connection_lost(None)

    assert upstream_transport.closed is True


def test_upstream_close_tears_down_downstream():
    """Backend hangs up first (the common HTTP/1.1 ``Connection: close`` path) ->
    the downstream client socket is closed too, so its FD is not leaked."""
    downstream, downstream_transport, client, _ = _wire_up_proxy_pair()

    client.connection_lost(None)

    assert downstream_transport.closed is True
