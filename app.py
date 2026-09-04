import streamlit as st
import pandas as pd
import io
from schema_resolver import standardize_dataframe_schema, resolve_column_name
from config import AMOUNT_TOLERANCE_INR, DATE_WINDOW_DAYS, SEMANTIC_SIMILARITY_THRESHOLD
from data_generator import generate_reconciliation_dataset
from pipeline import ReconciliationPipeline
from metrics import PerformanceMetricsEvaluator

# Page Configuration
st.set_page_config(
    page_title="TallyLedgers",
    layout="wide",
    page_icon=""
)

# ---------------------------------------------------------
# Design tokens — cream / dark-teal duotone
# ---------------------------------------------------------
CREAM = "#FBF3E6"
CREAM_SOFT = "#F3E9D8"
INK = "#0E3B3E"
TEAL_900 = "#0E3B3E"
TEAL_700 = "#146569"
TEAL_500 = "#1B8B8C"
TEAL_300 = "#7FBAB6"
TEAL_100 = "#E4EFEA"
TERRACOTTA = "#BC5B2E"
TERRACOTTA_TINT = "#F4E1D3"

DARK_BG = "#0F2626"
DARK_BG_SOFT = "#163434"
DARK_TEXT = "#F3E9D8"
DARK_SUBTEXT = "#8FC4C1"
DARK_BORDER = "#2A5457"
DARK_METRIC_BG = "#163434"
DARK_INPUT_BG = "#0B1D1D"

