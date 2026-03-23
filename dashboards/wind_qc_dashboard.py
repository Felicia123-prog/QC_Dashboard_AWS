import streamlit as st
import os
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import plotly.express as px

st.title("AWS QC Dashboard – Windrichting (Raw Value)")

# 📁 Detecteer stations
data_path = "data"
stations = [d for d in os.listdir(data_path) if os.path.isdir(os.path.join(data_path, d))]

station = st.selectbox("Kies een station", stations)

# 📄 Automatisch windrichting-bestand kiezen
station_path = os.path.join(data_path, station)
wind_file = "Wind_Dir_Averagedeg_QC.xlsx"
file_path = os.path.join(station_path, wind_file)

df = pd.read_excel(file_path)

# Combineer Dag + Tijd (één keer!)
df["Timestamp"] = pd.to_datetime(df["Dag"].astype(str) + " " + df["Tijd"].astype(str))
df = df.sort_values("Timestamp")

# 📅 Dagselectie
alle_dagen = sorted(df["Timestamp"].dt.date.unique())
gekozen_dag = st.selectbox("Kies een dag", alle_dagen)

df_dag = df[df["Timestamp"].dt.date == gekozen_dag]

st.subheader(f"QC Rapport – {gekozen_dag}")

# ---------------------------------------------------------
# 1. CUSTOM BLOCKS TIMELINE – MISSING DETECTIE
# ---------------------------------------------------------
st.subheader("Ontbrekende metingen voor de dag!")

df["Raw Value"] = pd.to_numeric(df["Raw Value"], errors="coerce")

df_dag = df[df["Timestamp"].dt.date == gekozen_dag].copy()

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

st.markdown("**Legenda:** 🟩 Ontvangen meting   |   🟥 Ontbrekende meting**")

# ---------------------------------------------------------
# 2. QC SAMENVATTING – DAG
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
    font-size:16px;
