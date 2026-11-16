import ssl
import logger # type: ignore


def flush_outgoing(sock, outgoing):
    while True:
        data = outgoing.read()
        if not data:
            break
        sock.sendall(data)

def tls_handshake(sock, hostname):
    context = ssl.create_default_context()
    incoming = ssl.MemoryBIO()
    outgoing = ssl.MemoryBIO()

    ssl_obj = context.wrap_bio(
        incoming,
        outgoing,
        server_hostname=hostname
    )
    logger.log("tls_handshake_start")
    while True:
        try:
            ssl_obj.do_handshake()
            flush_outgoing(sock, outgoing)
            break
        except ssl.SSLWantReadError:
            # The SSL object needs more data to continue the handshake
            flush_outgoing(sock, outgoing)
            # Receive more data from the server
            received_data = sock.recv(65536)
            if not received_data:
                logger.log("tcp_closed_by_peer")
                raise ConnectionError("Connection closed by server")
            incoming.write(received_data)
    logger.log("tls_handshake_done", tls_version=ssl_obj.version())
    return ssl_obj, incoming, outgoing
