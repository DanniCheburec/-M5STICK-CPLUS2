"""
app.py — Streamlit дашборд.
Запускается: streamlit run app.py

На старте поднимает Flask API в фоновом потоке (порт 5050).
Streamlit сам слушает порт 8501.
"""

import time
import pandas as pd
import streamlit as st
from datetime import datetime

# ─── Запуск Flask API в фоне (только один раз) ───────────────────────────
if "api_started" not in st.session_state:
    from api_server import run_api_server
    run_api_server()
    st.session_state["api_started"] = True

from database import init_db, fetch_all, fetch_stats, EMOTIONS, ts_to_str

init_db()

# ─── Конфигурация страницы ───────────────────────────────────────────────
st.set_page_config(
    page_title="Трекер эмоций",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Sidebar ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Трекер Эмоций")
    st.caption("M5StickC Plus 2")

    st.divider()

    auto_refresh = st.toggle("Авто-обновление", value=False)
    refresh_sec  = st.slider("Интервал (сек)", 5, 60, 10, disabled=not auto_refresh)

    st.divider()

    # Фильтры
    st.subheader("Фильтры")
    source_filter = st.multiselect(
        "Источник",
        options=["serial", "ble", "web", "mobile", "unknown"],
        default=[],
        placeholder="Все источники",
    )

    date_range = st.date_input(
        "Период",
        value=[],
        help="Оставьте пустым для показа всех записей",
    )

    st.divider()
    st.caption("API: http://localhost:5050")
    st.caption(f"Обновлено: {datetime.now().strftime('%H:%M:%S')}")

# ─── Загрузка данных ─────────────────────────────────────────────────────
@st.cache_data(ttl=5)
def load_data():
    rows = fetch_all()
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["datetime"] = df["ts"].apply(ts_to_str)
    # Переименуем колонки в нижнем регистре → с большой буквы для отображения
    rename = {e.lower(): e for e in EMOTIONS}
    df.rename(columns=rename, inplace=True)
    return df


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    if source_filter:
        df = df[df["source"].isin(source_filter)]

    if len(date_range) == 2:
        start = int(datetime.combine(date_range[0], datetime.min.time()).timestamp())
        end   = int(datetime.combine(date_range[1], datetime.max.time()).timestamp())
        df    = df[(df["ts"] >= start) & (df["ts"] <= end)]

    return df


df_raw      = load_data()
df_filtered = apply_filters(df_raw.copy()) if not df_raw.empty else df_raw

# ─── Метрики ─────────────────────────────────────────────────────────────
st.header("Обзор")

stats = fetch_stats()
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Всего записей", stats["total"])
with col2:
    shown = len(df_filtered) if not df_filtered.empty else 0
    st.metric("Показано", shown)
with col3:
    sources_str = ", ".join(stats["sources"].keys()) if stats["sources"] else "—"
    st.metric("Источники", sources_str)
with col4:
    if stats["avg"]:
        best = max(stats["avg"], key=stats["avg"].get)
        st.metric("Лидирующая эмоция", best, delta=f"avg {stats['avg'][best]}")
    else:
        st.metric("Лидирующая эмоция", "—")

# ─── Средние значения (мини-бар-чарт) ───────────────────────────────────
if not df_filtered.empty and all(e in df_filtered.columns for e in EMOTIONS):
    st.subheader("Средние значения по эмоциям")

    avg_df = (
        df_filtered[EMOTIONS]
        .mean()
        .reset_index()
        .rename(columns={"index": "Эмоция", 0: "Среднее"})
    )
    avg_df.columns = ["Эмоция", "Среднее"]

    # Цвета под каждую эмоцию
    COLOR_MAP = {
        "Happiness": "#22c55e",
        "Sadness":   "#3b82f6",
        "Anger":     "#ef4444",
        "Stress":    "#f97316",
        "Energy":    "#eab308",
        "Calm":      "#06b6d4",
    }

    cols_avg = st.columns(len(EMOTIONS))
    for i, emotion in enumerate(EMOTIONS):
        val = df_filtered[emotion].mean() if emotion in df_filtered.columns else 0
        with cols_avg[i]:
            st.metric(emotion, f"{val:.1f}", delta=None)

    st.bar_chart(
        df_filtered[EMOTIONS].mean(),
        use_container_width=True,
        height=220,
        color="#6366f1",
    )

# ─── Таблица записей ─────────────────────────────────────────────────────
st.subheader("Таблица записей")

if df_filtered.empty:
    st.info("Нет записей. Подключите M5Stick и запустите pc_client.py или отправьте данные через API.")
else:
    # Колонки для отображения
    display_cols = ["id", "datetime", "source"] + EMOTIONS

    # Оставляем только те, что есть в df
    display_cols = [c for c in display_cols if c in df_filtered.columns]

    # Colour-map для значений 1-10
    def color_value(val):
        if not isinstance(val, (int, float)):
            return ""
        r = int(255 * (1 - val / 10))
        g = int(255 * (val / 10))
        return f"background-color: rgb({r},{g},80,0.3); color: #1f2937"

    styled = (
        df_filtered[display_cols]
        .style
        .applymap(color_value, subset=EMOTIONS)
        .format({e: "{:.0f}" for e in EMOTIONS if e in display_cols})
    )

    st.dataframe(
        styled,
        use_container_width=True,
        height=min(600, 60 + len(df_filtered) * 36),
        hide_index=True,
    )

    # Экспорт CSV
    csv = df_filtered[display_cols].to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇ Скачать CSV",
        data=csv,
        file_name=f"emotions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )

# ─── График по времени ───────────────────────────────────────────────────
if not df_filtered.empty and len(df_filtered) > 1:
    st.subheader("Динамика по времени")

    emotion_select = st.multiselect(
        "Эмоции для графика",
        options=EMOTIONS,
        default=["Happiness", "Stress", "Energy"],
    )

    if emotion_select:
        chart_df = df_filtered[["datetime"] + [e for e in emotion_select if e in df_filtered.columns]].copy()
        chart_df = chart_df.sort_values("datetime")
        chart_df = chart_df.set_index("datetime")
        st.line_chart(chart_df, use_container_width=True, height=300)

# ─── Авто-обновление ─────────────────────────────────────────────────────
if auto_refresh:
    time.sleep(refresh_sec)
    st.cache_data.clear()
    st.rerun()
