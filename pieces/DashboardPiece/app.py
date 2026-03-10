"""Streamlit dashboard app for DashboardPiece output (dashboard_data.json)."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


def _load_payload(path: str = "dashboard_data.json") -> dict:
    json_path = Path(path)
    if not json_path.is_file():
        return {}
    try:
        return json.loads(json_path.read_text())
    except Exception:
        return {}


def _records_to_df(records: object) -> pd.DataFrame:
    if not isinstance(records, list) or not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    return df


def _as_float(value, default=0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _pick_existing(columns: list[str], options: list[str]) -> str | None:
    lower_map = {column.lower(): column for column in columns}
    for option in options:
        if option.lower() in lower_map:
            return lower_map[option.lower()]
    return None


def _filter_by_scenario(df: pd.DataFrame, selected_scenario: str) -> pd.DataFrame:
    if df.empty:
        return df
    for col in ["scenario", "scenario_name", "case", "variant"]:
        if col in df.columns:
            filtered = df[df[col].astype(str) == selected_scenario]
            if not filtered.empty:
                return filtered
    return df


def _first_row(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    return df.iloc[0].to_dict()


def _kpi_value(mapping: dict, keys: list[str], default: float = 0.0) -> float:
    for key in keys:
        if key in mapping:
            return _as_float(mapping[key], default)
    return default


def _render_dataset_table(title: str, df: pd.DataFrame, missing_message: str) -> None:
    st.markdown(f"**{title}**")
    if df.empty:
        st.info(missing_message)
        return
    st.caption(f"Rows: {len(df)} | Columns: {len(df.columns)}")
    st.dataframe(df, width="stretch")


def _find_soc_series(*frames: pd.DataFrame) -> tuple[pd.DataFrame, str | None, str | None]:
    for frame in frames:
        if frame.empty:
            continue
        datetime_col = _pick_existing(frame.columns.tolist(), ["datetime", "timestamp", "time"])
        soc_col = _pick_existing(frame.columns.tolist(), ["soc_pct", "battery_soc", "state_of_charge", "soc"])
        if datetime_col and soc_col:
            return frame, datetime_col, soc_col
    return pd.DataFrame(), None, None


st.set_page_config(page_title="ISGvRE - Virtual RE", layout="wide")
st.title("ISGvRE - Virtual RE Dashboard")

payload = _load_payload("dashboard_data.json")
if not payload:
    st.warning("dashboard_data.json was not provided or could not be parsed.")
    st.stop()

datasets = payload.get("datasets", {})
status = payload.get("inputs", {})

preprocess_df = _records_to_df(datasets.get("preprocess_predict", []))
predict_df = _records_to_df(datasets.get("predict_predictions", []))
simulate_df = _records_to_df(datasets.get("simulate_results", []))
simulate_summary_df = _records_to_df(datasets.get("simulate_summary", []))
kpi_df = _records_to_df(datasets.get("kpi_results", []))
investment_df = _records_to_df(datasets.get("investment_evaluation", []))

scenario_options = payload.get("scenarios") or ["Default"]
default_scenario = payload.get("default_scenario", scenario_options[0])
selected_scenario = st.selectbox(
    "Scenario selector",
    scenario_options,
    index=scenario_options.index(default_scenario) if default_scenario in scenario_options else 0,
)

st.subheader("What-If RE Capacity")
re_capacity_factor = st.slider(
    "What-If RE capacity multiplier",
    min_value=0.5,
    max_value=2.0,
    step=0.05,
    value=1.0,
)

# KPI cards
st.subheader("KPI Cards")
kpi_data = {}
kpi_data.update(_first_row(simulate_summary_df))
kpi_data.update(_first_row(kpi_df))
kpi_data.update(_first_row(investment_df))

saving = _kpi_value(
    kpi_data,
    ["annual_savings_eur", "annual_savings_€", "estimated_yearly_savings_eur", "savings_eur"],
)
peak_reduction = _kpi_value(kpi_data, ["peak_reduction_kw", "peak_reduction", "peak_shaving_kw"])
payback = _kpi_value(kpi_data, ["simple_payback_years", "payback_years", "payback_period", "payback"])
co2_saved = _kpi_value(kpi_data, ["annual_co2_saved_ton", "co2_saved_ton_est", "co2_saved_ton", "co2_saved"])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Saving (€)", f"{saving:,.2f}" if saving else "Not provided")
c2.metric("Peak reduction (kW)", f"{peak_reduction:,.2f}" if peak_reduction else "Not provided")
c3.metric("Payback period (y)", f"{payback:,.2f}" if payback else "Not provided")
c4.metric("CO₂ saved (t)", f"{co2_saved:,.2f}" if co2_saved else "Not provided")

# Load curve
st.subheader("Load Curve: Original vs Net Load")
load_df = simulate_df.copy()
load_df = _filter_by_scenario(load_df, selected_scenario)

if load_df.empty:
    st.info("simulated_results.csv was not provided or has no rows.")
else:
    datetime_col = _pick_existing(load_df.columns.tolist(), ["datetime", "timestamp", "time"])
    original_col = _pick_existing(load_df.columns.tolist(), ["baseline_load_kw", "original_load_kw", "load_kw", "original_load"])
    net_col = _pick_existing(load_df.columns.tolist(), ["simulated_load_kw", "net_load_kw", "net_load", "grid_import_kw"])

    if not datetime_col or not original_col or not net_col:
        st.info("simulated_results.csv does not contain required columns for load curve.")
    else:
        chart_df = load_df[[datetime_col, original_col, net_col]].copy()
        chart_df = chart_df.sort_values(by=datetime_col)
        chart_df["what_if_net_load"] = chart_df[original_col] - (
            (chart_df[original_col] - chart_df[net_col]) * re_capacity_factor
        )
        fig_load = px.line(
            chart_df,
            x=datetime_col,
            y=[original_col, net_col, "what_if_net_load"],
            title="Original vs. Net Load",
        )
        fig_load.update_layout(legend_title_text="Series")
        st.plotly_chart(fig_load, width="stretch")

# Prediction chart
st.subheader("Prediction: Actual vs Forecast")
prediction_df = _filter_by_scenario(predict_df.copy(), selected_scenario)
if prediction_df.empty:
    st.info("predictions_15min.csv was not provided or has no rows.")
else:
    datetime_col = _pick_existing(prediction_df.columns.tolist(), ["datetime", "timestamp", "time"])
    actual_col = _pick_existing(prediction_df.columns.tolist(), ["load_kw", "actual_load_kw", "load"])
    pred_col = _pick_existing(prediction_df.columns.tolist(), ["prediction_load_kw", "prediction_load_mw", "predicted_load_kw"])
    if not datetime_col or not actual_col or not pred_col:
        st.info("predictions_15min.csv does not contain required columns for prediction chart.")
    else:
        fig_pred = px.line(
            prediction_df.sort_values(by=datetime_col),
            x=datetime_col,
            y=[actual_col, pred_col],
            title="Prediction vs Actual Load",
        )
        st.plotly_chart(fig_pred, width="stretch")

# Battery SoC timeline
st.subheader("Battery SoC Timeline")
soc_source_df, datetime_col, soc_col = _find_soc_series(
    _filter_by_scenario(preprocess_df.copy(), selected_scenario),
    _filter_by_scenario(predict_df.copy(), selected_scenario),
    _filter_by_scenario(simulate_df.copy(), selected_scenario),
)
if soc_source_df.empty:
    st.info("Battery SoC data was not provided in the selected output files.")
else:
    soc_df = soc_source_df[[datetime_col, soc_col]].copy().sort_values(by=datetime_col)
    fig_soc = px.line(soc_df, x=datetime_col, y=soc_col, title="Battery SoC (%)")
    st.plotly_chart(fig_soc, width="stretch")

# MRK comparison bar chart
st.subheader("MRK Comparison")
invest_df = investment_df.copy()
invest_df = _filter_by_scenario(invest_df, selected_scenario)

if invest_df.empty:
    st.info("investment_evaluation.csv was not provided or has no rows.")
else:
    mrk_columns = [c for c in invest_df.columns if "mrk" in c.lower()]
    if not mrk_columns:
        st.info("investment_evaluation.csv does not contain MRK columns.")
    else:
        mrk_means = invest_df[mrk_columns].apply(pd.to_numeric, errors="coerce").mean().reset_index()
        mrk_means.columns = ["metric", "value"]
        fig_mrk = px.bar(mrk_means, x="metric", y="value", title="MRK Comparison")
        st.plotly_chart(fig_mrk, width="stretch")

st.subheader("Source File Data")
_render_dataset_table(
    "PreprocessEnergyDataPiece: predict_dataset_15min.parquet",
    preprocess_df,
    "predict_dataset_15min.parquet was not provided or has no rows.",
)
_render_dataset_table(
    "PredictPiece: predictions_15min.csv",
    predict_df,
    "predictions_15min.csv was not provided or has no rows.",
)
_render_dataset_table(
    "SimulatePiece: simulated_results.csv",
    simulate_df,
    "simulated_results.csv was not provided or has no rows.",
)
_render_dataset_table(
    "SimulatePiece: summary.csv",
    simulate_summary_df,
    "summary.csv was not provided or has no rows.",
)
_render_dataset_table(
    "KPIPiece: kpi_results.csv",
    kpi_df,
    "kpi_results.csv was not provided or has no rows.",
)
_render_dataset_table(
    "InvestmentEvalPiece: investment_evaluation.csv",
    investment_df,
    "investment_evaluation.csv was not provided or has no rows.",
)

with st.expander("Input files status"):
    status_rows = []
    for input_name, details in status.items():
        status_rows.append(
            {
                "input": input_name,
                "provided": details.get("provided", False),
                "rows": details.get("rows", 0),
                "error": details.get("error"),
            }
        )
    if status_rows:
        st.dataframe(pd.DataFrame(status_rows), width="stretch")
    else:
        st.info("No input status metadata available.")