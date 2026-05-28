import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(page_title="Deals Analytics", layout="wide", page_icon="📊")

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)

SHEETS_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTYJRscGLHS2b2l3S-qdzgY-B-XiZQxzPBHKUEYVuA-lg62asMyGAE-RjpzkU44_iRTwIrtWzYmFZlf/pub?gid=2072143524&single=true&output=csv"

@st.cache_data(ttl=3600)
def load_data():
    df = None
    # Завантаження з Google Sheets (публічний CSV)
    try:
        df = pd.read_csv(SHEETS_CSV_URL)
    except Exception as e:
        st.warning(f"Google Sheets недоступний: {e}. Використовую локальний файл.")

    # Fallback: локальний файл data.xlsx
    if df is None:
        local = Path(__file__).parent / "data.xlsx"
        if local.exists():
            df = pd.read_excel(local)
        else:
            st.error("❌ Не вдалося завантажити дані.")
            st.stop()

    df.columns = df.columns.str.strip()
    df["AQL date"] = pd.to_datetime(df["AQL date"], errors="coerce")
    df["Closing Date"] = pd.to_datetime(df["Closing Date"], errors="coerce")

    ppc_order = {"0.0": 0, "0-500": 1, "500-1000": 2, "1000-2000": 3,
                 "2000-5000": 4, "5000-10000": 5, "20000+": 6}
    df["PPC budget USD"] = df["PPC budget USD"].astype(str).str.strip()
    df["PPC budget USD"] = df["PPC budget USD"].replace("0", "0.0")
    df["ppc_order"] = df["PPC budget USD"].map(ppc_order).fillna(0)
    return df

df = load_data()

# ── Sidebar filters ──────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🔍 Фільтри")

    countries = sorted(df["Client country"].dropna().unique())
    sel_countries = st.multiselect("Client country", countries, default=countries)

    crms = sorted(df["Client CRM"].dropna().unique())
    sel_crms = st.multiselect("Client CRM", crms, default=crms)

    min_date = df["AQL date"].min().date()
    max_date = df["AQL date"].max().date()
    date_range = st.date_input("Date range", value=(min_date, max_date),
                               min_value=min_date, max_value=max_date)

# Apply filters
filtered = df[
    df["Client country"].isin(sel_countries) &
    df["Client CRM"].isin(sel_crms)
]
if len(date_range) == 2:
    filtered = filtered[
        (filtered["AQL date"].dt.date >= date_range[0]) &
        (filtered["AQL date"].dt.date <= date_range[1])
    ]

# ── KPI row ──────────────────────────────────────────────────────────────────
st.title("📊 Deals Analytics Dashboard")

total = len(filtered)
won   = (filtered["Stage"] == "Closed Won").sum()
lost  = (filtered["Stage"] == "Closed Lost").sum()
win_rate = round(won / (won + lost) * 100, 1) if (won + lost) > 0 else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Всього угод", total)
c2.metric("Closed Won", won)
c3.metric("Closed Lost", lost)
c4.metric("Win Rate", f"{win_rate}%")

st.divider()

# ── Row 1: Win rate by country + Win rate by CRM ─────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("🌍 Win rate по країнах")
    closed = filtered[filtered["Stage"].isin(["Closed Won", "Closed Lost"])]
    by_country = (
        closed.groupby("Client country")["Stage"]
        .apply(lambda x: (x == "Closed Won").sum() / len(x) * 100)
        .reset_index()
    )
    by_country.columns = ["Country", "Win Rate %"]
    by_country = by_country.sort_values("Win Rate %", ascending=True)
    fig = px.bar(by_country, x="Win Rate %", y="Country", orientation="h",
                 color="Win Rate %", color_continuous_scale="teal",
                 text=by_country["Win Rate %"].apply(lambda x: f"{x:.0f}%"))
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False, coloraxis_showscale=False,
                      margin=dict(l=0, r=20, t=10, b=0), height=380)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("🖥️ Win rate по CRM")
    by_crm = (
        closed.groupby("Client CRM")["Stage"]
        .apply(lambda x: (x == "Closed Won").sum() / len(x) * 100)
        .reset_index()
    )
    by_crm.columns = ["CRM", "Win Rate %"]
    by_crm = by_crm[by_crm["Win Rate %"] > 0].sort_values("Win Rate %", ascending=True)
    fig2 = px.bar(by_crm, x="Win Rate %", y="CRM", orientation="h",
                  color="Win Rate %", color_continuous_scale="purples",
                  text=by_crm["Win Rate %"].apply(lambda x: f"{x:.0f}%"))
    fig2.update_traces(textposition="outside")
    fig2.update_layout(showlegend=False, coloraxis_showscale=False,
                       margin=dict(l=0, r=20, t=10, b=0), height=380)
    st.plotly_chart(fig2, use_container_width=True)

