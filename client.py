import socket
import sys
import time

PORT = 5001

if len(sys.argv) < 4:
    print(f"Uso: python {sys.argv[0]} <tcp|udp> <tam_msg> <qtd_msgs> [ip_servidor]")
    sys.exit(1)

PROTO = sys.argv[1].lower()
msg_size = int(sys.argv[2])
msg_count = int(sys.argv[3])
HOST = sys.argv[4] if len(sys.argv) >= 5 else "127.0.0.1"

payload = b"x" * (msg_size - 10)  # reserva espaço p/ seq num

if PROTO == "tcp":
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)  # timeout de segurança

    try:
        sock.connect((HOST, PORT))

        # envia cabeçalho com nova linha no final
        header = f"{msg_size},{msg_count}\n"
        sock.sendall(header.encode())

        sent_msgs = 0
        total_bytes = 0
        start_time = time.perf_counter()

        for seq in range(1, msg_count + 1):
            msg = f"{seq}|".encode() + payload

            while True:
                try:
                    sock.sendall(msg)
                    total_bytes += len(msg)

                    ack = sock.recv(3)
                    if not ack:
                        print("Conexão fechada pelo servidor.")
                        sock.close()
                        sys.exit(1)

                    if ack != b"ACK":
                        print(f"Erro: ACK inválido recebido: {ack}")
                        continue

                    sent_msgs += 1
                    break

                except socket.timeout:
                    print(f"Timeout ao enviar mensagem {seq}, tentando novamente...")
                    continue
                except ConnectionError as e:
                    print(f"Erro de conexão: {e}")
                    sock.close()
                    sys.exit(1)

        elapsed = time.perf_counter() - start_time
        print(f"\n--- Cliente TCP ---")
        print(f"Tempo total: {elapsed:.4f}s")
        print(f"Throughput: {total_bytes / elapsed:.2f} bytes/s")
        print(f"Mensagens enviadas: {sent_msgs}")

    except socket.error as e:
        print(f"Erro no socket: {e}")
    finally:
        sock.close()

else:  # Parte UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    addr = (HOST, PORT)

    # Envia cabeçalho
    sock.sendto(f"{msg_size},{msg_count}".encode(), addr)

    total_bytes = 0
    start_time = time.perf_counter()

    # Intervalo entre pacotes ajustável
    packet_interval = 0.0001  # 100μs (ajuste conforme necessário)

    for seq in range(1, msg_count + 1):
        msg = f"{seq}|".encode() + payload
        sock.sendto(msg, addr)
        total_bytes += len(msg)
        
        # Intervalo entre pacotes
        if msg_count > 500:  # Só aplica delay para grandes quantidades
            time.sleep(packet_interval)

    elapsed = time.perf_counter() - start_time
    sock.close()

    print(f"\n--- Cliente UDP (sem ACK) ---")
    print(f"Tempo total: {elapsed:.4f}s")
    print(f"Throughput: {total_bytes / elapsed:.2f} bytes/s")
    print(f"Mensagens enviadas: {msg_count}")
