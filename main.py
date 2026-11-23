import logger, hl_tcp, hl_tls, hl_http # type: ignore
import h11, json

HOST = "api.hyperliquid.xyz"
PORT = 443

sock = hl_tcp.tcp_open(HOST, PORT)
ssl_obj, incoming, outgoing = hl_tls.tls_handshake(sock, HOST)
conn = h11.Connection(our_role=h11.CLIENT)
hl_http.send_request(sock, ssl_obj, outgoing, conn, "/info", b'{"type": "meta"}', HOST)
status_code, response_body_bytes = hl_http.read_response(sock, ssl_obj, incoming, conn)

if status_code != 200:
    raise Exception(f"HTTP request failed with status code {status_code}")
else:
    universe = json.loads(response_body_bytes.decode("utf-8"))
    tokens = [token['name'] for token in universe['universe']]

hl_tcp.tcp_close(sock)
logger.close_log()