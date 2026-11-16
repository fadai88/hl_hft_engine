import logger, hl_tcp, hl_tls # type: ignore

HOST = "api.hyperliquid.xyz"
PORT = 443

sock = hl_tcp.tcp_open(HOST, PORT)
ssl_obj, incoming, outgoing = hl_tls.tls_handshake(sock, HOST)
hl_tcp.tcp_close(sock)
logger.close_log()