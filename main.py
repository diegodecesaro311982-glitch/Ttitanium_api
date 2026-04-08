from fastapi import FastAPI, Request
import uvicorn
import os
import time

app = FastAPI()

# GAVETA GLOBAL: Armazena o estado de cada Magic separadamente
# Estrutura: { "60561": {"type": "BUY", "volume": 1.5, "last_update": ...}, ... }
gaveta_magics = {}

# MONITOR DE CLIENTES: Para o painel do Master saber quem está vivo
clientes_ativos = {}

@app.get("/")
async def status_check():
    return {"status": "Titanium Engine V2 Online", "magics_ativos": list(gaveta_magics.keys())}

@app.post("/sync-master")
async def sync_master(request: Request):
    try:
        data = await request.json()
        master_name = data.get("client_name", "DIEGO_MASTER")
        magic_id = str(data.get("magic")) # Transformamos em string para a gaveta
        
        # ATUALIZA A GAVETA DO MAGIC ESPECÍFICO
        gaveta_magics[magic_id] = {
            "type": data.get("type"),       # BUY, SELL ou NONE
            "volume": data.get("volume"),   # Volume total (acumulado do médio)
            "last_update": time.time()
        }
        
        # LIMPEZA E COLETA DE CLIENTES ONLINE
        agora = time.time()
        # Remove clientes que não dão sinal há mais de 20 segundos
        temp_clientes = [name for name, last_seen in clientes_ativos.items() if agora - last_seen < 20]
        
        # Devolve para o Master a lista de quem está online para o Painel
        return {
            "status": "ok",
            "active_receptors": [{"client_name": n} for n in temp_clientes]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/sync-client")
async def sync_client(request: Request):
    try:
        data = await request.json()
        nome = data.get("client_name", "DESCONHECIDO")
        
        # Registra presença do Receptor no Monitor
        clientes_ativos[nome] = time.time()
        
        # O Receptor recebe a gaveta inteira com todos os Magics e Volumes
        # Assim ele decide se abre médio, fecha ou reverte baseado no volume total
        return gaveta_magics
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # Configuração obrigatória para o RENDER
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
