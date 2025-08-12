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

    # A leitura do cabeçalho está OK, embora ler 1 byte por vez seja ineficiente.
    # Para este teste, não é um problema.
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

    while received_msgs < msg_count:
        # --- INÍCIO DA CORREÇÃO ---
        bytes_da_mensagem_atual = b""
        bytes_faltando = msg_size
        
        # Este loop garante que leremos uma mensagem completa de 'msg_size'
        while len(bytes_da_mensagem_atual) < msg_size:
            # Pedimos para receber apenas os bytes que ainda faltam para completar a mensagem
            chunk = conn.recv(bytes_faltando)
            if not chunk:
                # Se recv() retorna vazio, a conexão foi fechada pelo cliente
                print("Conexão encerrada prematuramente pelo cliente.")
                break
            
            bytes_da_mensagem_atual += chunk
            bytes_faltando -= len(chunk)
        
        if len(bytes_da_mensagem_atual) != msg_size:
            # Se saímos do loop sem a mensagem completa, algo deu errado
            break
        # --- FIM DA CORREÇÃO ---

        # Agora 'bytes_da_mensagem_atual' contém a mensagem completa
        total_bytes_received += len(bytes_da_mensagem_atual)
        received_msgs += 1
        conn.sendall(b"ACK")

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
    
    # IMPORTANTE: Definimos um timeout no socket.
    # Se recvfrom() não receber nada em 2.0 segundos, ele lançará uma exceção.
    sock.settimeout(2.0)
    
    sock.bind((HOST, PORT))
    print(f"[UDP] Servidor escutando em {HOST}:{PORT}")

    try:
        # Ainda precisamos do cabeçalho para saber o total esperado
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
    
    # O loop agora é infinito e só será quebrado pelo timeout.
    while True:
        try:
            data, _ = sock.recvfrom(BUFFER)
            
            # Se for a primeira mensagem, marca o tempo de início
            if start_time == 0:
                start_time = time.perf_counter()

            # Atualiza o tempo de fim a cada pacote recebido
            end_time = time.perf_counter()
            
            received_msgs += 1
            total_bytes += len(data)

        except socket.timeout:
            # Se chegamos aqui, significa que se passaram 2s sem receber pacotes.
            # Assumimos que a transmissão terminou.
            print("[UDP] Timeout detectado. Finalizando a recepção.")
            break # Quebra o loop "while True"

    sock.close()

    # --- Lógica de cálculo dos resultados ---
    # A perda total é simplesmente o que o cliente disse que enviaria vs. o que recebemos.
    total_loss = msg_count - received_msgs
    elapsed = end_time - start_time if start_time > 0 else 0

    print(f"\n--- Resultados UDP ---")
    if elapsed > 0:
        print(f"Tempo de transmissão (do primeiro ao último pacote): {elapsed:.4f}s")
        print(f"Throughput (dados recebidos): {total_bytes / elapsed:.2f} bytes/s")
    else:
        print("Nenhuma mensagem de dados foi recebida.")
        
    print(f"Mensagens recebidas: {received_msgs}/{msg_count}")
    print(f"Total de perdas: {total_loss}")

if __name__ == "__main__":
    if PROTO == "tcp":
        run_tcp()
    else:
        run_udp()