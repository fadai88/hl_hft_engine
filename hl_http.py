import ssl, h11
import hl_tls, logger # type: ignore

def send_request(sock, ssl_obj, outgoing, conn, path, body, hostname):
    request = h11.Request(method="POST",
            target=path,
            headers=[("Host", hostname), 
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(body)))])

    chunks = [
        conn.send(request),
        conn.send(h11.Data(data=body)),
        conn.send(h11.EndOfMessage()),
    ]
    payload = b"".join(chunk for chunk in chunks if chunk)
    logger.log("http_request", method=request.method.decode(), target=request.target.decode(), 
            headers=[(header[0].decode(), header[1].decode()) for header in request.headers], body=body.decode())
    ssl_obj.write(payload)
    hl_tls.flush_outgoing(sock, outgoing)


def read_response(sock, ssl_obj, incoming, conn):
    status_code = None
    body_bytes = b""
    done = False
    # Read response
    while not done:
        try:
            data = sock.recv(65536)
            if not data:
                logger.log("tcp_closed_by_peer")
                raise ConnectionError("Connection closed by server")
            incoming.write(data)
            while True:
                try:
                    incoming_data = ssl_obj.read(65536)
                    conn.receive_data(incoming_data)
                    if not incoming_data:
                        logger.log("tls_closed_by_peer")
                        break
                except ssl.SSLWantReadError:
                    break
            while True:
                event = conn.next_event()
                if event is h11.NEED_DATA:
                    break
                elif isinstance(event, h11.Response):
                    decoded_byte_pairs = [(byte_pair[0].decode("utf-8"), byte_pair[1].decode("utf-8")) for byte_pair in event.headers]
                    logger.log("http_response_headers", status_code=event.status_code, headers=decoded_byte_pairs)
                    status_code = event.status_code
                elif isinstance(event, h11.Data):
                    body_bytes += event.data
                elif isinstance(event, h11.EndOfMessage):
                    logger.log("http_response_body", body=body_bytes.decode())
                    done = True
                    break
        except h11.RemoteProtocolError as e:
            logger.log("http_protocol_error", error=str(e))
            raise
    return status_code, body_bytes
