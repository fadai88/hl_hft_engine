import ssl
from wsproto import WSConnection, ConnectionType
from wsproto.events import Request, AcceptConnection, RejectConnection
from wsproto.utilities import RemoteProtocolError
import hl_tls, logger

def ws_handshake(sock, ssl_obj, incoming, outgoing, hostname, path):
    ws = WSConnection(ConnectionType.CLIENT)
    payload = ws.send(Request(host=hostname, target=path))
    logger.log("ws_upgrade_request", payload=payload.decode())
    ssl_obj.write(payload)
    hl_tls.flush_outgoing(sock, outgoing)
    while True:
        data = sock.recv(65536)
        if not data:
            logger.log("tcp_closed_by_peer")
            raise ConnectionError("Connection closed by server")
        incoming.write(data)
        try:
            while True:
                try:
                    incoming_data = ssl_obj.read(65536)
                    if not incoming_data:
                        logger.log("tls_closed_by_peer")
                        raise ConnectionError("server closed the connection during WebSocket handshake")
                    ws.receive_data(incoming_data)
                except ssl.SSLWantReadError:
                    break
                for event in ws.events():
                    if isinstance(event, AcceptConnection):
                        logger.log("ws_accepted")
                        return ws
                    elif isinstance(event, RejectConnection):
                        headers = [(name.decode(), value.decode()) for name, value in event.headers]
                        logger.log("ws_upgrade_rejected", status_code=event.status_code, headers=headers)
                        raise ConnectionError(f"WebSocket upgrade rejected: {event.status_code}")
        except (ssl.SSLError, RemoteProtocolError) as e:
            logger.log("ws_upgrade_error", error=str(e))
            raise
