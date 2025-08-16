import socket
import sys
import time

BUFFER = 65536
HOST = "0.0.0.0"
PORT = 5001

if len(sys.argv) < 2 or sys.argv[1] not in ("tcp", "udp"):
    print(f"Uso: python {sys.argv[0]} <tcp|udp>")
    sys.exit(1)

PROTO = sys.argv[1].lower()

def run_tcp():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((HOST, PORT))
    sock.listen(1)
    print(f"[TCP] Servidor escutando em {HOST}:{PORT}")
    conn, addr = sock.accept()
    print(f"[TCP] Conexão de {addr}")

    # leitura do cabeçalho
    header_data = b""
    while b"\n" not in header_data:
        chunk = conn.recv(1)
        if not chunk:
            print("Conexão encerrada antes do cabeçalho")
            conn.close()
            return
        header_data += chunk

    header = header_data.decode().strip()
    msg_size, msg_count = map(int, header.split(","))
    print(f"[TCP] Recebendo {msg_count} mensagens de {msg_size} bytes...")

    received_msgs = 0
    total_bytes_received = 0
    start_time = time.perf_counter()

    conn.settimeout(5.0)

    try:
        while received_msgs < msg_count:
            bytes_da_mensagem_atual = b""
            bytes_faltando = msg_size

            while len(bytes_da_mensagem_atual) < msg_size:
                try:
                    chunk = conn.recv(bytes_faltando)
                    if not chunk:
                        # cliente fechou a conexão
                        if received_msgs < msg_count:
                            print("Conexão encerrada prematuramente pelo cliente.")
                        conn.close()
                        sock.close()
                        return
                    bytes_da_mensagem_atual += chunk
                    bytes_faltando -= len(chunk)
                except socket.timeout:
                    print("Timeout ao esperar mensagem completa")
                    break

            if len(bytes_da_mensagem_atual) != msg_size:
                print(f"Mensagem incompleta recebida ({len(bytes_da_mensagem_atual)}/{msg_size})")
                continue  # tenta próxima

            total_bytes_received += len(bytes_da_mensagem_atual)
            received_msgs += 1
            conn.sendall(b"ACK")

    except socket.timeout:
        print("Timeout geral na conexão TCP")
    except ConnectionResetError:
        print("Conexão resetada pelo cliente")

    elapsed = time.perf_counter() - start_time
    conn.close()
    sock.close()

    print(f"\n--- Resultados TCP ---")
    print(f"Tempo total: {elapsed:.4f}s")
    if elapsed > 0:
        print(f"Throughput: {total_bytes_received / elapsed:.2f} bytes/s")
    print(f"Mensagens recebidas: {received_msgs}/{msg_count}")
    print(f"Perdas (mensagens não recebidas): {msg_count - received_msgs}")

def run_udp():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5.0)
    sock.bind((HOST, PORT))
    print(f"[UDP] Servidor escutando em {HOST}:{PORT}")

    try:
        header, addr = sock.recvfrom(1024)
        msg_size, msg_count = map(int, header.decode().strip().split(","))
        print(f"[UDP] Recebendo {msg_count} mensagens de {msg_size} bytes de {addr}...")
    except socket.timeout:
        print("[UDP] Timeout: Nenhuma comunicação iniciada. Servidor desligando.")
        sock.close()
        return

    received_msgs = 0
    total_bytes = 0
    start_time = 0
    end_time = 0
    expected_end_time = time.perf_counter() + 10.0

    while received_msgs < msg_count and time.perf_counter() < expected_end_time:
        try:
            data, _ = sock.recvfrom(msg_size + 100)
            if start_time == 0:
                start_time = time.perf_counter()

            if len(data) >= msg_size - 10:
                received_msgs += 1
                total_bytes += len(data)
                end_time = time.perf_counter()
            else:
                print(f"[UDP] Pacote muito pequeno recebido: {len(data)} bytes")

        except socket.timeout:
            print(f"[UDP] Timeout parcial. Recebidos {received_msgs}/{msg_count}")
            break

    sock.close()

    total_loss = msg_count - received_msgs
    elapsed = end_time - start_time if start_time > 0 else 0

    print(f"\n--- Resultados UDP ---")
    if elapsed > 0:
        print(f"Tempo de transmissão: {elapsed:.4f}s")
        print(f"Throughput: {total_bytes / elapsed:.2f} bytes/s")
    else:
        print("Nenhuma mensagem de dados foi recebida.")
    print(f"Mensagens recebidas: {received_msgs}/{msg_count}")
    print(f"Total de perdas: {total_loss}")

if __name__ == "__main__":
    if PROTO == "tcp":
        run_tcp()
    else:
        run_udp()
