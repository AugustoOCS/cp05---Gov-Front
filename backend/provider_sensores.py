"""Provider de Sensores (leitura atual e histórico).

Dados SIMULADOS de forma determinística (mesma tag + mesmo instante = mesmo valor).
Para plugar o provider construído em aula, basta reescrever as funções
`leitura_atual` e `historico` mantendo o formato de retorno.
"""
import math
import random
import zlib
from datetime import datetime, timedelta, timezone

INTERVALO_S = 300  # uma leitura a cada 5 minutos

SENSORES = {
    "MTR-001-TEMP": {"descricao": "Temperatura do mancal - Motor 1", "unidade": "°C", "base": 62.0, "amp": 6.0, "alerta": 75.0, "critico": 85.0},
    "MTR-001-VIB": {"descricao": "Vibração RMS - Motor 1", "unidade": "mm/s", "base": 2.5, "amp": 0.8, "alerta": 4.5, "critico": 7.1},
    "MTR-002-TEMP": {"descricao": "Temperatura do mancal - Motor 2", "unidade": "°C", "base": 58.0, "amp": 5.0, "alerta": 75.0, "critico": 85.0},
    "MTR-002-CORR": {"descricao": "Corrente de fase - Motor 2", "unidade": "A", "base": 14.0, "amp": 1.5, "alerta": 18.0, "critico": 22.0},
}


def existe(tag: str) -> bool:
    return tag in SENSORES


def listar_tags() -> list[dict]:
    return [{"tag": t, "descricao": c["descricao"], "unidade": c["unidade"]} for t, c in SENSORES.items()]


def limiares(tag: str) -> dict:
    c = SENSORES[tag]
    return {"alerta": c["alerta"], "critico": c["critico"]}


def severidade(tag: str, valor: float | None) -> str:
    if valor is None:
        return "indisponivel"
    c = SENSORES[tag]
    if valor >= c["critico"]:
        return "critico"
    if valor >= c["alerta"]:
        return "alerta"
    return "normal"


def _valor(tag: str, ts: datetime) -> float | None:
    c = SENSORES[tag]
    bucket = int(ts.timestamp() // INTERVALO_S)
    rng = random.Random(zlib.crc32(tag.encode()) ^ bucket)
    ciclo = math.sin(bucket / 12) * c["amp"]
    ruido = rng.gauss(0, c["amp"] * 0.15)
    pico = c["amp"] * 2.5 if rng.random() < 0.03 else 0.0
    if rng.random() < 0.05:  # ~5% de leituras perdidas (alimenta a métrica de completude)
        return None
    return round(c["base"] + ciclo + ruido + pico, 2)


def leitura_atual(tag: str) -> dict:
    agora = datetime.now(timezone.utc)
    ts = agora - timedelta(seconds=random.randint(0, 90))
    valor = _valor(tag, ts)
    return {
        "tag": tag,
        "valor": valor,
        "unidade": SENSORES[tag]["unidade"],
        "severidade": severidade(tag, valor),
        "timestamp_leitura": ts.isoformat(timespec="seconds"),
    }


def historico(tag: str, limite: int) -> list[dict]:
    agora = datetime.now(timezone.utc)
    base = agora - timedelta(seconds=agora.timestamp() % INTERVALO_S)
    pontos = []
    for i in range(limite - 1, -1, -1):
        ts = base - timedelta(seconds=i * INTERVALO_S)
        v = _valor(tag, ts)
        pontos.append({"timestamp": ts.isoformat(timespec="seconds"), "valor": v, "severidade": severidade(tag, v)})
    return pontos
