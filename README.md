# Sensor Monitoring API — Observabilidade de um endpoint de IA

Checkpoint integrado de **Governança em IA** e **Front-end** (Tecnólogo em IA — FIAP), solução Forzy · Digital Twin.
API FastAPI para o provider de Sensores (leitura atual e histórico) que registra metadados de observabilidade a cada
chamada, e uma interface Streamlit que consome a API via `requests`.

## Integrantes

| RM | Nome |
| --- | --- |
| 562080 | Augusto Oliveira |
| 561720 | Felipe Cabral |
| 564705 | Gabriel Tonelli |
| 562163 | Marcelo Maso |
| 565818 | Sofia Bueris |
| 564962 | Vinicius Adrian |

## Arquitetura

```
┌────────────────────┐   requests + headers          ┌──────────────────────────────┐
│ Streamlit          │   X-Session-Id, X-Feature     │ FastAPI                      │
│ frontend/app.py    │ ────────────────────────────▶ │ backend/main.py              │
│ consumo.py (script)│ ◀──────────────────────────── │  ├─ middleware de observab.  │
└────────────────────┘          JSON                 │  ├─ endpoints de sensores    │
                                                     │  └─ GET /v1/observabilidade  │
                                                     └──────────────┬───────────────┘
                                                                    │
                                              backend/provider_sensores.py (dados simulados)
                                              logs/observabilidade.jsonl (registros persistidos)
```

- **Provider** (`backend/provider_sensores.py`): leitura atual e histórico de 4 sensores de motores (dados simulados e
  determinísticos, com ~5% de leituras ausentes). Para usar o provider da aula, reescreva `leitura_atual` e `historico`.
- **Middleware** (`backend/main.py`): para cada chamada registra `timestamp`, `session_id` (header `X-Session-Id`),
  `feature` (header `X-Feature`), método, rota, tag, `status_code`, `latencia_ms`, `freshness_seg`, `completude_pct`
  e `severidade`. Guarda em memória (últimos 5000) e em `logs/observabilidade.jsonl`.
- **Front-end** (`frontend/app.py`): leitura atual, histórico (gráfico com limiares) e relatório de observabilidade.
- **Script** (`consumo.py`): consome os três endpoints via `requests`.

## Endpoints

| Método | Rota | Descrição |
| --- | --- | --- |
| GET | `/v1/sensores` | Lista as tags disponíveis |
| GET | `/v1/sensores/{tag}/leitura-atual` | Valor atual, severidade e limiares |
| GET | `/v1/sensores/{tag}/historico?limite=100` | Série histórica (1 ponto a cada 5 min) |
| GET | `/v1/observabilidade?limite=100&feature=&session_id=` | Resumo agregado + registros de chamadas |

Chamadas a `/v1/observabilidade` não são registradas, para não poluir a evidência. Documentação interativa em `/docs`.

## Como rodar localmente

Requer Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Terminal 1 — API:

```bash
uvicorn backend.main:app --reload --port 8000
```

Terminal 2 — interface:

```bash
streamlit run frontend/app.py
```

Script de consumo (opcional, com a API no ar):

```bash
python consumo.py MTR-001-TEMP
```

A URL da API pode ser trocada pela variável `API_URL` ou no campo da barra lateral do Streamlit.

## Pacotes

`fastapi`, `uvicorn`, `requests`, `streamlit`, `pandas` (ver `requirements.txt`).
