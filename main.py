from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, List
import time

app = FastAPI()

# Banco de dados na memória
# master_positions: { "TICKET_123": {"magic": 101, "type": "BUY", "vol": 1.0, "price": 125000}, ... }
master_positions: Dict[int, Dict] = {}
status_clientes: Dict[str, Dict] = {}

class PositionUpdate(BaseModel):
    ticket: int
    magic: int
    symbol: str
    type: str # BUY ou SELL
    volume: float
    price: float

class ClientReport(BaseModel):
    client_id: str
    profit: float

@app.get("/")
def dashboard():
    return {
        "posicoes_mestre_ativas": list(master_positions.values()),
        "clientes_online": status_clientes,
        "contagem": len(status_clientes)
    }

# O MESTRE ENVIA CADA TICKET INDIVIDUALMENTE
@app.post("/update-ticket")
async def update_ticket(pos: PositionUpdate):
    master_positions[pos.ticket] = pos.dict()
    return {"status": "Ticket Atualizado", "ticket": pos.ticket}

# O MESTRE AVISA QUANDO UM TICKET FECHA
@app.delete("/close-ticket/{ticket}")
async def close_ticket(ticket: int):
    if ticket in master_positions:
        del master_positions[ticket]
    return {"status": "Ticket Removido"}

# O CLIENTE SINCRONIZA TUDO
@app.post("/sync-client")
async def sync_client(report: ClientReport):
    status_clientes[report.client_id] = {
        "lucro": report.profit,
        "last_seen": time.time()
    }
    return list(master_positions.values())