st.markdown(f"""
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
    html, body, [class*="css"] {{
        font-family: 'IBM Plex Mono', monospace;
    }}

    :root {{
        --bg: {CREAM};
        --bg-soft: {CREAM_SOFT};
        --text: {INK};
        --subtext: {TEAL_700};
        --border: {TEAL_100};
        --input-bg: {CREAM};
        --input-border: {TEAL_300};
        --metric-bg: {TEAL_900};
        --metric-shadow: {TEAL_300};
        --metric-label: {TEAL_100};
        --metric-value: {CREAM};
        --legend-bg: {TEAL_100};
        --legend-text: {INK};
    }}
    
    @media (prefers-color-scheme: dark) {{
        :root {{
            --bg: {DARK_BG};
            --bg-soft: {DARK_BG_SOFT};
            --text: {DARK_TEXT};
            --subtext: {DARK_SUBTEXT};
            --border: {DARK_BORDER};
            --input-bg: {DARK_INPUT_BG};
            --input-border: {TEAL_500};
            --metric-bg: {DARK_METRIC_BG};
            --metric-shadow: {TEAL_700};
            --metric-label: {DARK_SUBTEXT};
            --metric-value: {DARK_TEXT};
            --legend-bg: {DARK_BG_SOFT};
            --legend-text: {DARK_TEXT};
        }}
    }}

    [data-theme="dark"] {{
        --bg: {DARK_BG};
        --bg-soft: {DARK_BG_SOFT};
        --text: {DARK_TEXT};
        --subtext: {DARK_SUBTEXT};
        --border: {DARK_BORDER};
        --input-bg: {DARK_INPUT_BG};
        --input-border: {TEAL_500};
        --metric-bg: {DARK_METRIC_BG};
        --metric-shadow: {TEAL_700};
        --metric-label: {DARK_SUBTEXT};
        --metric-value: {DARK_TEXT};
        --legend-bg: {DARK_BG_SOFT};
        --legend-text: {DARK_TEXT};
    }}

    /* Root text color fix: Streamlit sets color-scheme: dark on a high-level
       wrapper when the viewer's theme is dark, which makes the browser cascade
       its own white (rgb(250,250,250)) down into every descendant that doesn't
       have its own explicit color — including stTabPanel content, plain text,
       and anything we haven't individually targeted. Setting color here, at the
       actual root, fixes the inherited default everywhere in one place instead
       of chasing it widget-by-widget. More specific rules below (cards, sidebar,
       metrics) still win since they're more specific selectors. */
    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stTabPanel"] {{
        color: var(--text) !important;
    }}
    .stApp {{ background-color: var(--bg); }}
    
    .main-header {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 2.8rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin-bottom: 0.1rem;
        color: var(--text) !important;
        border-bottom: 3px solid var(--border);
        padding-bottom: 0.5rem;
    }}
    
    .main-header-sub {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.1rem;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        color: var(--subtext) !important;
        margin-bottom: 0.5rem;
        padding-top: 0.15rem;
        font-weight: 600;
        border-bottom: 2px solid var(--border);
        padding-bottom: 0.75rem;
    }}
    
    .sub-header {{
        font-size: 0.95rem;
        margin-bottom: 1.75rem;
        color: var(--subtext) !important;
    }}
    
    .section-label {{
        font-size: 0.95rem;
        font-weight: 600;
        margin: 1.75rem 0 0.75rem 0;
        padding-bottom: 0.4rem;
        color: var(--text) !important;
        border-bottom: 1px solid var(--border);
        letter-spacing: 0.02em;
    }}
    
    label[data-testid="stWidgetLabel"] p, 
    label[data-testid="stWidgetLabel"] span {{
        color: var(--subtext) !important;
        font-size: 0.8rem !important;
        font-weight: 600 !important;
    }}

    div[data-testid="stSelectbox"] > div > div,
    div[data-testid="stNumberInput"] > div,
    div[data-testid="stTextInput"] > div {{
        background-color: var(--bg-soft) !important;
        border: 1px solid var(--input-border) !important;
        border-radius: 12px;
    }}

    div[data-testid="stNumberInput"] input,
    div[data-testid="stNumberInput"] > div > div {{
        background-color: transparent !important;
    }}

    div[data-testid="stSelectbox"] * {{
        color: var(--text) !important;
    }}

    div[data-testid="stNumberInput"] input,
    div[data-testid="stTextInput"] input {{
        color: var(--text) !important;
    }}

    .stMarkdown, .stMarkdown p, .stMarkdown span, .stMarkdown strong {{
        color: var(--text) !important;
    }}

    div[data-testid="stFileUploader"] section {{
        background-color: var(--input-bg) !important;
        border: 1px dashed var(--input-border) !important;
        border-radius: 16px;
    }}
    
    div[data-testid="stFileUploader"] [data-testid="stUploadedFileData"] {{
        background-color: var(--bg-soft) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
        padding: 8px 12px !important;
    }}
    
    div[data-testid="stFileUploader"] [data-testid="stUploadedFileData"] * {{
        color: var(--text) !important;
        fill: var(--text) !important;
    }}
    
    div[data-testid="stUploadedFileData"] > div:first-child {{
        background-color: var(--border) !important;
        border-radius: 6px !important;
    }}
    
    div[data-testid="stUploadedFileData"] svg {{
        fill: var(--text) !important;
        color: var(--text) !important;
    }}

    div[data-testid="stRadio"] label p {{ color: var(--text) !important; }}

    div[data-testid="stExpander"] {{
        background-color: var(--bg-soft);
        border: 1px solid var(--border);
        border-radius: 18px;
    }}

    div[data-testid="stMetric"] {{
        background-color: var(--metric-bg);
        box-shadow: 7px 7px 0 var(--metric-shadow);
        border-radius: 20px;
        padding: 16px 18px;
        margin-bottom: 8px;
        min-height: 110px;
        border: 1px solid var(--border);
    }}
    
    div[data-testid="stMetric"] label,
    div[data-testid="stMetric"] label p {{
        color: var(--metric-label) !important;
        font-size: 0.78rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }}
    
    div[data-testid="stMetricValue"],
    div[data-testid="stMetricValue"] * {{
        color: var(--metric-value) !important;
        font-size: 1.4rem !important;
        font-weight: 700 !important;
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: clip !important;
    }}

    .stDataFrame {{
        border: 1px solid var(--border);
        border-radius: 16px;
        overflow: hidden;
        background-color: var(--bg);
    }}

    .inline-download-btn {{
        display: flex;
        justify-content: flex-end;
    }}
    
    .inline-download-btn > button {{
        background-color: var(--bg-soft) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        box-shadow: none !important;
        padding: 0.3rem 0.8rem !important;
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        width: auto !important;
        min-height: unset !important;
        letter-spacing: 0.05em;
    }}
    
    .inline-download-btn > button:hover {{
        border-color: {TEAL_500} !important;
        background-color: var(--border) !important;
    }}

    .legend-box {{
        background-color: var(--legend-bg);
        color: var(--legend-text) !important;
        border-radius: 14px;
        padding: 10px 14px;
        margin-top: 8px;
        margin-bottom: 12px;
    }}
    
    .badge-status {{
        padding: 8px 12px;
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 700;
        text-align: center;
        letter-spacing: 0.08em;
        margin-bottom: 2px;
        border: 1px solid transparent;
    }}
    
    .badge-live {{
        background-color: {TEAL_100};
        border-color: {TEAL_500};
        color: {INK};
    }}
    
    .badge-offline {{
        background-color: {TERRACOTTA_TINT};
        border-color: {TERRACOTTA};
        color: {TERRACOTTA};
    }}
    
    /* ============================================================
       UNIFIED TAB STYLING - Clean, consistent, dark mode ready
       ============================================================ */
    
    /* Tab container - the bar that holds all tabs */
    div[data-baseweb="tab-list"] {{
        background-color: var(--bg-soft) !important;
        border-radius: 12px !important;
        padding: 6px !important;
        border: 1px solid var(--border) !important;
        gap: 4px !important;
        margin-bottom: 8px !important;
    }}
    
    /* Individual tab buttons */
    button[data-baseweb="tab"] {{
        background-color: transparent !important;
        color: var(--subtext) !important;
        border-radius: 8px !important;
        padding: 8px 18px !important;
        font-weight: 500 !important;
        border: 1px solid transparent !important;
        transition: all 0.25s ease !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.82rem !important;
        letter-spacing: 0.02em !important;
        min-height: 40px !important;
    }}
    
    /* Hover state */
    button[data-baseweb="tab"]:hover {{
        background-color: var(--border) !important;
        color: var(--text) !important;
        border-color: var(--border) !important;
        transform: translateY(-1px) !important;
    }}
    
    /* Selected/Active tab */
    button[data-baseweb="tab"][aria-selected="true"] {{
        background-color: var(--metric-bg) !important;
        color: var(--metric-value) !important;
        border-color: var(--border) !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.12) !important;
    }}
    
    /* Tab text inside button — target every descendant level (p, span, div),
       since BaseWeb sometimes wraps the label in a nested span with its own
       color that a `p`-only selector won't reach. */
    button[data-baseweb="tab"] p,
    button[data-baseweb="tab"] span,
    button[data-baseweb="tab"] div {{
        color: inherit !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        margin: 0 !important;
        font-family: 'IBM Plex Mono', monospace !important;
    }}

    /* Selected tab text */
    button[data-baseweb="tab"][aria-selected="true"] p,
    button[data-baseweb="tab"][aria-selected="true"] span,
    button[data-baseweb="tab"][aria-selected="true"] div {{
        color: var(--metric-value) !important;
    }}
    
    /* ============================================================
       DARK MODE OVERRIDES
       ============================================================ */
    
    @media (prefers-color-scheme: dark) {{
        div[data-baseweb="tab-list"] {{
            background-color: var(--bg-soft) !important;
            border-color: var(--border) !important;
        }}
        
        button[data-baseweb="tab"] {{
            color: var(--subtext) !important;
        }}
        button[data-baseweb="tab"] p,
        button[data-baseweb="tab"] span,
        button[data-baseweb="tab"] div {{
            color: {DARK_SUBTEXT} !important;
        }}
        
        button[data-baseweb="tab"]:hover {{
            background-color: var(--border) !important;
            color: var(--text) !important;
        }}
        
        button[data-baseweb="tab"][aria-selected="true"] {{
            background-color: var(--metric-bg) !important;
            color: var(--metric-value) !important;
            border-color: var(--border) !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
        }}
        button[data-baseweb="tab"][aria-selected="true"] p,
        button[data-baseweb="tab"][aria-selected="true"] span,
        button[data-baseweb="tab"][aria-selected="true"] div {{
            color: {DARK_TEXT} !important;
        }}
    }}

    /* Explicit dark theme support */
    [data-theme="dark"] div[data-baseweb="tab-list"] {{
        background-color: var(--bg-soft) !important;
        border-color: var(--border) !important;
    }}
    
    [data-theme="dark"] button[data-baseweb="tab"] {{
        color: var(--subtext) !important;
    }}
    [data-theme="dark"] button[data-baseweb="tab"] p,
    [data-theme="dark"] button[data-baseweb="tab"] span,
    [data-theme="dark"] button[data-baseweb="tab"] div {{
        color: {DARK_SUBTEXT} !important;
    }}
    
    [data-theme="dark"] button[data-baseweb="tab"]:hover {{
        background-color: var(--border) !important;
        color: var(--text) !important;
    }}
    
    [data-theme="dark"] button[data-baseweb="tab"][aria-selected="true"] {{
        background-color: var(--metric-bg) !important;
        color: var(--metric-value) !important;
        border-color: var(--border) !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
    }}
    [data-theme="dark"] button[data-baseweb="tab"][aria-selected="true"] p,
    [data-theme="dark"] button[data-baseweb="tab"][aria-selected="true"] span,
    [data-theme="dark"] button[data-baseweb="tab"][aria-selected="true"] div {{
        color: {DARK_TEXT} !important;
    }}
</style>
""", unsafe_allow_html=True)