# ── Row 2: Stage distribution + Deals by Source ──────────────────────────────
col3, col4 = st.columns(2)

with col3:
    st.subheader("📋 Розподіл угод по Stage")
    stage_counts = filtered["Stage"].value_counts().reset_index()
    stage_counts.columns = ["Stage", "Count"]
    color_map = {
        "Closed Won":    "#2ecc71",
        "Closed Lost":   "#e74c3c",
        "Negotiations":  "#3498db",
        "Trial":         "#f39c12",
        "Project set up":"#9b59b6",
        "Payment":       "#1abc9c",
    }
    fig3 = px.pie(stage_counts, values="Count", names="Stage",
                  color="Stage", color_discrete_map=color_map, hole=0.4)
    fig3.update_traces(textposition="outside", textinfo="percent+label")
    fig3.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=380,
                       showlegend=True, legend=dict(orientation="h", y=-0.15))
    st.plotly_chart(fig3, use_container_width=True)

with col4:
    st.subheader("📣 Deals by Source")
    source_counts = filtered["Source"].value_counts().reset_index()
    source_counts.columns = ["Source", "Count"]
    fig4 = px.bar(source_counts, x="Count", y="Source", orientation="h",
                  color="Count", color_continuous_scale="blues", text="Count")
    fig4.update_traces(textposition="outside")
    fig4.update_layout(showlegend=False, coloraxis_showscale=False,
                       margin=dict(l=0, r=20, t=10, b=0), height=380,
                       yaxis=dict(categoryorder="total ascending"))
    st.plotly_chart(fig4, use_container_width=True)

# ── Row 3: Win rate by PPC budget ────────────────────────────────────────────
st.subheader("💰 Залежність win rate від PPC budget")

ppc_label_order = ["0.0", "0-500", "500-1000", "1000-2000", "2000-5000", "5000-10000", "20000+"]
ppc_closed = filtered[filtered["Stage"].isin(["Closed Won", "Closed Lost"])].copy()

by_ppc = (
    ppc_closed.groupby("PPC budget USD")
    .apply(lambda x: pd.Series({
        "Win Rate %":   (x["Stage"] == "Closed Won").sum() / len(x) * 100,
        "Total deals":  len(x),
    }))
    .reset_index()
)
by_ppc = by_ppc[by_ppc["PPC budget USD"].isin(ppc_label_order)]
by_ppc["sort_key"] = by_ppc["PPC budget USD"].map({v: i for i, v in enumerate(ppc_label_order)})
by_ppc = by_ppc.sort_values("sort_key")

