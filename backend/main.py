"""API FastAPI - Sensor Monitoring (checkpoint Governança em IA + Front-end).

Cada chamada gera um registro de observabilidade com: headers de contexto
(X-Session-Id, X-Feature), timestamp, latência, status e metadados do dado
entregue (freshness e completude).
"""
import asyncio
import itertools
import math
import json
import random
import statistics
import time
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request

from backend import provider_sensores as provider

app = FastAPI(title="Sensor Monitoring API", version="1.0.0")

REGISTROS: deque = deque(maxlen=5000)
_ids = itertools.count(1)
LOG_FILE = Path("logs/observabilidade.jsonl")
LOG_FILE.parent.mkdir(exist_ok=True)
IGNORAR = ("/v1/observabilidade", "/docs", "/openapi.json", "/redoc")


@app.middleware("http")
async def registrar_chamada(request: Request, call_next):
    if request.url.path.startswith(IGNORAR):
        return await call_next(request)

    request.state.obs = {}  # os endpoints preenchem tag, freshness, completude...
    inicio = time.perf_counter()
    response = await call_next(request)
    latencia_ms = (time.perf_counter() - inicio) * 1000

    obs = request.state.obs
    registro = {
        "id": next(_ids),
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "session_id": request.headers.get("X-Session-Id", "sem-sessao"),
        "feature": request.headers.get("X-Feature", "nao-informada"),
        "metodo": request.method,
        "rota": request.url.path,
        "tag": obs.get("tag"),
        "status_code": response.status_code,
        "latencia_ms": round(latencia_ms, 2),
        "freshness_seg": obs.get("freshness_seg"),
        "completude_pct": obs.get("completude_pct"),
        "severidade": obs.get("severidade"),
    }
    REGISTROS.append(registro)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    return response


async def _simular_io():
    # Simula o tempo de acesso à fonte do sensor (20-120 ms)
    await asyncio.sleep(random.uniform(0.02, 0.12))


def _checar_tag(request: Request, tag: str):
    request.state.obs["tag"] = tag
    if not provider.existe(tag):
        raise HTTPException(status_code=404, detail=f"Sensor '{tag}' não encontrado")


@app.get("/v1/sensores")
async def listar_sensores(request: Request):
    return provider.listar_tags()


@app.get("/v1/sensores/{tag}/leitura-atual")
async def leitura_atual(tag: str, request: Request):
    _checar_tag(request, tag)
    await _simular_io()
    dado = provider.leitura_atual(tag)
    ts = datetime.fromisoformat(dado["timestamp_leitura"])
    request.state.obs.update(
        freshness_seg=round((datetime.now(timezone.utc) - ts).total_seconds(), 1),
        completude_pct=0.0 if dado["valor"] is None else 100.0,
        severidade=dado["severidade"],
    )
    return {**dado, "limiares": provider.limiares(tag)}


@app.get("/v1/sensores/{tag}/historico")
async def historico(tag: str, request: Request, limite: int = Query(100, ge=1, le=1000)):
    _checar_tag(request, tag)
    await _simular_io()
    pontos = provider.historico(tag, limite)
    validos = [p for p in pontos if p["valor"] is not None]
    ultimo = datetime.fromisoformat(pontos[-1]["timestamp"])
    request.state.obs.update(
        freshness_seg=round((datetime.now(timezone.utc) - ultimo).total_seconds(), 1),
        completude_pct=round(100 * len(validos) / len(pontos), 1),
        severidade=pontos[-1]["severidade"],
    )
    return {
        "tag": tag,
        "unidade": provider.SENSORES[tag]["unidade"],
        "limiares": provider.limiares(tag),
        "total_pontos": len(pontos),
        "pontos": pontos,
    }


def _p95(valores: list[float]) -> float:
    return sorted(valores)[math.ceil(0.95 * len(valores)) - 1] if valores else 0.0


@app.get("/v1/observabilidade")
async def observabilidade(
    limite: int = Query(100, ge=1, le=5000),
    feature: str | None = None,
    session_id: str | None = None,
):
    regs = [r for r in REGISTROS if (not feature or r["feature"] == feature) and (not session_id or r["session_id"] == session_id)]
    lat = [r["latencia_ms"] for r in regs]
    fresh = [r["freshness_seg"] for r in regs if r["freshness_seg"] is not None]
    comp = [r["completude_pct"] for r in regs if r["completude_pct"] is not None]
    erros = [r for r in regs if r["status_code"] >= 400]
    resumo = {
        "total_chamadas": len(regs),
        "taxa_erro_pct": round(100 * len(erros) / len(regs), 1) if regs else 0.0,
        "latencia_media_ms": round(statistics.mean(lat), 2) if lat else 0.0,
        "latencia_p95_ms": round(_p95(lat), 2),
        "freshness_medio_seg": round(statistics.mean(fresh), 1) if fresh else None,
        "completude_media_pct": round(statistics.mean(comp), 1) if comp else None,
        "por_feature": dict(Counter(r["feature"] for r in regs)),
        "por_status": dict(Counter(str(r["status_code"]) for r in regs)),
    }
    return {"resumo": resumo, "registros": list(reversed(regs))[:limite]}
