from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import time
import logging

# Configuração de Log para você ver tudo o que acontece no Render
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TitaniumServer")

app = FastAPI(title="Titanium Copy Engine V4")

# Permite conexões de qualquer lugar
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- BANCO DE DADOS EM MEMÓRIA (GAVETAS) ---
class TitaniumDB:
    def __init__(self):
        self.magics = {}   # Armazena volume, tipo e preço médio de cada Magic
        self.clients = {}  # Monitora o status de cada receptor
        self.master_status = "OFFLINE"
        self.last_master_update = 0

db = TitaniumDB()

@app.get("/")
async def health_check():
    agora = time.time()
    receptores_vivos = {name: f"{int(agora - ts)}s atrás" for name, ts in db.clients.items() if agora - ts < 60}
    return {
        "engine": "Titanium V4",
        "status": "Online",
        "master_last_seen": f"{int(agora - db.last_master_update)}s atrás" if db.last_master_update > 0 else "Nunca",
        "magics_na_gaveta": db.magics,
        "receptores_online": receptores_vivos
    }

@app.post("/sync-master")
async def sync_master(request: Request):
    try:
        data = await request.json()
        magic_id = str(data.get("magic"))
        
        if not magic_id:
            raise HTTPException(status_code=400, detail="Magic ID ausente")

        # Atualiza a Gaveta com precisão
        db.magics[magic_id] = {
            "type": data.get("type", "NONE"),
            "volume": float(data.get("volume", 0.0)),
            "price": float(data.get("price", 0.0)), # Caso queira expandir para preço depois
            "last_update": time.time()
        }
        
        db.last_master_update = time.time()
        db.master_status = "ONLINE"

        # Coleta Receptores Ativos para devolver ao Master
        agora = time.time()
        ativos = [{"client_name": n} for n, ts in db.clients.items() if agora - ts < 30]
        
        return {
            "status": "success",
            "active_receptors": ativos,
            "server_time": agora
        }
    except Exception as e:
        logger.error(f"Erro no Master: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/sync-client")
async def sync_client(request: Request):
    try:
        data = await request.json()
        nome_cliente = data.get("client_name", "REC_DESCONHECIDO")
        
        # Registra presença do Receptor
        db.clients[nome_cliente] = time.time()
        
        # O Receptor recebe a foto atual de TODAS as gavetas
        # Isso permite que ele ajuste todos os magics de uma vez só
        return db.magics
        
    except Exception as e:
        logger.error(f"Erro no Cliente {data.get('client_name')}: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # Porta dinâmica para o Render
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Iniciando Titanium Engine na porta {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
