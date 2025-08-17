# run_tests.py
import subprocess
import sys
import time
import re
from collections import defaultdict

# --- Configurações dos Testes ---

# IP do servidor. Mude para o IP da máquina remota se não for um teste local.
# Você também pode passar como argumento na linha de comando.
SERVER_IP = "127.0.0.1"

# Número de vezes que cada cenário de teste será executado.
NUM_RUNS = 5

# Definição dos cenários de teste: (protocolo, tamanho_msg, qtd_msgs)
TEST_CASES = [
    ("udp", 100, 100),
    ("udp", 1000, 1000),
    ("udp", 5000, 5000),
    ("tcp", 100, 100),
    ("tcp", 1000, 1000),
    ("tcp", 5000, 5000),
]

# --- Funções Auxiliares ---

def parse_output(output):
    """Extrai métricas (throughput, perdas, tempo) da saída de texto dos scripts."""
    results = {}
    
    # Expressões regulares para encontrar os valores
    throughput_re = re.search(r"Throughput: ([\d.]+) bytes/s", output)
    loss_re = re.search(r"(Perdas|Total de perdas|mensagens não recebidas): (\d+)", output)
    time_re = re.search(r"Tempo total: ([\d.]+)s", output)

    if throughput_re:
        results["throughput"] = float(throughput_re.group(1))
    if loss_re:
        results["loss"] = int(loss_re.group(2))
    if time_re:
        results["time"] = float(time_re.group(1))
        
    return results

def run_single_test(proto, msg_size, msg_count, server_ip):
    """Executa um único teste (servidor + cliente) e retorna a saída de ambos."""
    
    # Comando para iniciar o servidor
    server_cmd = [sys.executable, "server.py", proto]
    
    # Inicia o servidor em um novo processo
    # stdout=subprocess.PIPE captura a saída para análise
    server_proc = subprocess.Popen(server_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Pequena pausa para garantir que o servidor esteja escutando
    time.sleep(1) 
    
    # Comando para iniciar o cliente
    client_cmd = [sys.executable, "client.py", proto, str(msg_size), str(msg_count), server_ip]
    
    # Inicia o cliente e espera ele terminar
    client_proc = subprocess.Popen(client_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Captura a saída do cliente
    try:
        client_output, client_error = client_proc.communicate(timeout=30) # Timeout de 30s
    except subprocess.TimeoutExpired:
        client_proc.kill()
        client_output, client_error = client_proc.communicate()
        client_error += "\nCLIENTE FINALIZADO POR TIMEOUT!"

    # Termina o servidor e captura sua saída
    server_proc.terminate() 
    try:
        server_output, server_error = server_proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        server_proc.kill()
        server_output, server_error = server_proc.communicate()
        server_error += "\nSERVIDOR FINALIZADO POR TIMEOUT!"

    return client_output, server_output, client_error, server_error


# --- Script Principal ---

def main():
    # Permite sobrescrever o IP do servidor via linha de comando
    server_ip = sys.argv[1] if len(sys.argv) > 1 else SERVER_IP
    print(f"Iniciando bateria de testes para o servidor em: {server_ip}\n")
    
    # Dicionário para armazenar todos os resultados
    all_results = defaultdict(lambda: defaultdict(list))

    # Loop principal pelos cenários de teste
    for proto, msg_size, msg_count in TEST_CASES:
        test_id = f"{proto.upper()}_{msg_size}b_{msg_count}msgs"
        print(f"--- Executando testes para: {test_id} ---")

        for i in range(NUM_RUNS):
            print(f"  Rodada {i + 1}/{NUM_RUNS}...")
            client_out, server_out, client_err, server_err = run_single_test(
                proto, msg_size, msg_count, server_ip
            )
            
            # Se houve algum erro, imprime para debug
            if client_err:
                print(f"    [ERRO CLIENTE]:\n{client_err}")
            if server_err:
                print(f"    [ERRO SERVIDOR]:\n{server_err}")

            # Extrai os resultados da saída do cliente e do servidor
            client_results = parse_output(client_out)
            server_results = parse_output(server_out)
            
            # Armazena os resultados. Prioriza throughput do cliente e perdas do servidor.
            if "throughput" in client_results:
                all_results[test_id]["throughput"].append(client_results["throughput"])
            if "loss" in server_results:
                all_results[test_id]["loss"].append(server_results["loss"])
            if "time" in client_results:
                all_results[test_id]["time"].append(client_results["time"])
        print("-" * (25 + len(test_id)))
        print()


    # --- Geração do Relatório ---
    print("\n\n========================================")
    print("      RELATÓRIO FINAL DE MÉDIAS")
    print("========================================")

    for test_id, metrics in all_results.items():
        print(f"\nResultados para [{test_id}]:")
        
        # Calcula e exibe a média do Throughput
        if metrics["throughput"]:
            avg_throughput = sum(metrics["throughput"]) / len(metrics["throughput"])
            print(f"  - Throughput Médio: {avg_throughput:,.2f} bytes/s")
        
        # Calcula e exibe a média do Tempo
        if metrics["time"]:
            avg_time = sum(metrics["time"]) / len(metrics["time"])
            print(f"  - Tempo Médio.....: {avg_time:.4f} s")
            
        # Calcula e exibe a média de Perdas
        if metrics["loss"]:
            avg_loss = sum(metrics["loss"]) / len(metrics["loss"])
            # Extrai o número de mensagens enviadas do ID do teste
            total_sent = int(test_id.split('_')[2].replace('msgs', ''))
            loss_percent = (avg_loss / total_sent) * 100 if total_sent > 0 else 0
            print(f"  - Perda Média.....: {avg_loss:.2f} pacotes ({loss_percent:.2f}%)")

if __name__ == "__main__":
    main()