fig5 = go.Figure()
fig5.add_trace(go.Bar(
    x=by_ppc["PPC budget USD"], y=by_ppc["Win Rate %"],
    marker_color="#667eea",
    text=by_ppc["Win Rate %"].apply(lambda x: f"{x:.0f}%"),
    textposition="outside",
    name="Win Rate %",
))
fig5.add_trace(go.Scatter(
    x=by_ppc["PPC budget USD"], y=by_ppc["Win Rate %"],
    mode="lines+markers",
    line=dict(color="#f39c12", width=2, dash="dot"),
    marker=dict(size=8, color="#f39c12"),
    name="Тренд",
))
fig5.update_layout(
    xaxis_title="PPC budget USD",
    yaxis_title="Win Rate %",
    margin=dict(l=0, r=0, t=10, b=0),
    height=350,
    legend=dict(orientation="h", y=1.1),
)
st.plotly_chart(fig5, use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.caption(f"Дані: {total} угод | {len(sel_countries)} країн | {len(sel_crms)} CRM")

# ── TAB: Data Quality ─────────────────────────────────────────────────────────
st.divider()
st.header("🔍 Data Quality Check")

issues = []

# 1. Closed Won/Lost без Closing Date
mask1 = df["Stage"].isin(["Closed Won", "Closed Lost"]) & df["Closing Date"].isna()
for _, row in df[mask1].iterrows():
    issues.append({
        "❗ Проблема": "Closed Won/Lost без Closing Date",
        "AQL date": str(row["AQL date"])[:10],
        "Stage": row["Stage"],
        "Country": row["Client country"],
        "CRM": row["Client CRM"],
        "Source": row["Source"],
        "Деталі": "Stage закрита, але дата закриття відсутня"
    })

# 2. Не закрита угода, але є Closing Date
mask2 = ~df["Stage"].isin(["Closed Won", "Closed Lost"]) & df["Closing Date"].notna()
for _, row in df[mask2].iterrows():
    issues.append({
        "❗ Проблема": "Closing Date у незакритій угоді",
        "AQL date": str(row["AQL date"])[:10],
        "Stage": row["Stage"],
        "Country": row["Client country"],
        "CRM": row["Client CRM"],
        "Source": row["Source"],
        "Деталі": f"Stage = {row['Stage']}, але є Closing Date"
    })

# 3. Closing Date раніше за AQL date
mask3 = df["AQL date"].notna() & df["Closing Date"].notna() & (df["Closing Date"] < df["AQL date"])
for _, row in df[mask3].iterrows():
    issues.append({
        "❗ Проблема": "Closing Date раніше за AQL date",
        "AQL date": str(row["AQL date"])[:10],
        "Stage": row["Stage"],
        "Country": row["Client country"],
        "CRM": row["Client CRM"],
        "Source": row["Source"],
        "Деталі": f"AQL: {str(row['AQL date'])[:10]} → Closing: {str(row['Closing Date'])[:10]}"
    })

# 4. Closed Lost без причини відмови
mask4 = (df["Stage"] == "Closed Lost") & (
    df["Loss reason description"].isna() |
    (df["Loss reason description"].astype(str).str.strip() == "")
)
for _, row in df[mask4].iterrows():
    issues.append({
        "❗ Проблема": "Closed Lost без причини відмови",
        "AQL date": str(row["AQL date"])[:10],
        "Stage": row["Stage"],
        "Country": row["Client country"],
        "CRM": row["Client CRM"],
        "Source": row["Source"],
        "Деталі": "Loss reason description порожня"
    })

# 5. Нульова кількість sales reps
mask5 = df["Number of sales reps"].isna() | (df["Number of sales reps"] == 0)
for _, row in df[mask5].iterrows():
    issues.append({
        "❗ Проблема": "Відсутня кількість sales reps",
        "AQL date": str(row["AQL date"])[:10],
        "Stage": row["Stage"],
        "Country": row["Client country"],
        "CRM": row["Client CRM"],
        "Source": row["Source"],
        "Деталі": f"Number of sales reps = {row['Number of sales reps']}"
    })

# ── Виводимо результат ────────────────────────────────────────────────────────
if issues:
    issues_df = pd.DataFrame(issues)

    # Зведена статистика
    summary = issues_df["❗ Проблема"].value_counts().reset_index()
    summary.columns = ["Тип проблеми", "Кількість"]

    total_issues = len(issues_df)
    st.metric("Всього проблем", total_issues,
              delta=f"{round(total_issues/len(df)*100,1)}% від усіх угод",
              delta_color="inverse")

    col_a, col_b = st.columns(2)
    with col_a:
        st.dataframe(summary, use_container_width=True, hide_index=True, height=210)

    with col_b:
        fig_q = px.bar(
            summary, x="Кількість", y="Тип проблеми", orientation="h",
            color="Кількість", color_continuous_scale="reds", text="Кількість"
        )
        fig_q.update_traces(textposition="outside")
        fig_q.update_layout(showlegend=False, coloraxis_showscale=False,
                            margin=dict(l=0, r=40, t=10, b=0), height=210)
        st.plotly_chart(fig_q, use_container_width=True)

    # Фільтр по типу проблеми
    st.subheader("📋 Таблиця Data Issues")
    issue_types = ["Всі"] + sorted(issues_df["❗ Проблема"].unique().tolist())
    selected_type = st.selectbox("Фільтр по типу проблеми", issue_types)

    show_df = issues_df if selected_type == "Всі" else issues_df[issues_df["❗ Проблема"] == selected_type]

    st.dataframe(
        show_df.reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
        column_config={
            "❗ Проблема": st.column_config.TextColumn(width="medium"),
            "Деталі": st.column_config.TextColumn(width="large"),
        }
    )

    # Кнопка завантажити як CSV
    csv = show_df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Завантажити як CSV", csv, "data_issues.csv", "text/csv")

else:
    st.success("✅ Проблем з даними не знайдено!")