">
<p>Windrichting wordt elke 10 minuten gemeten en geregistreerd.</p>
<p>In totaal moeten er <b>144 metingen</b> zijn per dag.</p>
<p><b>Ontbrekende metingen:</b> {ontbrekend} van de 144.</p>
<p><b>Datacompleetheid:</b> {percentage}%.</p>
<p><b>Kwaliteit:</b> {kwaliteit}</p>
<p>Minimaal <b>75%</b> van de datametingen moet aanwezig zijn om te voldoen aan de kwaliteitsnorm.</p>
</div>
"""

st.markdown(qc_html, unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. MAANDOVERZICHT QC
# ---------------------------------------------------------
st.subheader("Maandelijkse QC – Windrichting")

qc_resultaten = []

for dag in alle_dagen:
    df_dag_m = df[df["Timestamp"].dt.date == dag].copy()
    df_dag_m["Raw Value"] = pd.to_numeric(df_dag_m["Raw Value"], errors="coerce")
    aanwezig_m = df_dag_m["Raw Value"].notna().sum()
    totaal_m = 144
    percentage_m = round((aanwezig_m / totaal_m) * 100, 1)
    status_m = "goed" if percentage_m >= 75 else "slecht"

    qc_resultaten.append({
        "Dag": dag,
        "Aanwezig": aanwezig_m,
        "Percentage": percentage_m,
        "Status": status_m
    })

qc_df = pd.DataFrame(qc_resultaten)

# ---------------------------------------------------------
# 4. GRAFIEK MAANDOVERZICHT
# ---------------------------------------------------------
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

fig2.update_xaxes(visible=False, range=[0, len(qc_df) * (cell_size + gap)])
fig2.update_yaxes(visible=False, range=[0, cell_size])
fig2.update_layout(height=150, margin=dict(l=20, r=20, t=20, b=20), plot_bgcolor="white")

st.plotly_chart(fig2, use_container_width=True)

st.markdown("**Legenda:** 🟩 Geschikte dag (≥75% compleet)   |   🟥 Ongeschikte dag (<75% compleet)**")

# ---------------------------------------------------------
# 5. GEREGISTREERDE METINGEN & QC
# ---------------------------------------------------------
st.subheader("Geregistreerde Windrichtingmetingen & Datakwaliteit")

# GEEN nieuwe Timestamp-opbouw hier!
df["Raw Value"] = pd.to_numeric(df["Raw Value"], errors="coerce")

df_dag = df[df["Timestamp"].dt.date == gekozen_dag].copy()
df_dag = df_dag[df_dag["Raw Value"].notna()]

if df_dag.empty:
    st.warning(f"Er zijn geen windrichtingmetingen beschikbaar voor {gekozen_dag}.")
    st.stop()

df_dag = df_dag.sort_values("Timestamp")

# ---------------------------------------------------------
# 6. QC REGELS – WINDRICHTING (0–360°)
# ---------------------------------------------------------
df_dag["QC_Flag"] = "OK"
df_dag.loc[(df_dag["Raw Value"] < 0) | (df_dag["Raw Value"] > 360), "QC_Flag"] = "OUT_OF_RANGE"

# ---------------------------------------------------------
# 7. TABEL MET KLEUREN + AFRONDING
# ---------------------------------------------------------
df_dag["Raw Value"] = df_dag["Raw Value"].round(0).astype("Int64")

def highlight_qc(val):
    colors = {
        "OK": "background-color: #b6f2b6",
        "OUT_OF_RANGE": "background-color: #ff8a80"
    }
    return colors.get(val, "")

st.write(f"Windrichtingmetingen op {gekozen_dag}:")
st.dataframe(
    df_dag[["Timestamp", "Raw Value", "QC_Flag"]]
    .style
    .applymap(highlight_qc, subset=["QC_Flag"])
    .format({"Raw Value": "{:.0f}"})
)

st.markdown("""
### Legenda datakwaliteit
- 🟩 **OK** — Geldige windrichting (0–360°)  
- 🟥 **OUT_OF_RANGE** — Ongeldige waarde (buiten 0–360°)  
""")

# ---------------------------------------------------------
# 8. PREMIUM WINDROOS – DAG (ZONDER DOMINANTE PIJL)
# ---------------------------------------------------------
df_dag["Raw Value"] = df_dag["Raw Value"].round(0).astype("Int64")

df_dag["Sector"] = (df_dag["Raw Value"] // 10) * 10
freq_dag = df_dag.groupby("Sector").size().reset_index(name="Count")

max_count_dag = freq_dag["Count"].max()
freq_dag["Color"] = freq_dag["Count"] / max_count_dag

fig_d = go.Figure()

fig_d.add_trace(go.Barpolar(
    r=freq_dag["Count"] * 1.4,
    theta=freq_dag["Sector"],
    marker=dict(
        color=freq_dag["Color"],
        colorscale="Blues",
        cmin=0,
        cmax=1
    ),
    opacity=0.95,
    name="Frequentie"
))

cardinal_angles = [0, 45, 90, 135, 180, 225, 270, 315]
cardinal_labels = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

for angle, label in zip(cardinal_angles, cardinal_labels):
    fig_d.add_trace(go.Scatterpolar(
        r=[max_count_dag * 1.8],
        theta=[angle],
        mode="text",
        text=[label],
        textfont=dict(size=14, color="black"),
        showlegend=False
    ))

fig_d.update_layout(
    title=f"Windroos – {gekozen_dag}",
    polar=dict(
        radialaxis=dict(showticklabels=True, ticks='outside', range=[0, max_count_dag * 2]),
        angularaxis=dict(direction="clockwise", rotation=90)
    ),
    showlegend=True
)

st.plotly_chart(fig_d, use_container_width=True)

st.markdown("""
### Uitleg Windroos
De windroos toont **hoe vaak** de wind uit elke richting heeft gewaaid.

- **Blauwe balken**: geven de **frequentie** weer.  
  - Hoe **langer** de balk, hoe **vaker** de wind uit die richting kwam.  
  - Hoe **donkerder** de kleur, hoe **hoger** de frequentie.

- De cirkel is verdeeld in **sectoren van 10°** (0°, 10°, 20°, … 350°).

- De labels **N, NE, E, SE, S, SW, W, NW** geven de **windrichtingen** aan.

- De windroos gebruikt **alle individuele metingen** van de dag.  
  Er wordt **geen gemiddelde windrichting** berekend, omdat dat meteorologisch niet correct is.
