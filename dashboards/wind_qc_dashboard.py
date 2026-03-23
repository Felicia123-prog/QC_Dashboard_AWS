import streamlit as st
import os
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.title("AWS QC Dashboard – Windrichting (Raw Value)")

# 📁 Detecteer stations
data_path = "data/processed"
stations = [d for d in os.listdir(data_path) if os.path.isdir(os.path.join(data_path, d))]

station = st.selectbox("Kies een station", stations)

# 📄 Automatisch windrichting-bestand kiezen
station_path = os.path.join(data_path, station)
wind_file = "Wind_Dir_Averagedeg_QC.xlsx"
file_path = os.path.join(station_path, wind_file)

df = pd.read_excel(file_path)

# ---------------------------------------------------------
# ⭐ 1. Kolomnamen opschonen
# ---------------------------------------------------------
df.columns = df.columns.str.strip()

# ---------------------------------------------------------
# ⭐ 2. Tijd fixen (DIT IS DE BELANGRIJKSTE FIX)
# ---------------------------------------------------------
df["Dag"] = df["Dag"].astype(str).str.strip()
df["Tijd"] = df["Tijd"].astype(str).str.strip().str.slice(-8)

# ---------------------------------------------------------
# ⭐ 3. Timestamp bouwen (nu 100% correct)
# ---------------------------------------------------------
df["Timestamp"] = pd.to_datetime(df["Dag"] + " " + df["Tijd"], errors="coerce")
df = df.sort_values("Timestamp")

# ---------------------------------------------------------
# ⭐ 4. Raw Value fix
# ---------------------------------------------------------
df["Raw Value"] = pd.to_numeric(df["Raw Value"], errors="coerce")
df["Cleaned Value"] = pd.to_numeric(df["Cleaned Value"], errors="coerce")
df["Raw Value"] = df["Raw Value"].fillna(df["Cleaned Value"])

# 📅 Dagselectie
alle_dagen = sorted(df["Timestamp"].dt.date.unique())
gekozen_dag = st.selectbox("Kies een dag", alle_dagen)

df_dag = df[df["Timestamp"].dt.date == gekozen_dag]

st.subheader(f"QC Rapport – {gekozen_dag}")

# ---------------------------------------------------------
# ⭐ 5. MISSING BLOCKS – IDENTIEK AAN TEMPERATUUR
# ---------------------------------------------------------
st.subheader("Ontbrekende metingen voor de dag!")

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
    tickmode="array",
    tickvals=[h * (cell_size + gap) + cell_size/2 for h in range(cols)],
    ticktext=[f"{h:02d}:00" for h in range(cols)],
    showgrid=False,
    zeroline=False
)

fig.update_yaxes(
    title_text="<b>10-minuten blok</b>",
    tickmode="array",
    tickvals=[i * (cell_size + gap) + cell_size/2 for i in range(rows)],
    ticktext=["00", "10", "20", "30", "40", "50"],
    showgrid=False,
    zeroline=False
)

fig.update_layout(
    width=cols * (cell_size + gap) + 200,
    height=rows * (cell_size + gap) + 200,
    plot_bgcolor="white"
)

st.plotly_chart(fig, use_container_width=True)

st.markdown("**Legenda:** 🟩 Ontvangen meting   |   🟥 Ontbrekende meting**")

