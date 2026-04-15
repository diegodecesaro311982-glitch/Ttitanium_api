from flask import Flask, request, jsonify
import time
import threading
import os
import logging

# Configuração de Logs para você acompanhar pelo painel do Render
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- ESTRUTURA DE DADOS DE ALTA DISPONIBILIDADE ---
class TitaniumState:
    def __init__(self):
        # Armazena as ordens por Magic: {"60561": "TK1:B:0.1|TK2:B:0.1"}
        self.master_magics = {}
        # Armazena os clientes online: {"NOME": timestamp}
        self.connected_clients = {}
        # Timestamp do último sinal do Master
        self.last_master_beat = 0
        # Lock para evitar que dois clientes acessem o dado ao mesmo tempo (Hedge Safety)
        self.lock = threading.Lock()

state = TitaniumState()

@app.route('/')
def health():
    uptime = time.time() - state.start_time if hasattr(state, 'start_time') else 0
    return jsonify({
        "status": "online",
        "version": "1.5.0-ULTRA",
        "active_magics": len(state.master_magics),
        "active_clients": len(state.connected_clients)
    }), 200

@app.route('/sync', methods=['POST'])
def sync_protocol():
    payload = request.json
    now = time.time()

    if not payload:
        return jsonify({"error": "Empty payload"}), 400

    # ------------------------------------------------------------------
    # LÓGICA DO MASTER (COMANDANTE)
    # ------------------------------------------------------------------
    if 'm' in payload:
        master_id = payload.get('m')
        data_list = payload.get('d', []) # Lista de Magics e seus Tickets
        
        with state.lock:
            state.last_master_beat = now
            # Processa cada Magic individualmente (Hedge e Preço Médio)
            for entry in data_list:
                m_id = str(entry.get('id'))
                m_list = entry.get('l', 'EMPTY')
                
                # Se mudou de Compra para Venda (Reversão), o estado é sobrescrito aqui
                state.master_magics[m_id] = m_list
                
            # Identifica quem são os Receptores ativos (últimos 15 segundos)
            active_names = [
                name for name, last_seen in state.connected_clients.items() 
                if (now - last_seen) < 15
            ]
            
        # O Master recebe como resposta a lista de quem ele está comandando
        return ",".join(active_names), 200

    # ------------------------------------------------------------------
    # LÓGICA DO RECEPTOR (SOLDADO)
    # ------------------------------------------------------------------
    if 'client' in payload:
        client_name = payload.get('client')
        
        with state.lock:
            # Registra a presença do cliente no servidor
            state.connected_clients[client_name] = now
            # O Receptor puxa TODOS os magics. Ele decide localmente qual seguir.
            # Isso permite que um único Receptor siga vários Masters se necessário.
            current_snapshot = state.master_magics
            
        return jsonify(current_snapshot), 200

    return jsonify({"error": "Invalid protocol identification"}), 400

# ------------------------------------------------------------------
# SISTEMA DE PROTEÇÃO E LIMPEZA (WATCHDOG)
# ------------------------------------------------------------------
def memory_guard():
    """ Limpa dados antigos para manter a latência zero na RAM do Render """
    while True:
        time.sleep(30)
        current_now = time.time()
        with state.lock:
            # 1. Remove clientes offline há mais de 2 minutos
            expired_clients = [
                name for name, last_seen in state.connected_clients.items() 
                if (current_now - last_seen) > 120
            ]
            for name in expired_clients:
                del state.connected_clients[name]
                logger.info(f"Cliente {name} removido por inatividade.")

            # 2. Se o Master sumir por mais de 1 hora, limpa os Magics por segurança
            if (current_now - state.last_master_beat) > 3600:
                state.master_magics.clear()
                logger.warning("Master offline há muito tempo. Magics limpos por proteção.")

# Inicia a thread de proteção em background
state.start_time = time.time()
threading.Thread(target=memory_guard, daemon=True).start()

# ------------------------------------------------------------------
# INICIALIZAÇÃO DO SERVIDOR
# ------------------------------------------------------------------
if __name__ == '__main__':
    # O Render fornece a porta automaticamente na variável de ambiente PORT
    port = int(os.environ.get("PORT", 5000))
    # Rodar com debug=False para garantir a máxima performance
    app.run(host='0.0.0.0', port=port, debug=False)
