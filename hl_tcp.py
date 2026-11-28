import socket
import logger # type: ignore


def tcp_open(hostname, port):
    logger.log("dns_resolving", host=hostname, port=port)
    infos = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    ip = infos[0][4][0]
    ips = [info[4][0] for info in infos]
    logger.log("dns_resolved", ips=ips)

    # Created after DNS so a DNS failure leaves nothing to close, and with the
    # address's family (IPv4 or IPv6) so the socket can actually reach it.
    sock = socket.socket(infos[0][0], socket.SOCK_STREAM)
    logger.log("tcp_connecting", ip=ip, port=port)
    try:
        sock.connect((ip, port))
    except OSError as e:
        # The caller never receives this socket, so it must be closed here.
        logger.log("tcp_connect_failed", ip=ip, port=port, error=str(e))
        sock.close()
        raise
    logger.log("tcp_opened")

    return sock

def tcp_close(sock_connected):
    logger.log("tcp_closing")
    sock_connected.close()
    logger.log("tcp_closed")

