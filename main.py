import logger, hl_tcp, hl_tls, hl_http, hl_ws # type: ignore
import h11, json
from wsproto.utilities import ProtocolError

HOST = "api.hyperliquid.xyz"
PORT = 443


def close_step(step, func, *args):
    # One failed close must not skip the remaining ones, and must not replace
    # the exception that brought us here. Only network/protocol errors are
    # swallowed; a coding mistake still raises.
    try:
        func(*args)
    except (OSError, ProtocolError) as e:
        logger.log("close_error", step=step, error_type=type(e).__name__, error=str(e))


# Each name stays None until that object exists, so the finally block knows
# exactly what has to be closed, however far we got.
sock_http = ssl_obj_http = incoming_http = outgoing_http = None
sock_ws = ssl_obj_ws = incoming_ws = outgoing_ws = ws = None

try:
    sock_http = hl_tcp.tcp_open(HOST, PORT)
    ssl_obj_http, incoming_http, outgoing_http = hl_tls.tls_handshake(sock_http, HOST)
    conn_http = h11.Connection(our_role=h11.CLIENT)
    hl_http.send_request(sock_http, ssl_obj_http, outgoing_http, conn_http, "/info", b'{"type": "meta"}', HOST)
    status_code, response_body_bytes = hl_http.read_response(sock_http, ssl_obj_http, incoming_http, conn_http)

    if status_code != 200:
        raise Exception(f"HTTP request failed with status code {status_code}")
    else:
        universe = json.loads(response_body_bytes.decode("utf-8"))
        tokens = [token['name'] for token in universe['universe']]

    sock_ws = hl_tcp.tcp_open(HOST, PORT)
    ssl_obj_ws, incoming_ws, outgoing_ws = hl_tls.tls_handshake(sock_ws, HOST)
    ws = hl_ws.ws_handshake(sock_ws, ssl_obj_ws, incoming_ws, outgoing_ws, HOST, path="/ws")

except BaseException as e:
    # Record why we're shutting down (including Ctrl+C), then let it propagate.
    logger.log("fatal_error", error_type=type(e).__name__, error=str(e))
    raise

finally:
    if ws is not None:
        close_step("ws_close", hl_ws.ws_close, sock_ws, ssl_obj_ws, incoming_ws, outgoing_ws, ws)
    if ssl_obj_ws is not None:
        close_step("tls_close_ws", hl_tls.tls_close, sock_ws, ssl_obj_ws, incoming_ws, outgoing_ws)
    if sock_ws is not None:
        close_step("tcp_close_ws", hl_tcp.tcp_close, sock_ws)

    if ssl_obj_http is not None:
        close_step("tls_close_http", hl_tls.tls_close, sock_http, ssl_obj_http, incoming_http, outgoing_http)
    if sock_http is not None:
        close_step("tcp_close_http", hl_tcp.tcp_close, sock_http)

    logger.close_log()
