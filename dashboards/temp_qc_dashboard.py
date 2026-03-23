import streamlit as st
import os
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.title("AWS QC Dashboard – Temperatuur (Raw Value)")

# 📁 Detecteer stations
data_path = "data/processed"
stations = [d for d in os.listdir(data_path) if os.path.isdir(os.path.join(data_path, d))]

station = st.selectbox("Kies een station", stations)

# 📄 Automatisch temperatuur-bestand kiezen
station_path = os.path.join(data_path, station)
temp_file = "Air_Temperaturedeg_C_QC.xlsx"
file_path = os.path.join(station_path, temp_file)

df = pd.read_excel(file_path)

# Combineer Dag + Tijd
df['Timestamp'] = pd.to_datetime(df['Dag'].astype(str) + ' ' + df['Tijd'].astype(str))
df = df.sort_values('Timestamp')

# 📅 Dagselectie
alle_dagen = sorted(df['Timestamp'].dt.date.unique())
gekozen_dag = st.selectbox("Kies een dag", alle_dagen)

df_dag = df[df['Timestamp'].dt.date == gekozen_dag]

st.subheader(f"QC Rapport – {gekozen_dag}")

# -----------------------------
# 1. CUSTOM BLOCKS TIMELINE
# -----------------------------
st.subheader("Ontbrekende metingen voor de dag!")

df["Raw Value"] = pd.to_numeric(df["Raw Value"], errors="coerce")
df_dag = df[df['Timestamp'].dt.date == gekozen_dag].copy()

start = pd.to_datetime(str(gekozen_dag) + " 00:00:00")
expected_times = pd.date_range(start=start, periods=144, freq="10min")

df_expected = pd.DataFrame({"Timestamp": expected_times})

df_expected = df_expected.merge(
    df_dag[["Timestamp", "Raw Value"]],
    on="Timestamp",
    how="left"
)

df_expected["Status"] = df_expected["Raw Value"].notna()
df_expected["Hour"] = df_expected["Timestamp"].dt.hour
df_expected["Block"] = df_expected["Timestamp"].dt.minute // 10

cell_size = 30
gap = 5
rows = 6
cols = 24

fig = go.Figure()

for _, row in df_expected.iterrows():
    hour = row["Hour"]
    block = row["Block"]
    status = row["Status"]

    color = "green" if status else "red"

    x = hour * (cell_size + gap)
    y = (5 - block) * (cell_size + gap)

    fig.add_shape(
        type="rect",
        x0=x, x1=x + cell_size,
        y0=y, y1=y + cell_size,
        line=dict(width=0),
        fillcolor=color
    )

fig.update_xaxes(
    title_text="<b>Uur van de dag</b>",
    title_font=dict(size=16),
    tickfont=dict(size=14, color="black"),
    range=[0, cols * (cell_size + gap)],
    tickmode="array",
    tickvals=[h * (cell_size + gap) + cell_size/2 for h in range(cols)],
    ticktext=[f"<b>{h:02d}:00</b>" for h in range(cols)],
    showgrid=False,
    zeroline=False
)

fig.update_yaxes(
    title_text="<b>10-minuten blok</b>",
    title_font=dict(size=16),
    tickfont=dict(size=14, color="black"),
    range=[0, rows * (cell_size + gap)],
    tickmode="array",
    tickvals=[i * (cell_size + gap) + cell_size/2 for i in range(rows)],
    ticktext=[f"<b>{t}</b>" for t in ["00", "10", "20", "30", "40", "50"]],
    showgrid=False,
    zeroline=False
)

fig.update_layout(
    width=cols * (cell_size + gap) + 200,
    height=rows * (cell_size + gap) + 200,
    margin=dict(l=80, r=40, t=60, b=80),
    plot_bgcolor="white"
)

st.plotly_chart(fig, use_container_width=True)

st.markdown("**Legenda:** 🟩 Ontvangen meting   |   🟥 Ontbrekende meting")

# -----------------------------
# 2. QC SAMENVATTING
# -----------------------------
st.subheader("QC")

totaal_blokken = 144
aanwezig = df_expected["Status"].sum()
ontbrekend = totaal_blokken - aanwezig
percentage = round((aanwezig / totaal_blokken) * 100, 1)

kwaliteit = (
    "Voldoende — dag voldoet aan de minimale eis."
    if percentage >= 75
    else "Onvoldoende — minder dan 75% datacompleetheid."
)

qc_html = f"""
<div style="
    background-color:#f0f2f6;
    padding:18px;
    border-radius:10px;
    border-left:6px solid #4a90e2;
    font-size:16px;
">
<p>De temperatuur wordt elke 10 minuten gemeten en geregistreerd.</p>
<p>In totaal moeten er <b>144 metingen</b> zijn per dag.</p>
<p><b>Ontbrekende metingen:</b> {ontbrekend} van de 144.</p>
<p><b>Datacompleetheid:</b> {percentage}%.</p>
<p><b>Kwaliteit:</b> {kwaliteit}</p>
<p>Minimaal <b>75%</b> van de datametingen moet aanwezig zijn om te voldoen aan de kwaliteitsnorm.</p>
</div>
"""

st.markdown(qc_html, unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. MAANDOVERZICHT QC – TEMPERATUUR
# ---------------------------------------------------------

st.subheader("Maandelijkse QC – Temperatuur")

alle_dagen = sorted(df['Timestamp'].dt.date.unique())
qc_resultaten = []

for dag in alle_dagen:
    df_dag = df[df['Timestamp'].dt.date == dag].copy()
    df_dag["Raw Value"] = pd.to_numeric(df_dag["Raw Value"], errors="coerce")
    aanwezig = df_dag["Raw Value"].notna().sum()
    percentage = round((aanwezig / 144) * 100, 1)
    status = "goed" if percentage >= 75 else "slecht"

    qc_resultaten.append({
        "Dag": dag,
        "Aanwezig": aanwezig,
        "Percentage": percentage,
        "Status": status
    })

qc_df = pd.DataFrame(qc_resultaten)

fig2 = go.Figure()

cell_size = 40
gap = 10

for i, row in qc_df.iterrows():
    kleur = "green" if row["Status"] == "goed" else "red"

    x0 = i * (cell_size + gap)
    x1 = x0 + cell_size

    fig2.add_shape(
        type="rect",
        x0=x0, x1=x1,
        y0=0, y1=cell_size,
        line=dict(width=0),
        fillcolor=kleur
    )

    fig2.add_annotation(
        x=x0 + cell_size/2,
        y=cell_size/2,
        text=str(row["Dag"].day),
        showarrow=False,
        font=dict(color="white", size=14)
    )

fig2.update_xaxes(visible=False)
fig2.update_yaxes(visible=False)
fig2.update_layout(height=150, plot_bgcolor="white")

st.plotly_chart(fig2, use_container_width=True)

st.markdown("**Legenda:** 🟩 Geschikte dag (≥75% compleet)   |   🟥 Ongeschikte dag (<75% compleet)")

eerste_dag = alle_dagen[0]
maand = eerste_dag.month
jaar = eerste_dag.year

dagen_per_maand = {
    1: 31, 2: 29 if (jaar % 4 == 0 and (jaar % 100 != 0 or jaar % 400 == 0)) else 28,
    3: 31, 4: 30, 5: 31, 6: 30,
    7: 31, 8: 31, 9: 30, 10: 31,
    11: 30, 12: 31
}

totaal_dagen_in_maand = dagen_per_maand[maand]
dagen_met_data = len(alle_dagen)
ontbrekende_dagen = totaal_dagen_in_maand - dagen_met_data