""")

st.markdown(f"""
### Dagelijkse Windrichting Samenvatting
- **Hoogste frequentie:** {max_count_dag} metingen  
- **Aantal sectoren met wind:** {freq_dag[freq_dag['Count'] > 0].shape[0]}  
""")

# ---------------------------------------------------------
# 9. QC SAMENVATTING – DAG
# ---------------------------------------------------------
laagste = df_dag["Raw Value"].min()
hoogste = df_dag["Raw Value"].max()
qc_counts = df_dag["QC_Flag"].value_counts()

st.markdown(f"""
### Samenvatting datakwaliteit
- **Laagste waarde:** {laagste}°  
- **Hoogste waarde:** {hoogste}°  
- **Aantal OUT_OF_RANGE:** {qc_counts.get('OUT_OF_RANGE', 0)}  
""")

if qc_counts.get("OUT_OF_RANGE", 0) > 0:
    conclusie = "❌ De dag bevat ongeldige windrichtingwaarden (buiten 0–360°)."
else:
    conclusie = "✔️ Alle waarden vallen binnen het geldige bereik."

st.markdown(f"### Dagconclusie\n{conclusie}")

# ---------------------------------------------------------
# 10. MAANDSTATISTIEKEN – WINDRICHTING
# ---------------------------------------------------------
maand = gekozen_dag.month
jaar = gekozen_dag.year

df_maand = df[
    (df["Timestamp"].dt.month == maand) &
    (df["Timestamp"].dt.year == jaar)
].copy()

df_maand = df_maand[df_maand["Raw Value"].notna()]

if not df_maand.empty:

    totaal_waarden = len(df_maand)
    fout_count = ((df_maand["Raw Value"] < 0) | (df_maand["Raw Value"] > 360)).sum()
    fout_percentage = (fout_count / totaal_waarden) * 100

    laagste_maand = df_maand["Raw Value"].min()
    hoogste_maand = df_maand["Raw Value"].max()

    st.markdown(f"""
    ### Maandstatistieken ({gekozen_dag.strftime('%B %Y')})
    - **Aantal ongeldige waarden:** {fout_count}  
    - **Percentage ongeldige waarden:** {fout_percentage:.1f}%  
    - **Laagste waarde in de maand:** {laagste_maand}°  
    - **Hoogste waarde in de maand:** {hoogste_maand}°  
    """)

    problemen = []

    if fout_percentage >= 50:
        maand_conclusie = (
            "❌ Meer dan 50% van de maandwaarden is ongeldig. "
            "De data is NIET geschikt voor analyse."
        )
    else:
        if fout_count > 0:
            problemen.append(
                f"Er zijn {fout_count} ongeldige waarden gevonden. "
                "Filter deze uit voordat je de data verder gebruikt."
            )

        if problemen:
            maand_conclusie = (
                "⚠️ De data bevat aandachtspunten. Gebruik de data alleen na filtering.\n\n"
                + "\n".join(f"- {p}" for p in problemen)
            )
        else:
            maand_conclusie = (
                "✔ Het station toont geldige windrichtingwaarden voor deze maand. "
                "Het station is geschikt voor verdere analyse."
            )

    st.markdown(f"### Maandconclusie\n{maand_conclusie}")

# ---------------------------------------------------------
# 12. PREMIUM WINDROOS – MAAND (ZONDER DOMINANTE PIJL)
# ---------------------------------------------------------
st.subheader("Maandelijkse Windroos")

df_maand_valid = df_maand[df_maand["Raw Value"].between(0, 360)]

if df_maand_valid.empty:
    st.info("Geen geldige windrichtingwaarden beschikbaar voor deze maand.")
else:
    df_maand_valid["Sector"] = (df_maand_valid["Raw Value"] // 10) * 10
    freq_m = df_maand_valid.groupby("Sector").size().reset_index(name="Count")

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
        opacity=0.95,
        name="Frequentie"
    ))

    cardinal_angles = [0, 45, 90, 135, 180, 225, 270, 315]
    cardinal_labels = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

    for angle, label in zip(cardinal_angles, cardinal_labels):
        fig_m.add_trace(go.Scatterpolar(
            r=[max_count_m * 1.8],
            theta=[angle],
            mode="text",
            text=[label],
            textfont=dict(size=14, color="black"),
            showlegend=False
        ))

    fig_m.update_layout(
        title=f"Maandelijkse Windroos – {gekozen_dag.strftime('%B %Y')}",
        polar=dict(
            radialaxis=dict(showticklabels=True, ticks='outside', range=[0, max_count_m * 2]),
            angularaxis=dict(direction="clockwise", rotation=90)
        ),
        showlegend=True
    )

    st.plotly_chart(fig_m, use_container_width=True)

    st.markdown("""
    ### Uitleg Windroos
    De windroos toont **hoe vaak** de wind uit elke richting heeft gewaaid.

    - **Blauwe balken**: geven de **frequentie** weer.  
      - Hoe **langer** de balk, hoe **vaker** de wind uit die richting kwam.  
      - Hoe **donkerder** de kleur, hoe **hoger** de frequentie.

    - De cirkel is verdeeld in **sectoren van 10°** (0°, 10°, 20°, … 350°).

    - De labels **N, NE, E, SE, S, SW, W, NW** geven de **windrichtingen** aan.

    - De windroos gebruikt **alle individuele metingen** van de maand.  
      Er wordt **geen gemiddelde windrichting** berekend, omdat dat meteorologisch niet correct is.
    """)

    st.markdown(f"""
    ### Maandelijkse Windrichting Samenvatting
    - **Hoogste frequentie:** {max_count_m} metingen  
    - **Aantal sectoren met wind:** {freq_m[freq_m['Count'] > 0].shape[0]}  
    """)
