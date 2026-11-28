import ssl, socket
from wsproto import WSConnection, ConnectionType
from wsproto.connection import ConnectionState
from wsproto.events import Request, AcceptConnection, RejectConnection, CloseConnection
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

def ws_close(sock, ssl_obj, incoming, outgoing, ws, code=1000, reason="client closing", timeout=5):
    # Already fully closed: nothing to send.
    if ws.state not in (ConnectionState.OPEN, ConnectionState.REMOTE_CLOSING):
        logger.log("ws_close_skipped", state=ws.state.name)
        return
    # In REMOTE_CLOSING the server closed first and this frame is our reply;
    # in OPEN we start the close and must wait for the server's reply.
    payload = ws.send(CloseConnection(code=code, reason=reason))
    ssl_obj.write(payload)
    hl_tls.flush_outgoing(sock, outgoing)
    logger.log("ws_close_sent", code=code, reason=reason)
    if ws.state is ConnectionState.CLOSED:
        logger.log("ws_closed", initiator="server")
        return
    sock.settimeout(timeout)
    try:
        while True:
            data = sock.recv(65536)
            if not data:
                logger.log("ws_close_unacknowledged", why="tcp_closed_by_peer")
                return
            incoming.write(data)
            while True:
                try:
                    incoming_data = ssl_obj.read(65536)
                    if not incoming_data:
                        logger.log("ws_close_unacknowledged", why="tls_closed_by_peer")
                        return
                    ws.receive_data(incoming_data)
                except ssl.SSLWantReadError:
                    break
                # Messages still in flight before the server's close reply are dropped.
                for event in ws.events():
                    if isinstance(event, CloseConnection):
                        logger.log("ws_closed", initiator="client", code=event.code, reason=event.reason)
                        return
    except socket.timeout:
        logger.log("ws_close_unacknowledged", why="timeout")
    except (ConnectionResetError, BrokenPipeError):
        logger.log("ws_close_unacknowledged", why="connection_reset")
    except (ssl.SSLError, RemoteProtocolError) as e:
        logger.log("ws_close_error", error=str(e))
        raise
