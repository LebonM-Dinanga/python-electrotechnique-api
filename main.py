from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import math

app = FastAPI(
    title="Electrotechnique Python API",
    version="1.0.0",
    description="API de calculs pour TFE en électrotechnique"
)

@app.get("/")
def root():
    return {"status": "ok", "message": "API Python électrotechnique active"}

@app.get("/courant-triphasé")
def courant_triphasé(
    puissance_kw: float = Query(..., description="Puissance active en kW"),
    tension_v: float = Query(..., description="Tension ligne-ligne en V"),
    cosphi: float = Query(..., gt=0, le=1, description="Facteur de puissance"),
    rendement: float = Query(..., gt=0, le=1, description="Rendement")
):
    p_w = puissance_kw * 1000
    i_a = p_w / (math.sqrt(3) * tension_v * cosphi * rendement)
    return {
        "formule": "I = P / (√3 × U × cosφ × η)",
        "courant_a": round(i_a, 4),
        "unite": "A"
    }