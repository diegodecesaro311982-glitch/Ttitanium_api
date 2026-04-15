from flask import Flask, request, jsonify
import time
import threading

app = Flask(__name__)

# --- BANCO DE DADOS EM MEMÓRIA (ALTA PERFORMANCE) ---
# Estrutura: { "60561": "TK1:B:0.1|TK2:B:0.1", "63370": "EMPTY" }
titanium_db = {
    "orders": {},
    "clients": {},  # { "nome_cliente": timestamp }
    "master_last_seen": 0
}

# Lock para evitar conflitos de leitura/escrita simultânea (Preço Médio rápido)
db_lock = threading.Lock()

@app.route('/')
def health_check():
    return "Titanium Brain V1.3 - Online", 200

@app.route('/sync', methods=['POST'])
def sync_protocol():
    global titanium_db
    data = request.json
    now = time.time()

    if not data:
        return jsonify({"error": "No data received"}), 400

    # --- IDENTIFICAÇÃO DO COMANDANTE (MASTER) ---
    if 'm' in data:
        with db_lock:
            titanium_db["master_last_seen"] = now
            # Atualiza cada Magic Number enviado (Hedge/Médio)
            # Esperado: [{"id": 60561, "l": "..."}, {"id": 63370, "l": "..."}]
            for entry in data.get('d', []):
                m_id = str(entry.get('id'))
                titanium_db["orders"][m_id] = entry.get('l', 'EMPTY')

            # Filtra apenas clientes que deram sinal nos últimos 15 segundos
            active_clients = [
                name for name, last_seen in titanium_db["clients"].items() 
                if (now - last_seen) < 15
            ]
        
        # O Master recebe a lista de nomes para o painel do MT5
        return ",".join(active_clients), 200

    # --- IDENTIFICAÇÃO DO RECEPTOR (CLIENT) ---
    if 'client' in data:
        c_name = data.get('client')
        with db_lock:
            titanium_db["clients"][c_name] = now
            # O Receptor puxa o estado atual de todos os Magics
            current_orders = titanium_db["orders"]
        
        return jsonify(current_orders), 200

    return "Invalid Protocol", 400

# --- LIMPEZA AUTOMÁTICA DE MEMÓRIA (OPCIONAL/ROBUSTEZ) ---
def auto_cleanup():
    while True:
        time.sleep(60)
        now = time.time()
        with db_lock:
            # Remove clientes offline há mais de 5 minutos para não pesar
            expired = [n for n, t in titanium_db["clients"].items() if (now - t) > 300]
            for n in expired:
                del titanium_db["clients"][n]

# Inicia a limpeza em uma thread separada para não travar a latência
threading.Thread(target=auto_cleanup, daemon=True).start()

if __name__ == '__main__':
    # O Render usa a porta da variável de ambiente PORT
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