# ---------------------------------------------------------
# ⭐ 6. QC SAMENVATTING – DAG
# ---------------------------------------------------------
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
">
<p>Windrichting wordt elke 10 minuten gemeten.</p>
<p><b>Ontbrekende metingen:</b> {ontbrekend} van 144</p>
<p><b>Datacompleetheid:</b> {percentage}%</p>
<p><b>Kwaliteit:</b> {kwaliteit}</p>
</div>
"""

st.markdown(qc_html, unsafe_allow_html=True)

# ---------------------------------------------------------
# ⭐ 7. MAANDOVERZICHT QC
# ---------------------------------------------------------
st.subheader("Maandelijkse QC – Windrichting")

qc_resultaten = []

for dag in alle_dagen:
    df_dag = df[df["Timestamp"].dt.date == dag].copy()
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
        fillcolor=kleur,
        line=dict(width=0)
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

st.markdown("**Legenda:** 🟩 Geschikte dag   |   🟥 Ongeschikte dag**")

# ---------------------------------------------------------
# ⭐ 8. GEREGISTREERDE METINGEN & QC
# ---------------------------------------------------------
st.subheader("Geregistreerde Windrichtingmetingen & Datakwaliteit")

df_dag = df[df["Timestamp"].dt.date == gekozen_dag].copy()
df_dag = df_dag[df_dag["Raw Value"].notna()]

if df_dag.empty:
    st.warning("Geen windrichtingmetingen beschikbaar.")
    st.stop()

df_dag = df_dag.sort_values("Timestamp")
df_dag["Raw Value"] = df_dag["Raw Value"].round(0).astype("Int64")

# QC regels
df_dag["QC_Flag"] = "OK"
df_dag.loc[(df_dag["Raw Value"] < 0) | (df_dag["Raw Value"] > 360), "QC_Flag"] = "OUT_OF_RANGE"

# Tabel
def highlight_qc(val):
    return "background-color: #ff8a80" if val == "OUT_OF_RANGE" else "background-color: #b6f2b6"

st.dataframe(
    df_dag[["Timestamp", "Raw Value", "QC_Flag"]]
    .style
    .applymap(highlight_qc, subset=["QC_Flag"])
)

st.markdown("""
### Legenda
- 🟩 **OK** — Geldige windrichting (0–360°)
- 🟥 **OUT_OF_RANGE** — Ongeldige waarde
""")

# ---------------------------------------------------------
# ⭐ 9. WINDROOS – DAG
# ---------------------------------------------------------
st.subheader("Windroos – Dag")

df_dag["Sector"] = (df_dag["Raw Value"] // 10) * 10
freq = df_dag.groupby("Sector").size().reset_index(name="Count")

max_count = freq["Count"].max()
freq["Color"] = freq["Count"] / max_count

fig_w = go.Figure()

fig_w.add_trace(go.Barpolar(
    r=freq["Count"] * 1.4,
    theta=freq["Sector"],
    marker=dict(
        color=freq["Color"],
        colorscale="Blues",
        cmin=0,
        cmax=1
    ),
    opacity=0.95
))

fig_w.update_layout(
    polar=dict(
        angularaxis=dict(direction="clockwise", rotation=90),
        radialaxis=dict(range=[0, max_count * 2])
    ),
    showlegend=False
)

st.plotly_chart(fig_w, use_container_width=True)

# ---------------------------------------------------------
# ⭐ 10. DAGCONCLUSIE
# ---------------------------------------------------------
outliers = (df_dag["QC_Flag"] == "OUT_OF_RANGE").sum()

if outliers > 0:
    st.markdown("### Dagconclusie\n❌ Ongeldige windrichtingwaarden aanwezig.")
else:
    st.markdown("### Dagconclusie\n✔️ Alle waarden geldig.")

# ---------------------------------------------------------
# ⭐ 11. MAANDSTATISTIEKEN
# ---------------------------------------------------------
st.subheader("Maandstatistieken – Windrichting")

df_maand = df[df["Timestamp"].dt.month == gekozen_dag.month].copy()
df_maand = df_maand[df_maand["Raw Value"].notna()]

ongeldig = ((df_maand["Raw Value"] < 0) | (df_maand["Raw Value"] > 360)).sum()
totaal = len(df_maand)
percentage_ongeldig = (ongeldig / totaal) * 100 if totaal > 0 else 0

st.markdown(f"""
- **Aantal ongeldige waarden:** {ongeldig}
- **Percentage ongeldige waarden:** {percentage_ongeldig:.1f}%
""")

if percentage_ongeldig >= 50:
    st.markdown("### Maandconclusie\n❌ Meer dan 50% ongeldig — data ongeschikt.")
elif percentage_ongeldig > 0:
    st.markdown("### Maandconclusie\n⚠️ Enkele ongeldige waarden — filteren aanbevolen.")
else:
    st.markdown("### Maandconclusie\n✔️ Alle waarden geldig.")

# ---------------------------------------------------------
# ⭐ 12. WINDROOS – MAAND
# ---------------------------------------------------------
st.subheader("Maandelijkse Windroos")

df_valid = df_maand[df_maand["Raw Value"].between(0, 360)]

if df_valid.empty:
    st.info("Geen geldige windrichtingwaarden voor deze maand.")
else:
    df_valid["Sector"] = (df_valid["Raw Value"] // 10) * 10
    freq_m = df_valid.groupby("Sector").size().reset_index(name="Count")

    max_count_m = freq_m["Count"].max()
    freq_m["Color"] = freq_m["Count"] / max_count_m

    fig_m = go.Figure()

    fig_m.add_trace(go.Barpolar(
        r=freq_m["Count"] * 1.4,
        theta=freq_m["Sector"],
        marker=dict(
            color=freq_m["Color"],
            colorscale="Blues",
            cmin=0,
            cmax=1
        ),
        opacity=0.95
    ))

    fig_m.update_layout(
        polar=dict(
            angularaxis=dict(direction="clockwise", rotation=90),
            radialaxis=dict(range=[0, max_count_m * 2])
        ),
        showlegend=False
    )

    st.plotly_chart(fig_m, use_container_width=True)
