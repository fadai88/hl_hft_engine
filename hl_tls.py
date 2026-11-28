import ssl, socket
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

def tls_close(sock, ssl_obj, incoming, outgoing, timeout=5):
    # Send our close_notify, then wait for the server's. Many servers just drop
    # the TCP connection instead of replying, which is fine: we only record it.
    logger.log("tls_closing")
    sock.settimeout(timeout)
    outcome = "peer_replied"
    try:
        while True:
            try:
                ssl_obj.unwrap()
                break
            except ssl.SSLWantReadError:
                flush_outgoing(sock, outgoing)
                received_data = sock.recv(65536)
                if not received_data:
                    outcome = "tcp_closed_by_peer"
                    break
                incoming.write(received_data)
    except socket.timeout:
        outcome = "timeout"
    except (ConnectionResetError, BrokenPipeError):
        outcome = "connection_reset"
    logger.log("tls_closed", outcome=outcome)
