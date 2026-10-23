import pandas as pd
import streamlit as st

from twin.store import TwinStore

st.title("Gemelo Digital - Inspección de calzado")
rows = TwinStore().all()
if not rows:
    st.info("Sin datos todavía. Ejecuta el simulador y el controlador.")
else:
    df = pd.DataFrame(rows)
    c1, c2, c3 = st.columns(3)
    c1.metric("OK", int((df.decision == "OK").sum()))
    c2.metric("Rechazo", int((df.decision == "RECHAZO").sum()))
    c3.metric("Latencia media (ms)", f"{df.latencia_ms.mean():.1f}")
    st.dataframe(df.tail(50))
