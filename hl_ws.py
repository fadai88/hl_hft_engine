import ssl
from wsproto import WSConnection, ConnectionType
from wsproto.events import Request, AcceptConnection, RejectConnection
import hl_tls, logger

def ws_handshake(sock, ssl_obj, incoming, outgoing, hostname, path):
    ws = WSConnection(ConnectionType.CLIENT)
    # send the Request, log ws_upgrade_request, write + flush
    payload = ws.send(Request(host=hostname, target=path))
    logger.log("ws_upgrade_request", host=hostname, target=path)
    ssl_obj.write(payload)
    hl_tls.flush_outgoing(sock, outgoing)
    # receive loop until AcceptConnection or RejectConnection
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
                        logger.log("ws_upgrade_rejected", status_code=event.status_code, reason=event.reason)
                        raise ConnectionError(f"WebSocket upgrade rejected: {event.status_code} {event.reason}")
        except Exception as e:
            logger.log("ws_upgrade_error", error=str(e))
            raise
