from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import logging

# Configuração de Log para monitorar erros no Render
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Banco de dados em memória (Snapshot por Bloco)
# Estrutura: { "NOME_MASTER": { "MAGIC_ID": { "dados" } } }
db_snapshots = {}
# Registro de atividade dos clientes para o painel ON/OFF
active_clients = {}

@app.route('/')
def health_check():
    return "<h1>Titanium API v41.0 - Online</h1>", 200

@app.route('/sync-master', methods=['POST'])
def sync_master():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data"}), 400
            
        master_name = data.get('client_name', 'DEFAULT_MASTER')
        magic = str(data.get('magic'))
        volume = float(data.get('volume', 0))
        
        if master_name not in db_snapshots:
            db_snapshots[master_name] = {}
        
        # LÓGICA DE BLOCO: Se volume é 0, removemos o bloco para não virar "lixo"
        if volume <= 0:
            db_snapshots[master_name].pop(magic, None)
        else:
            db_snapshots[master_name][magic] = {
                "magic": int(magic),
                "type": data.get('type'),
                "volume": volume,
                "price": data.get('price', 0),
                "session": int(time.time())
            }
        
        # Retorna a lista de clientes que pediram dados desse master nos últimos 30s
        clients_on = [c for c, t in active_clients.items() if t > (time.time() - 30)]
        return jsonify({"status": "success", "active_clients": clients_on}), 200

    except Exception as e:
        logger.error(f"Master Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/sync-client', methods=['POST'])
def sync_client():
    try:
        data = request.json
        client_name = data.get('client_name', 'UNKNOWN_CLIENT')
        target_master = data.get('target_master', 'DIEGO_MASTER')
        
        # Registra que o cliente está online
        active_clients[client_name] = time.time()
        
        if target_master not in db_snapshots:
            return jsonify([]), 200
            
        # Filtra apenas blocos atualizados no último minuto (Anti-Fantasma)
        agora = int(time.time())
        snapshot = [
            info for magic, info in db_snapshots[target_master].items() 
            if info['session'] > (agora - 60)
        ]
        
        return jsonify(snapshot), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
