import socket
import logger # type: ignore


def tcp_open(hostname, port):
    sock = socket.socket()
    logger.log("dns_resolving", host=hostname, port=port)
    infos = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    ip = infos[0][4][0]
    ips = [info[4][0] for info in infos]
    logger.log("dns_resolved", ips=ips)

    logger.log("tcp_connecting", ip=ip, port=port)
    sock.connect((ip, port))
    logger.log("tcp_opened")

    return sock

def tcp_close(sock_connected):
    logger.log("tcp_closing")
    sock_connected.close()
    logger.log("tcp_closed")

