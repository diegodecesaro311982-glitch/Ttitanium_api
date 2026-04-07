from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, List
import time

app = FastAPI()

# Banco de dados temporário (em memória)
master_positions: Dict[int, Dict] = {}
status_clientes: Dict[str, Dict] = {}

# Modelos de dados
class PositionUpdate(BaseModel):
    ticket: int
    magic: int
    symbol: str
    type: str
    volume: float
    price: float

class MagicProfit(BaseModel):
    magic: int
    profit: float

class ClientReport(BaseModel):
    client_name: str
    total_profit: float
    profits_per_magic: List[MagicProfit]

# ROTA DO PAINEL (O que você vê no navegador)
@app.get("/")
def dashboard():
    now = time.time()
    painel_formatado = {}
    
    for name, data in status_clientes.items():
        # Se o cliente não enviar dados por 30 segundos, fica Offline
        is_online = "ON" if (now - data["last_seen"] < 30) else "OFF"
        
        painel_formatado[name] = {
            "STATUS": is_online,
            "LUCRO_TOTAL": f"US$ {data['lucro_total']:.2f}",
            "SETUPS_DETALHADOS": data["detalhe_setups"]
        }
    
    return {
        "1_ORDENS_MESTRE_ATIVAS": list(master_positions.values()),
        "2_PAINEL_DE_CLIENTES": painel_formatado,
        "3_TOTAL_CONECTADOS": len(painel_formatado)
    }

# ROTA PARA O MESTRE ENVIAR ORDENS
@app.post("/update-ticket")
async def update_ticket(pos: PositionUpdate):
    master_positions[pos.ticket] = pos.dict()
    return {"status": "sucesso"}

# ROTA PARA QUANDO UMA ORDEM FECHA
@app.delete("/close-ticket/{ticket}")
async def close_ticket(ticket: int):
    if ticket in master_positions:
        del master_positions[ticket]
    return {"status": "removido"}

# ROTA PARA O CLIENTE ENVIAR LUCRO E STATUS
@app.post("/sync-client")
async def sync_client(report: ClientReport):
    status_clientes[report.client_name] = {
        "lucro_total": report.total_profit,
        "detalhe_setups": {f"Setup_{m.magic}": f"{m.profit:.2f}" for m in report.profits_per_magic},
        "last_seen": time.time()
    }
    return list(master_positions.values())
