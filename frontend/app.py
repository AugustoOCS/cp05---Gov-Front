"""Interface Streamlit - Sensor Monitoring (consome a API via requests)."""
import os
import uuid

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Sensor Monitoring", page_icon="📡", layout="wide")

if "session_id" not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex[:8]

ICONES = {"normal": "🟢", "alerta": "🟡", "critico": "🔴", "indisponivel": "⚪"}

# ---------- Sidebar ----------
st.sidebar.title("📡 Sensor Monitoring")
api_url = st.sidebar.text_input("URL da API", os.getenv("API_URL", "http://localhost:8000"))
st.sidebar.caption(f"Session ID: `{st.session_state.session_id}`")
secao = st.sidebar.radio("Seção", ["Leitura atual", "Histórico", "Observabilidade"])
st.sidebar.button("🔄 Atualizar")


def chamar(caminho: str, feature: str, params: dict | None = None):
    """GET na API enviando os headers de contexto exigidos pela Governança."""
    headers = {"X-Session-Id": st.session_state.session_id, "X-Feature": feature}
    try:
        r = requests.get(f"{api_url}{caminho}", headers=headers, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        st.error(f"Falha ao chamar {caminho}: {e}")
        return None


# Lista de sensores (carregada uma única vez por sessão)
if "sensores" not in st.session_state:
    st.session_state.sensores = chamar("/v1/sensores", "lista-sensores")
sensores = st.session_state.sensores
if not sensores:
    st.warning("Não foi possível carregar os sensores. Verifique se a API está no ar.")
    st.stop()

# ---------- Leitura atual ----------
if secao == "Leitura atual":
    st.header("Leitura atual")
    tag = st.selectbox("Sensor", [s["tag"] for s in sensores], key="tag_leitura")
    dado = chamar(f"/v1/sensores/{tag}/leitura-atual", "leitura-atual")
    if dado:
        c1, c2, c3 = st.columns(3)
        valor = "—" if dado["valor"] is None else f'{dado["valor"]} {dado["unidade"]}'
        c1.metric("Valor", valor)
        c2.metric("Severidade", f'{ICONES[dado["severidade"]]} {dado["severidade"]}')
        c3.metric("Leitura em (UTC)", dado["timestamp_leitura"].replace("T", " ")[:19])
        lim = dado["limiares"]
        st.caption(f'Limiares: alerta ≥ {lim["alerta"]} {dado["unidade"]} · crítico ≥ {lim["critico"]} {dado["unidade"]}')

# ---------- Histórico ----------
elif secao == "Histórico":
    st.header("Histórico")
    col1, col2 = st.columns([2, 1])
    tag = col1.selectbox("Sensor", [s["tag"] for s in sensores], key="tag_hist")
    limite = col2.slider("Pontos (1 a cada 5 min)", 12, 500, 100)
    dado = chamar(f"/v1/sensores/{tag}/historico", "historico", {"limite": limite})
    if dado:
        df = pd.DataFrame(dado["pontos"])
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["alerta"] = dado["limiares"]["alerta"]
        df["crítico"] = dado["limiares"]["critico"]
        faltantes = int(df["valor"].isna().sum())
        c1, c2, c3 = st.columns(3)
        c1.metric("Pontos", dado["total_pontos"])
        c2.metric("Leituras ausentes", faltantes)
        c3.metric("Em alerta/crítico", int(df["severidade"].isin(["alerta", "critico"]).sum()))
        st.line_chart(df.set_index("timestamp")[["valor", "alerta", "crítico"]], y_label=dado["unidade"])
        with st.expander("Ver tabela"):
            st.dataframe(df[["timestamp", "valor", "severidade"]].iloc[::-1], width="stretch", hide_index=True)

# ---------- Observabilidade ----------
else:
    st.header("Relatório de observabilidade")
    col1, col2 = st.columns(2)
    limite = col1.slider("Registros", 10, 1000, 200)
    so_minha = col2.checkbox("Apenas minha sessão", value=False)
    params = {"limite": limite}
    if so_minha:
        params["session_id"] = st.session_state.session_id
    dado = chamar("/v1/observabilidade", "observabilidade-ui", params)
    if dado:
        r = dado["resumo"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Chamadas", r["total_chamadas"])
        c2.metric("Latência média", f'{r["latencia_media_ms"]} ms')
        c3.metric("Latência p95", f'{r["latencia_p95_ms"]} ms')
        c4.metric("Taxa de erro", f'{r["taxa_erro_pct"]}%')
        c5, c6 = st.columns(2)
        c5.metric("Freshness médio", "—" if r["freshness_medio_seg"] is None else f'{r["freshness_medio_seg"]} s')
        c6.metric("Completude média", "—" if r["completude_media_pct"] is None else f'{r["completude_media_pct"]}%')

        if dado["registros"]:
            df = pd.DataFrame(dado["registros"])
            g1, g2 = st.columns(2)
            g1.subheader("Latência por chamada (ms)")
            g1.line_chart(df.sort_values("id").set_index("id")["latencia_ms"])
            g2.subheader("Chamadas por feature")
            g2.bar_chart(pd.Series(r["por_feature"], name="chamadas"))
            st.subheader("Registros")
            st.dataframe(df, width="stretch", hide_index=True)
        else:
            st.info("Ainda não há registros. Use as outras seções para gerar chamadas.")
