import ssl
from wsproto import WSConnection, ConnectionType
from wsproto.events import Request, AcceptConnection, RejectConnection
import hl_tls, logger

def ws_handshake(sock, ssl_obj, incoming, outgoing, hostname, path):
    # create ws = WSConnection(ConnectionType.CLIENT)
    # send the Request, log ws_upgrade_request, write + flush
    # receive loop until AcceptConnection or RejectConnection
    return ws