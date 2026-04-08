from flask import Flask, request, jsonify
from flask_cors import CORS
import time

app = Flask(__name__)
CORS(app)

# ESTRUTURA DE DADOS: { "NOME_DO_CLIENTE": { "MAGIC_ID": { "dados_da_ordem" } } }
# Isso garante que cada robô tenha apenas UMA linha por cliente.
db_snapshots = {}

@app.route('/')
def home():
    return "Titanium API - Sistema de Blocos Ativo", 200

# --- ROTA DO MASTER (ENVIA OS DADOS) ---
@app.route('/sync-master', methods=['POST'])
def sync_master():
    try:
        data = request.json
        client_name = data.get('client_name', 'MASTER_DEFAULT')
        magic = str(data.get('magic'))
        
        # Se o cliente não existe no "banco", cria o bloco dele
        if client_name not in db_snapshots:
            db_snapshots[client_name] = {}
            
        # Grava ou SOBRESCREVE o bloco do Magic específico
        # Se o volume for 0, nós removemos do bloco para limpar o lixo
        volume = float(data.get('volume', 0))
        if volume <= 0:
            if magic in db_snapshots[client_name]:
                del db_snapshots[client_name][magic]
        else:
            db_snapshots[client_name][magic] = {
                "magic": int(magic),
                "type": data.get('type'),
                "volume": volume,
                "price": data.get('price', 0),
                "session": int(time.time()) # Marca o tempo exato da escrita
            }
            
        return jsonify({"status": "success", "message": f"Bloco {magic} atualizado"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# --- ROTA DO RECEPTOR (LÊ OS DADOS) ---
@app.route('/sync-client', methods=['POST'])
def sync_client():
    try:
        data = request.json
        target_master = data.get('target_master', 'DIEGO_MASTER') # Qual master ele deve seguir
        agora = int(time.time())
        
        if target_master not in db_snapshots:
            return jsonify([]), 200
            
        # FILTRO DE SEGURANÇA: Só envia o que foi atualizado nos últimos 60 segundos
        # Isso mata as "ordens fantasmas" que ficam presas no cache
        current_state = []
        for magic, info in db_snapshots[target_master].items():
            if info['session'] > (agora - 60):
                current_state.append(info)
        
        return jsonify(current_state), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# --- ROTA DE MONITORAMENTO (PARA VOCÊ VER NO NAVEGADOR) ---
@app.route('/dashboard', methods=['GET'])
def dashboard():
    return jsonify(db_snapshots), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