# Application Header
st.markdown('<div class="main-header">TallyLedgers</div>', unsafe_allow_html=True)
st.markdown('<div class="main-header-sub">Financial Reconciliation Engine</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Enterprise-grade matching and exception management for payment gateway and bank statement records.</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# PIPELINE INITIALIZATION
# ---------------------------------------------------------
@st.cache_resource
def get_pipeline(base_currency: str):
    return ReconciliationPipeline(base_currency=base_currency)

def _get_rates_df(pipeline_obj):
    if hasattr(pipeline_obj.converter, "get_rates_summary"):
        return pipeline_obj.converter.get_rates_summary()
    return pd.DataFrame({
        'Currency': list(pipeline_obj.converter.rate_table.keys()),
        f'Rate to {pipeline_obj.converter.base_currency}': [float(v) for v in pipeline_obj.converter.rate_table.values()]
    }).sort_values('Currency')


# ---------------------------------------------------------
# 1. LANDING PAGE ENGINE CONFIGURATION DASHBOARD
# ---------------------------------------------------------
st.markdown('<div class="section-label">Engine Configuration</div>', unsafe_allow_html=True)

# FIX 1: Explicit vertical_alignment="bottom" aligns all items vertically across the row
col_mode, col_curr, col_tol, col_win, col_sem, col_status = st.columns(
    [1.5, 1, 1, 1, 1, 1.2], 
    vertical_alignment="bottom"
)

with col_mode:
    data_source = st.radio(
        "Data Source",
        ["Custom CSV Upload", "Synthetic Sample Data"],
        index=0,
        help="Choose whether to upload raw operational CSVs or run benchmark synthetic data."
    )

with col_curr:
    base_curr_choice = st.selectbox(
        "Base Currency",
        ["INR", "USD", "EUR", "GBP"],
        index=0,
        help="Target currency for multi-currency conversion normalization."
    )

pipeline = get_pipeline(base_curr_choice)

with col_tol:
    amt_tol = st.number_input(
        f"Amount Tolerance ({base_curr_choice})",
        value=float(100.0),
        step=0.01,
        format="%.2f",
        help="Allowed variance threshold between PG transaction and Bank credit."
    )

with col_win:
    date_win = st.slider(
        "Settlement Window (Days)",
        min_value=1,
        max_value=7,
        value=3,
        help="Maximum allowable days between PG payout date and Bank credit date."
    )

with col_sem:
    sem_thresh = st.slider(
        "Semantic Similarity Cutoff",
        min_value=0.50,
        max_value=0.95,
        value=0.75,
        step=0.05,
        help="SentenceTransformers vector cosine similarity threshold for description matching."
    )

# Clean badge layout aligned bottom
with col_status:
    st.markdown("<label style='font-size: 0.8rem; font-weight: 600; color: var(--subtext); margin-bottom: 8px; display: block; letter-spacing: 0.05em;'>Forex Feed Status</label>", unsafe_allow_html=True)
    if pipeline.converter.is_live:
        st.markdown(f"<div class='badge-status badge-live'>LIVE API MODE</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='badge-status badge-offline'>OFFLINE FALLBACK</div>", unsafe_allow_html=True)

st.markdown("---")

# ---------------------------------------------------------
# 3. DATA INGESTION & COLUMN MAPPING SECTION
# ---------------------------------------------------------
df_pg_raw = None
df_bank_raw = None
ground_truth = []
raw_pg, raw_bank = None, None

if data_source == "Custom CSV Upload":
    st.markdown('<div class="section-label">Operational Data Upload</div>', unsafe_allow_html=True)
    col_up1, col_up2 = st.columns(2)

    with col_up1:
        pg_file = st.file_uploader("Payment Gateway CSV Feed", type=["csv"], key="pg_upload")
    with col_up2:
        bank_file = st.file_uploader("Bank Statement CSV Feed", type=["csv"], key="bank_upload")

    if pg_file and bank_file:
        try:
            pg_file.seek(0)
            bank_file.seek(0)

            raw_pg = pd.read_csv(pg_file)
            raw_bank = pd.read_csv(bank_file)

            pg_cols = [str(c) for c in raw_pg.columns.tolist()]
            bank_cols = [str(c) for c in raw_bank.columns.tolist()]

            with st.expander("Inspect & Configure Field Mappings", expanded=True):
                col_map1, col_map2 = st.columns(2)

                with col_map1:
                    st.markdown("**Payment Gateway Column Mapping**")
                    pg_amt_auto = resolve_column_name(raw_pg, "amount")
                    pg_utr_auto = resolve_column_name(raw_pg, "utr")

                    pg_amt_idx = pg_cols.index(pg_amt_auto) if pg_amt_auto in pg_cols else 0
                    pg_utr_idx = pg_cols.index(pg_utr_auto) if pg_utr_auto in pg_cols else 0

                    pg_amt_col = st.selectbox(
                        "Amount Column (PG)",
                        options=pg_cols,
                        index=pg_amt_idx,
                        key="sb_pg_amt"
                    )
                    pg_utr_col = st.selectbox(
                        "UTR / Reference Column (PG)",
                        options=pg_cols,
                        index=pg_utr_idx,
                        key="sb_pg_utr"
                    )

                with col_map2:
                    st.markdown("**Bank Statement Column Mapping**")
                    bank_amt_auto = resolve_column_name(raw_bank, "amount")
                    bank_utr_auto = resolve_column_name(raw_bank, "utr")

                    bank_amt_idx = bank_cols.index(bank_amt_auto) if bank_amt_auto in bank_cols else 0
                    bank_utr_idx = bank_cols.index(bank_utr_auto) if bank_utr_auto in bank_cols else 0

                    bank_amt_col = st.selectbox(
                        "Credit Amount Column (Bank)",
                        options=bank_cols,
                        index=bank_amt_idx,
                        key="sb_bank_amt"
                    )
                    bank_utr_col = st.selectbox(
                        "UTR / Bank Reference Column (Bank)",
                        options=bank_cols,
                        index=bank_utr_idx,
                        key="sb_bank_utr"
                    )

            with st.expander("Raw Data Preview", expanded=True):
                rev_col1, rev_col2 = st.columns(2)
                with rev_col1:
                    st.markdown("**Payment Gateway Raw Data**")
                    st.dataframe(raw_pg.head(5), use_container_width=True)
                with rev_col2:
                    st.markdown("**Bank Settlement Raw Data**")
                    st.dataframe(raw_bank.head(5), use_container_width=True)

            df_pg_raw = standardize_dataframe_schema(
                raw_pg,
                entity_type="pg",
                override_amount_col=pg_amt_col,
                override_utr_col=pg_utr_col
            )
            df_bank_raw = standardize_dataframe_schema(
                raw_bank,
                entity_type="bank",
                override_amount_col=bank_amt_col,
                override_utr_col=bank_utr_col
            )

            st.success("CSV feeds processed and schema mapping standardized.")
        except Exception as e:
            st.error(f"Error processing uploaded datasets: {e}")
    else:
        st.info("Upload both payment gateway and bank settlement CSV files above to proceed.")

else:
    @st.cache_data
    def get_sample_data():
        return generate_reconciliation_dataset()

    df_pg_raw, df_bank_raw, ground_truth = get_sample_data()
    st.success("Engine initialized with pre-loaded synthetic benchmark dataset.")

    with st.expander("Synthetic Dataset Preview", expanded=False):
        rev_col1, rev_col2 = st.columns(2)
        with rev_col1:
            st.markdown("**Synthetic Payment Gateway Feed**")
            st.dataframe(df_pg_raw.head(5), use_container_width=True)
        with rev_col2:
            st.markdown("**Synthetic Bank Settlement Feed**")
            st.dataframe(df_bank_raw.head(5), use_container_width=True)

# ---------------------------------------------------------
# 4. RECONCILIATION EXECUTION & RESULTS DASHBOARD
# ---------------------------------------------------------
if df_pg_raw is not None and df_bank_raw is not None:
    # Fingerprint the current configuration so we can tell whether the
    # person has changed anything since the last time reconciliation ran.
    current_config = {
        "amount_tolerance": amt_tol,
        "date_window_days": date_win,
        "semantic_threshold": sem_thresh,
        "base_currency": base_curr_choice,
        "data_source": data_source,
        "pg_file_id": (pg_file.name, pg_file.size) if data_source == "Custom CSV Upload" and pg_file else "synthetic",
        "bank_file_id": (bank_file.name, bank_file.size) if data_source == "Custom CSV Upload" and bank_file else "synthetic",
    }

    has_results = "recon_results" in st.session_state
    config_changed = st.session_state.get("recon_last_config") != current_config

    col_run, col_run_status = st.columns([1, 4])
    with col_run:
        run_label = "Rerun reconciliation" if has_results else "Run reconciliation"
        run_clicked = st.button(run_label, key="run_reconciliation_btn")
    with col_run_status:
        if config_changed and has_results:
            st.markdown(
                "<div class='legend-box'>Settings have changed since the last run — "
                "click <b>Rerun reconciliation</b> to apply them.</div>",
                unsafe_allow_html=True
            )

    # Run automatically on first load so the dashboard isn't blank, then only
    # on an explicit click after that — avoids recomputing on every slider tick.
    if run_clicked or not has_results:
        matches, norm_pg, norm_bank, df_exceptions, metrics, df_eval = pipeline.run(
            df_pg=df_pg_raw,
            df_bank=df_bank_raw,
            amount_tolerance=amt_tol,
            date_window_days=date_win,
            semantic_threshold=sem_thresh,
            ground_truth=ground_truth
        )
        st.session_state["recon_results"] = (matches, norm_pg, norm_bank, df_exceptions, metrics, df_eval)
        st.session_state["recon_last_config"] = current_config

    matches, norm_pg, norm_bank, df_exceptions, metrics, df_eval = st.session_state["recon_results"]

    execution_time = metrics.get("elapsed_seconds", 0.0) if isinstance(metrics, dict) else 0.0

    st.markdown('<div class="section-label">Execution Summary</div>', unsafe_allow_html=True)

    matched_count = len(df_eval[~df_eval["match_tier"].str.contains("Unmatched", case=False, na=False)])
    total_count = len(df_eval)
    match_rate = (matched_count / total_count * 100) if total_count > 0 else 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Overall Match Rate", f"{match_rate:.1f}%")
    m2.metric("Total Processed", f"{total_count} records")
    m3.metric("Exceptions Routed", f"{len(df_exceptions)} records")
    m4.metric("Execution Latency", f"{execution_time:.2f} s")

    def style_tiers(val):
        str_val = str(val)
        if "Tier 1" in str_val:
            return f"background-color: {TEAL_900}; color: {CREAM}; font-weight: 600;"
        elif "Tier 2" in str_val:
            return f"background-color: {TEAL_700}; color: {CREAM}; font-weight: 600;"
        elif "Tier 3" in str_val:
            return f"background-color: {TEAL_300}; color: {INK}; font-weight: 600;"
        elif "Unmatched" in str_val:
            return f"background-color: {TERRACOTTA_TINT}; color: {TERRACOTTA}; font-weight: 600;"
        return ""

    FAIL_STYLE = f"background-color: {TERRACOTTA_TINT}; color: {TERRACOTTA}; font-weight: 600;"
    PASS_STYLE = f"background-color: {TEAL_100}; color: {INK}; font-weight: 600;"

    def highlight_ground_truth_failures(row):
        status = str(row.get("evaluation_status", "")).strip().upper()
        if status.startswith("FAIL"):
            return [FAIL_STYLE] * len(row)
        elif status.startswith("PASS"):
            return [PASS_STYLE] * len(row)
        return [""] * len(row)

    # FIX 2: Dynamic inline layout header function
    def render_inline_toolbar_header(title_text, dataframe, filename, key_suffix):
        head_col, btn_col = st.columns([3, 1], vertical_alignment="center")
        with head_col:
            st.markdown(f"### {title_text}" if title_text.startswith("Master") else f"**{title_text}**")
        with btn_col:
            if not dataframe.empty:
                b64 = io.BytesIO()
                dataframe.to_csv(b64, index=False)
                b64.seek(0)
                st.markdown('<div class="inline-download-btn">', unsafe_allow_html=True)
                st.download_button(
                    label="Export CSV",
                    data=b64,
                    file_name=filename,
                    mime="text/csv",
                    key=f"dl_{key_suffix}"
                )
                st.markdown('</div>', unsafe_allow_html=True)

    # Workspace Navigation Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Ledger",
        "Tier Analytics",
        "Exceptions",
        "Accuracy",
        "Normalized Feeds",
        "Engine Specifications"
    ])

    with tab1:
        render_inline_toolbar_header("Master Reconciliation Ledger", df_eval, "master_ledger.csv", "ledger")
        styled_df = df_eval.style.map(style_tiers, subset=["match_tier"])
        st.dataframe(styled_df, use_container_width=True)

    with tab2:
        st.markdown("**Match Tier Distribution**")
        tier_counts = df_eval["match_tier"].value_counts().reset_index()
        tier_counts.columns = ["Match Tier", "Count"]

        col_chart, col_stats = st.columns([2, 1])
        with col_chart:
            st.bar_chart(data=tier_counts, x="Match Tier", y="Count", use_container_width=True)

        with col_stats:
            for _, row in tier_counts.iterrows():
                st.metric(label=row["Match Tier"], value=f"{row['Count']} records")

        st.markdown('<div class="section-label">Filter Records by Tier</div>', unsafe_allow_html=True)
        selected_tier = st.selectbox("Match Tier Filter", options=["All"] + list(df_eval["match_tier"].unique()))

        filtered_df = df_eval if selected_tier == "All" else df_eval[df_eval["match_tier"] == selected_tier]
        
        render_inline_toolbar_header(
            f"Filtered Results: {selected_tier}", 
            filtered_df, 
            f"filtered_{selected_tier.lower().replace(' ', '_')}.csv", 
            f"filtered_{selected_tier}"
        )
        st.dataframe(filtered_df.style.map(style_tiers, subset=["match_tier"]), use_container_width=True)

    with tab3:
        render_inline_toolbar_header("Exception Management Queue", df_exceptions, "exceptions.csv", "exceptions")
        st.caption("Transactions requiring manual reconciliation review due to discrepancies or confidence failures.")

        if not df_exceptions.empty:
            cat_filter = st.multiselect(
                "Filter Exception Category",
                options=list(df_exceptions["Category Tag"].unique()),
                default=list(df_exceptions["Category Tag"].unique())
            )
            filtered_exceptions = df_exceptions[df_exceptions["Category Tag"].isin(cat_filter)]
            st.dataframe(filtered_exceptions, use_container_width=True)
        else:
            st.success("Zero exceptions logged — all records reconciled.")

    with tab4:
        st.markdown("**Ground Truth Accuracy Evaluation**")
        gt_file = st.file_uploader(
            "Ground Truth CSV (Expected Headers: transaction_id, expected_bank_id)",
            type=["csv"],
            key="gt_upload"
        )

        active_gt = ground_truth
        if gt_file:
            gt_df = pd.read_csv(gt_file)
            gt_df.columns = gt_df.columns.str.strip()
            active_gt = gt_df.to_dict(orient="records")

        if active_gt:
            metrics_summary, df_accuracy = PerformanceMetricsEvaluator.evaluate(
                matches, active_gt, start_time=0, end_time=execution_time
            )

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Precision", f"{metrics_summary['precision_pct']}%")
            c2.metric("Recall", f"{metrics_summary['recall_pct']}%")
            c3.metric("F1-Score", f"{metrics_summary['f1_score']}")
            c4.metric("False Positive Rate", f"{metrics_summary['fpr_pct']}%")

            render_inline_toolbar_header("Accuracy Evaluation Results", df_accuracy, "accuracy.csv", "accuracy")
            styled_accuracy = df_accuracy.style.apply(highlight_ground_truth_failures, axis=1)
            st.dataframe(styled_accuracy, use_container_width=True)

    with tab5:
        render_inline_toolbar_header(f"Normalized PG Feed ({base_curr_choice})", norm_pg, "normalized_pg.csv", "norm_pg")
        st.dataframe(norm_pg, use_container_width=True)

        render_inline_toolbar_header(f"Normalized Bank Feed ({base_curr_choice})", norm_bank, "normalized_bank.csv", "norm_bank")
        st.dataframe(norm_bank, use_container_width=True)

    with tab6:
        st.markdown("**Active Engine Operational Parameters**")
        mode_text = "Live API Rates" if pipeline.converter.is_live else "Offline Fallback Rates"
        st.markdown(f"""
        * **Input Mode:** `{data_source}`
        * **Normalization Base Currency:** `{base_curr_choice}`
        * **Forex Conversion Status:** `{mode_text}`
        * **Deterministic Matching Window:** amount tolerance ≤ {amt_tol} {base_curr_choice}, date window ≤ {date_win} days.
        * **Semantic Matching Fallback:** SentenceTransformers model active with similarity threshold ≥ {sem_thresh}.
        """)

        st.markdown('<div class="section-label">Active FX Rates Table</div>', unsafe_allow_html=True)
        rates_df = _get_rates_df(pipeline)
        st.dataframe(rates_df, hide_index=True, use_container_width=True)