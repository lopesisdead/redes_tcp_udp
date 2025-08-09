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

    # --- Ler cabeçalho até \n ---
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
    total_bytes = 0
    start_time = time.perf_counter()

    while received_msgs < msg_count:
        data = conn.recv(msg_size)
        if not data:
            break
        total_bytes += len(data)
        received_msgs += 1
        conn.sendall(b"ACK")

    elapsed = time.perf_counter() - start_time
    conn.close()
    sock.close()

    print(f"\n--- Resultados TCP ---")
    print(f"Tempo total: {elapsed:.4f}s")
    print(f"Throughput: {total_bytes / elapsed:.2f} bytes/s")
    print(f"Mensagens recebidas: {received_msgs}/{msg_count}")
    print(f"Perdas: {msg_count - received_msgs}")


def run_udp():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    print(f"[UDP] Servidor escutando em {HOST}:{PORT}")

    # 1º pacote: tam_msg e qtd_msgs
    header, addr = sock.recvfrom(1024)
    msg_size, msg_count = map(int, header.decode().strip().split(","))
    print(f"[UDP] Recebendo {msg_count} mensagens de {msg_size} bytes...")

    received_msgs = 0
    total_bytes = 0
    expected_seq = 1
    losses = 0

    start_time = time.perf_counter()
    while received_msgs < msg_count:
        try:
            data, addr = sock.recvfrom(msg_size + 20)
        except:
            continue
        if not data:
            continue

        # sequência no início da mensagem
        seq = int(data.split(b"|", 1)[0])
        if seq != expected_seq:
            losses += (seq - expected_seq)
            expected_seq = seq
        expected_seq += 1

        total_bytes += len(data)
        received_msgs += 1
        sock.sendto(b"ACK", addr)  # confirma recebimento

    elapsed = time.perf_counter() - start_time
    sock.close()

    print(f"\n--- Resultados UDP ---")
    print(f"Tempo total: {elapsed:.4f}s")
    print(f"Throughput: {total_bytes / elapsed:.2f} bytes/s")
    print(f"Mensagens recebidas: {received_msgs}/{msg_count}")
    print(f"Perdas detectadas: {losses}")

if __name__ == "__main__":
    if PROTO == "tcp":
        run_tcp()
    else:
        run_udp()
