# This script requires Python 3.11+ due to modern type hints.
from __future__ import annotations # For modern type hints

"""fund_momentum_emailer.py

Fetches fund price tables and fund-name bundle map,
computes two momentum screens:
    1. Best Long-Term Growth Assessment (top-10) - Ranks primarily by "All Dates" return,
       penalizing for poor 1-year and very poor recent (2-month) performance.
    2. Best Lag-Adjusted Short-Term Assessment (top-10)

Optionally, a list of specific funds can be provided via --compare for direct comparison.
Output tables include 2-week, 1-month, 2-month, 3-month, 6-month, 1-year, and All Dates performance.

Default file locations (assuming script is in 'bin/' and run from project root):
- CSV Data: Scans for 'tables/fund_tables_*.csv' (expected to contain log10 of normalized prices, ISO-8859-15 encoding)
- YAML Bundles: 'bin/fund_name_bundles.yaml' (expected to be ISO-8859-15 encoding)

If the --email flag is provided, it e-mails the top-10 results of each
screen (and any comparison funds) as HTML tables (with a Markdown fallback)
to a recipient specified via environment variables. Otherwise, it prints the
Markdown tables to the console.

This script requires Python 3.11 or newer.

Designed to be run regularly, e.g., via cron or GitHub Actions.

Cron example (Europe/Madrid timezone assumed; adjust path as needed):
    5 6 * * 1-5  /usr/bin/python3.11 /path/to/project/bin/fund_momentum_emailer.py --email

Usage examples:
    python3.11 bin/fund_momentum_emailer.py
    python3.11 bin/fund_momentum_emailer.py --email
    python3.11 bin/fund_momentum_emailer.py --compare "Fund Name A","Another Fund, with comma"
    python3.11 bin/fund_momentum_emailer.py --compare "'Fund C','Fund D'" --email


Environment variables (required only if --email is used):
    SMTP_HOST      default "smtp.gmail.com"
    SMTP_PORT      default "587" (as string, converted to int)
    SMTP_USER      required – full login address
    SMTP_PASS      required – password / app-password (for Gmail with 2FA, use an app password)
    RECIPIENT      required – where to send the e-mail
    SENDER         optional – From: address (defaults to SMTP_USER)
    SUBJECT_PREFIX optional – e-mail subject prefix (default "Daily Fund Momentum Rankings")

Shared Environment variables (can override default local file paths):
    YAML_DATA_URL  optional - URL (http/https/file) for the fund name bundles YAML file.


Python deps: pandas, numpy, pyyaml, requests, tabulate, argparse
    pip install pandas numpy pyyaml requests tabulate
"""
# Standard library imports
import os
import sys
import smtplib
import ssl
import textwrap
import argparse # For command-line argument parsing
import csv # For parsing comma-separated fund list
from datetime import datetime, timezone
from email.message import EmailMessage
from io import StringIO # Used for pd.read_csv with text string
from typing import Dict, List, Tuple, Any
from pathlib import Path # For creating file URIs
import glob # For finding multiple CSV files

# Third-party library imports
import numpy as np
import pandas as pd
import requests
import yaml
from tabulate import tabulate

# ------------------- Config & constants ------------------------------------ #

SCRIPT_PATH = Path(os.path.abspath(__file__))
PROJECT_ROOT_DIR = SCRIPT_PATH.parent.parent

DEFAULT_TABLES_DIR = PROJECT_ROOT_DIR / "tables"
DEFAULT_LOCAL_YAML_PATH = PROJECT_ROOT_DIR / "bin" / "fund_name_bundles.yaml"
DEFAULT_YAML_FILE_URI = DEFAULT_LOCAL_YAML_PATH.as_uri()

YAML_URL = os.getenv("YAML_DATA_URL", DEFAULT_YAML_FILE_URI)

CSV_ENCODING = "iso-8859-15"
YAML_ENCODING = "iso-8859-15"

# Define lookback period keys
TWO_WEEK_LOOKBACK_KEY = "2w"
ONE_MONTH_LOOKBACK_KEY = "1m"
TWO_MONTH_LOOKBACK_KEY = "2m"
THREE_MONTH_LOOKBACK_KEY = "3m"
SIX_MONTH_LOOKBACK_KEY = "6m"
ONE_YEAR_LOOKBACK_KEY = "1y"
ALL_DATES_KEY = "All Dates"


LOOKBACKS_BD: Dict[str, int] = {
    TWO_WEEK_LOOKBACK_KEY: 10, # Approx 2 weeks
    ONE_MONTH_LOOKBACK_KEY: 21,
    TWO_MONTH_LOOKBACK_KEY: 42,
    THREE_MONTH_LOOKBACK_KEY: 63,
    SIX_MONTH_LOOKBACK_KEY: 126,
    ONE_YEAR_LOOKBACK_KEY: 252,
}

# Weights for Lag-Adjusted Short-Term Score (sum to 1.0)
# These specific periods are used for scoring.
LAG_ADJ_WEIGHTS: Dict[str, float] = {
    ONE_MONTH_LOOKBACK_KEY: 0.40,
    THREE_MONTH_LOOKBACK_KEY: 0.35,
    SIX_MONTH_LOOKBACK_KEY: 0.20,
    ONE_YEAR_LOOKBACK_KEY: 0.05,
}
assert abs(sum(LAG_ADJ_WEIGHTS.values()) - 1.0) < 1e-6, "LAG_ADJ_WEIGHTS must sum to 1.0"

# Configuration for Long-Term Growth Assessment (based on "All Dates" primarily)
LONG_TERM_AD_1Y_THRESHOLD = 0.00
LONG_TERM_AD_1Y_PENALTY_FACTOR = 0.5
LONG_TERM_AD_2M_THRESHOLD = -0.05
LONG_TERM_AD_2M_PENALTY_FACTOR = 0.3

DISPLAY_COLUMNS = ["Fund", TWO_WEEK_LOOKBACK_KEY, ONE_MONTH_LOOKBACK_KEY, TWO_MONTH_LOOKBACK_KEY, THREE_MONTH_LOOKBACK_KEY, SIX_MONTH_LOOKBACK_KEY, ONE_YEAR_LOOKBACK_KEY, ALL_DATES_KEY]

LOG_VALUE_CLIP_MIN = -3.0
LOG_VALUE_CLIP_MAX = 3.0

# ------------------- Helper Functions -------------------------------------- #

def fetch_data(url: str, expected_encoding: str) -> str:
    """Download a text file from HTTP/HTTPS or read a local file (file:/// URI) and return its content."""
    if url.startswith("file:///"):
        try:
            file_path_str = url[7:]
            if sys.platform == "win32" and file_path_str.startswith("/"):
                file_path_str = file_path_str[1:]

            file_path = Path(file_path_str)
            with file_path.open('r', encoding=expected_encoding) as f:
                return f.read()
        except FileNotFoundError:
            print(f"Error: Local file not found at {file_path}", file=sys.stderr)
            raise
        except Exception as e:
            print(f"Error reading local file {file_path} with encoding {expected_encoding}: {e}", file=sys.stderr)
            raise
    elif url.startswith("http://") or url.startswith("https://"):
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            try:
                return resp.content.decode(expected_encoding)
            except UnicodeDecodeError:
                print(f"Warning: Could not decode HTTP content from {url} with {expected_encoding}. Falling back to requests' detected encoding.", file=sys.stderr)
                return resp.text
        except requests.exceptions.RequestException as e:
            print(f"Error fetching URL {url}: {e}", file=sys.stderr)
            raise
    else:
        raise ValueError(f"Unsupported URL scheme for {url}. Must be http, https, or file.")


def load_and_parse_individual_csv_files(tables_dir: Path) -> pd.DataFrame:
    """
    Scans a directory for fund_tables_*.csv files, parses each, and concatenates them.
    Skips leading blank lines to find the two '# ;' header lines.
    """
    all_dfs: List[pd.DataFrame] = []
    csv_files = sorted(list(tables_dir.glob("fund_tables_*.csv")))

    if not csv_files:
        print(f"Warning: No CSV files found in {tables_dir} matching pattern 'fund_tables_*.csv'.", file=sys.stderr)
        return pd.DataFrame()

    print(f"Found {len(csv_files)} CSV files to process in {tables_dir}.", file=sys.stderr)

    for csv_file_path in csv_files:
        print(f"Processing file: {csv_file_path.name}", file=sys.stderr)
        lines_to_skip_for_pandas = 0
        header_line1_text: str | None = None
        header_line2_text: str | None = None

        try:
            with csv_file_path.open('r', encoding=CSV_ENCODING) as f:
                temp_lines_read_count = 0
                for line_raw in f:
                    temp_lines_read_count += 1
                    line_stripped = line_raw.strip()
                    if line_stripped:
                        if line_stripped.startswith("# ;"):
                            header_line1_text = line_stripped
                        break
                else:
                    print(f"Warning: No non-blank lines or no first '# ;' header line found in {csv_file_path.name}. Skipping.", file=sys.stderr)
                    continue

                if header_line1_text is None:
                     print(f"Warning: First non-blank line in {csv_file_path.name} is not a '# ;' header. Line: '{line_stripped}'. Skipping.", file=sys.stderr)
                     continue

                header_line2_raw = f.readline()
                temp_lines_read_count += 1
                if not header_line2_raw:
                    print(f"Warning: File {csv_file_path.name} ended unexpectedly after the first potential header line. Skipping.", file=sys.stderr)
                    continue
                header_line2_text = header_line2_raw.strip()

                lines_to_skip_for_pandas = temp_lines_read_count

            if not (header_line1_text.startswith("# ;") and header_line2_text.startswith("# ;")):
                print(f"Warning: File {csv_file_path.name} headers not as expected. H1: '{header_line1_text}', H2: '{header_line2_text}'. Skipping.", file=sys.stderr)
                continue

            actual_header_str = header_line2_text
            column_names_from_header = [p.strip() for p in actual_header_str[3:].split(";") if p.strip()]

            if not column_names_from_header:
                print(f"Warning: No column names extracted from header in {csv_file_path.name}. Header was: '{actual_header_str}'. Skipping.", file=sys.stderr)
                continue

            df_raw_data = pd.read_csv(
                csv_file_path,
                sep=";",
                header=None,
                skiprows=lines_to_skip_for_pandas,
                encoding=CSV_ENCODING,
                skip_blank_lines=True,
                comment='#',
                dtype=str
            )

            if df_raw_data.empty:
                print(f"Warning: DataFrame (raw) empty after reading data from {csv_file_path.name}. Skipping.", file=sys.stderr)
                continue

            num_fund_cols_from_header = len(column_names_from_header)
            expected_total_cols_in_data = 1 + num_fund_cols_from_header

            if df_raw_data.shape[1] < expected_total_cols_in_data:
                num_actual_fund_cols = df_raw_data.shape[1] - 1
                if num_actual_fund_cols < 0 :
                    print(f"Warning: File {csv_file_path.name} has no data columns after date. Skipping.", file=sys.stderr)
                    continue
                current_column_names = ['date_str_temp'] + column_names_from_header[:num_actual_fund_cols]
                while len(current_column_names) < df_raw_data.shape[1]:
                    current_column_names.append(f"Unnamed_Extra_Col_{len(current_column_names)}")
                df_segment = df_raw_data.iloc[:, :len(current_column_names)].copy()
                df_segment.columns = current_column_names
            else:
                df_segment = df_raw_data.iloc[:, :expected_total_cols_in_data].copy()
                df_segment.columns = ['date_str_temp'] + column_names_from_header

            df_segment['date'] = df_segment['date_str_temp'].str.strip()
            df_segment["date"] = pd.to_datetime(df_segment["date"], errors='coerce', dayfirst=False, format='%Y-%m-%d')
            df_segment.drop(columns=['date_str_temp'], inplace=True)
            df_segment.dropna(subset=["date"], inplace=True)

            if df_segment.empty:
                print(f"Warning: DataFrame empty for {csv_file_path.name} after date processing and dropna. Skipping.", file=sys.stderr)
                continue

            for col in df_segment.columns:
                if col != 'date':
                    if df_segment[col].dtype == 'object':
                        df_segment[col] = df_segment[col].str.replace(',', '.', regex=False)
                    df_segment[col] = pd.to_numeric(df_segment[col], errors='coerce')

            df_segment.set_index("date", inplace=True)

            if not df_segment.columns.empty:
                all_dfs.append(df_segment)
            else:
                print(f"Warning: No data columns in {csv_file_path.name} after processing. Skipping.", file=sys.stderr)

        except Exception as e:
            print(f"Error processing file {csv_file_path.name}: {e}. Skipping this file.", file=sys.stderr)
            continue

    if not all_dfs:
        print("Warning: No dataframes were successfully parsed from any CSV file.", file=sys.stderr)
        return pd.DataFrame()

    full_df = pd.concat(all_dfs, axis=1, join='outer').sort_index()

    for col in full_df.columns:
        if full_df[col].dtype == 'object':
            full_df[col] = full_df[col].str.replace(',', '.', regex=False)
        full_df[col] = pd.to_numeric(full_df[col], errors='coerce')

    full_df = full_df.loc[:,~full_df.columns.duplicated(keep='first')]

    if not full_df.empty:
        print(f"Successfully concatenated data from {len(all_dfs)} CSV files into a DataFrame of shape {full_df.shape}.", file=sys.stderr)
    else:
        print(f"Warning: Concatenated DataFrame is empty, though {len(all_dfs)} individual DataFrames were processed (they might have been empty or incompatible).", file=sys.stderr)

    return full_df


def bundle_funds(prices_df: pd.DataFrame, fund_bundles_map: Dict[str, List[str]]) -> pd.DataFrame:
    """Collapse alias fund columns into canonical fund columns using fund_bundles_map."""
    if prices_df.empty:
        print("Warning: Raw prices DataFrame is empty, cannot bundle funds.", file=sys.stderr)
        return pd.DataFrame(index=prices_df.index)

    bundled_cols_dict: Dict[str, pd.Series] = {}
    for canonical_name, alias_names_list in fund_bundles_map.items():
        current_canonical_series: pd.Series | None = None
        for alias in alias_names_list:
            if alias in prices_df.columns:
                alias_data_series = prices_df[alias].copy()
                if current_canonical_series is None:
                    current_canonical_series = alias_data_series
                else:
                    current_canonical_series = current_canonical_series.combine_first(alias_data_series)

        if current_canonical_series is not None and not current_canonical_series.dropna().empty:
            bundled_cols_dict[canonical_name] = current_canonical_series

    if not bundled_cols_dict:
        print("Warning: No fund data could be bundled. Resulting DataFrame will be empty. Check YAML and CSV column names.", file=sys.stderr)
        return pd.DataFrame(index=prices_df.index)

    result_df = pd.DataFrame(bundled_cols_dict)
    return result_df.sort_index()


def compute_momentum_tables(log_prices: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Computes momentum tables and returns top-10s and the full performance DataFrame.
    Input 'log_prices' DataFrame contains log10 of normalized prices for each fund.
    """
    empty_perf_df = pd.DataFrame(index=log_prices.index if not log_prices.empty else None)

    if log_prices.empty or not isinstance(log_prices.index, pd.DatetimeIndex) or log_prices.columns.empty:
        print("Warning: Input log_prices DataFrame for momentum computation is empty or invalid. Returning empty tables.", file=sys.stderr)
        return pd.DataFrame(columns=DISPLAY_COLUMNS), pd.DataFrame(columns=DISPLAY_COLUMNS), empty_perf_df

    fund_performance_records: List[Dict[str, Any]] = []

    for fund_name in log_prices.columns:
        fund_series_raw = log_prices[fund_name].dropna()
        fund_series = fund_series_raw.clip(lower=LOG_VALUE_CLIP_MIN, upper=LOG_VALUE_CLIP_MAX).sort_index()

        if fund_series.empty:
            continue

        fund_latest_date = fund_series.index.max()
        l_current = fund_series.get(fund_latest_date)

        if pd.isna(l_current):
            continue

        if abs(l_current) > 1e-6:
             print(f"Warning: For fund {fund_name}, latest log value {l_current:.4f} (after potential clipping) is not close to 0. "
                   "This might affect return calculations if normalization assumption is incorrect.", file=sys.stderr)

        record: Dict[str, Any] = {"Fund": fund_name}
        has_any_valid_period_return = False

        if not fund_series.empty:
            fund_earliest_date = fund_series.index.min()
            l_earliest_past = fund_series.get(fund_earliest_date)

            if not pd.isna(l_earliest_past) and not pd.isna(l_current):
                log_difference_all_dates = l_current - l_earliest_past
                try:
                    all_dates_return = pow(10, log_difference_all_dates) - 1
                    record[ALL_DATES_KEY] = all_dates_return
                    has_any_valid_period_return = True
                except OverflowError:
                    print(f"Warning: OverflowError calculating '{ALL_DATES_KEY}' return for {fund_name}. Log diff: {log_difference_all_dates:.4f}. Setting return to NaN.", file=sys.stderr)
                    record[ALL_DATES_KEY] = np.nan
            else:
                record[ALL_DATES_KEY] = np.nan
        else:
            record[ALL_DATES_KEY] = np.nan

        for period_label, business_days_offset in LOOKBACKS_BD.items():
            target_past_date_for_lookback = fund_latest_date - pd.tseries.offsets.BDay(business_days_offset)
            valid_past_dates = fund_series.index[fund_series.index <= target_past_date_for_lookback]
            actual_past_data_date = pd.NaT if valid_past_dates.empty else valid_past_dates.max()

            if pd.isna(actual_past_data_date):
                record[period_label] = np.nan
                continue

            l_past = fund_series.get(actual_past_data_date)

            if pd.isna(l_past):
                record[period_label] = np.nan
            else:
                log_difference = l_current - l_past
                try:
                    period_return = pow(10, log_difference) - 1
                    record[period_label] = period_return
                    has_any_valid_period_return = True
                except OverflowError:
                    print(f"Warning: OverflowError calculating return for {fund_name}, period {period_label}. Log diff: {log_difference:.4f}. Setting return to NaN.", file=sys.stderr)
                    record[period_label] = np.nan

        if has_any_valid_period_return:
            fund_performance_records.append(record)

    if not fund_performance_records:
        print("Warning: No performance records could be calculated for any fund.", file=sys.stderr)
        return pd.DataFrame(columns=DISPLAY_COLUMNS), pd.DataFrame(columns=DISPLAY_COLUMNS), empty_perf_df

    perf_df = pd.DataFrame(fund_performance_records).set_index("Fund")

    if ALL_DATES_KEY in perf_df.columns:
        perf_df['LongTermAdjustedPerf'] = perf_df[ALL_DATES_KEY].copy()
        perf_df['LongTermAdjustedPerf'] = perf_df['LongTermAdjustedPerf'].fillna(-np.inf)

        if ONE_YEAR_LOOKBACK_KEY in perf_df.columns:
            poor_1y_mask = (perf_df[ONE_YEAR_LOOKBACK_KEY].notna()) & \
                           (perf_df[ONE_YEAR_LOOKBACK_KEY] < LONG_TERM_AD_1Y_THRESHOLD)
            if poor_1y_mask.any():
                shortfall_1y = (LONG_TERM_AD_1Y_THRESHOLD - perf_df.loc[poor_1y_mask, ONE_YEAR_LOOKBACK_KEY])
                valid_all_dates_for_penalty_1y = perf_df.loc[poor_1y_mask, ALL_DATES_KEY].fillna(0)
                penalty_1y = shortfall_1y * valid_all_dates_for_penalty_1y.abs() * LONG_TERM_AD_1Y_PENALTY_FACTOR
                perf_df.loc[poor_1y_mask, 'LongTermAdjustedPerf'] -= penalty_1y

        if TWO_MONTH_LOOKBACK_KEY in perf_df.columns:
            significant_2m_loss_mask = (perf_df[TWO_MONTH_LOOKBACK_KEY].notna()) & \
                                       (perf_df[TWO_MONTH_LOOKBACK_KEY] < LONG_TERM_AD_2M_THRESHOLD)
            if significant_2m_loss_mask.any():
                loss_beyond_threshold_2m = (perf_df.loc[significant_2m_loss_mask, TWO_MONTH_LOOKBACK_KEY] - LONG_TERM_AD_2M_THRESHOLD).abs()
                valid_all_dates_for_penalty_2m = perf_df.loc[significant_2m_loss_mask, ALL_DATES_KEY].fillna(0)
                penalty_2m = loss_beyond_threshold_2m * valid_all_dates_for_penalty_2m.abs() * LONG_TERM_AD_2M_PENALTY_FACTOR
                perf_df.loc[significant_2m_loss_mask, 'LongTermAdjustedPerf'] -= penalty_2m

        long_term_top10 = perf_df.sort_values("LongTermAdjustedPerf", ascending=False).head(10).reset_index()
    else:
        print(f"Warning: Missing '{ALL_DATES_KEY}' column for Long-Term Growth. Using empty table.", file=sys.stderr)
        long_term_top10 = pd.DataFrame(columns=DISPLAY_COLUMNS)

    z_scores_df_cols: Dict[str, pd.Series] = {}
    for period in LAG_ADJ_WEIGHTS.keys():
        if period in perf_df.columns:
            period_returns = perf_df[period].dropna()
            if len(period_returns) >= 2:
                mean_return = period_returns.mean()
                std_dev_return = period_returns.std(ddof=0)
                if std_dev_return != 0:
                    z_scores_df_cols[period] = (perf_df[period] - mean_return) / std_dev_return
                else:
                    z_scores_df_cols[period] = np.where(perf_df[period].notna(), 0.0, np.nan)
            else:
                z_scores_df_cols[period] = pd.Series(np.nan, index=perf_df.index, name=period)

    if not z_scores_df_cols and not perf_df.empty:
        perf_df["LagAdjScore"] = np.nan
    elif z_scores_df_cols:
        z_scores_df = pd.DataFrame(z_scores_df_cols).reindex(perf_df.index)
        weighted_z_scores_sum = pd.Series(0.0, index=perf_df.index)
        for period_key in LAG_ADJ_WEIGHTS.keys():
            if period_key in z_scores_df.columns:
                weighted_z_scores_sum = weighted_z_scores_sum.add(
                    LAG_ADJ_WEIGHTS[period_key] * z_scores_df[period_key].fillna(0),
                    fill_value=0
                )
        perf_df["LagAdjScore"] = weighted_z_scores_sum

    if "LagAdjScore" not in perf_df.columns and not perf_df.empty:
        perf_df["LagAdjScore"] = np.nan

    lag_adj_top10 = perf_df.sort_values("LagAdjScore", ascending=False).head(10).reset_index()

    return long_term_top10, lag_adj_top10, perf_df.reset_index()


def format_df_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """Prepares a DataFrame for display: selects columns and formats percentages."""
    if df.empty:
        return pd.DataFrame(columns=DISPLAY_COLUMNS)

    df_display = df.copy()
    if "Fund" not in df_display.columns and df_display.index.name == "Fund":
        df_display.reset_index(inplace=True)
    elif "Fund" not in df_display.columns and "Fund" in df_display.index.names:
         df_display.reset_index(level="Fund", inplace=True)


    for col in DISPLAY_COLUMNS:
        if col not in df_display.columns:
            df_display[col] = np.nan

    df_display = df_display[DISPLAY_COLUMNS]

    for col_label in DISPLAY_COLUMNS:
        if col_label != "Fund" and col_label in df_display.columns:
            df_display[col_label] = pd.to_numeric(df_display[col_label], errors='coerce') * 100
    return df_display

def df_to_markdown_table(df: pd.DataFrame) -> str:
    """Converts a DataFrame to a Markdown table string."""
    formatted_df = format_df_for_display(df)

    if formatted_df.empty and not df.empty:
        return "No data available for this assessment after formatting."
    elif formatted_df.empty and df.empty:
        return "No data available for this assessment."

    for col_label in DISPLAY_COLUMNS:
        if col_label != "Fund" and col_label in formatted_df.columns:
            formatted_df[col_label] = formatted_df[col_label].apply(
                lambda x: f"{x:.1f}%" if pd.notnull(x) else "N/A"
            )

    return tabulate(
        formatted_df, headers="keys", tablefmt="pipe",
        showindex=False, stralign="left", numalign="right"
    )

def df_to_html_table_styled(df: pd.DataFrame, table_id: str | None = None) -> str:
    """Converts a DataFrame to an HTML table string."""
    formatted_df = format_df_for_display(df)

    if formatted_df.empty and not df.empty:
        return "<p>No data available for this assessment after formatting.</p>"
    elif formatted_df.empty and df.empty:
        return "<p>No data available for this assessment.</p>"

    return formatted_df.to_html(
        index=False, na_rep="N/A",
        float_format=lambda x: f"{x:,.1f}%" if pd.notnull(x) else "N/A",
        border=0, classes="fund-table", table_id=table_id, escape=True
    )

def send_email(subject: str, html_body: str, text_body: str) -> None:
    """Sends an email with HTML and plain text alternatives."""
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port_str = os.getenv("SMTP_PORT", "587")
    try:
        smtp_port = int(smtp_port_str)
    except ValueError:
        print(f"Warning: SMTP_PORT '{smtp_port_str}' is not valid. Using default 587.", file=sys.stderr)
        smtp_port = 587

    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    recipient = os.getenv("RECIPIENT")
    sender = os.getenv("SENDER", smtp_user)

    missing_env_vars = [var for var, val in [("SMTP_USER", smtp_user), ("SMTP_PASS", smtp_pass), ("RECIPIENT", recipient)] if not val]
    if missing_env_vars:
        raise SystemExit(f"Error: Missing required SMTP env vars: {', '.join(missing_env_vars)}")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls(context=context)
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        print(f"Email sent successfully to {recipient}.", file=sys.stderr)
    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTP Auth Error: {e}. Check credentials/app password.", file=sys.stderr)
        raise SystemExit("Exiting due to SMTP Authentication Error.")
    except smtplib.SMTPException as e:
        print(f"SMTP Error: {e}", file=sys.stderr)
        raise SystemExit("Exiting due to SMTP Error.")
    except Exception as e:
        print(f"Unexpected email error: {e}", file=sys.stderr)
        raise SystemExit("Exiting due to unexpected email sending error.")

# ------------------- Main Execution --------------------------------------- #

def main() -> None:
    """Main function to orchestrate fetching, processing, and optionally emailing."""

    parser = argparse.ArgumentParser(
        description="Fund Momentum Emailer: Fetches fund data, computes momentum, and reports.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--email",
        action="store_true",
        help="Send the report via email. Requires SMTP environment variables to be set.\n"
             "If not set, tables are printed to the console."
    )
    parser.add_argument(
        "--compare",
        type=str,
        default=None,
        help="A comma-separated list of fund names to include for comparison.\n"
             "Example: --compare \"'Fund A, Inc.'\",\"Fund B\",'Fund C'\""
    )
    args = parser.parse_args()

    script_start_time = datetime.now()
    print(f"Script execution started at {script_start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}", file=sys.stderr)
    print(f"Scanning for CSV files in: {DEFAULT_TABLES_DIR}", file=sys.stderr)
    print(f"Using YAML bundle source: {YAML_URL}", file=sys.stderr)


    current_date_utc_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    email_subject_prefix = os.getenv("SUBJECT_PREFIX", "Daily Fund Momentum Rankings")
    final_email_subject = f"{email_subject_prefix} - {current_date_utc_str}"

    raw_prices_df = pd.DataFrame()
    processed_prices_df = pd.DataFrame()
    actual_fund_bundles: Dict[str, List[str]] = {}

    print("Fetching YAML bundle data...", file=sys.stderr)
    try:
        fund_name_bundles_yaml_txt = fetch_data(YAML_URL, expected_encoding=YAML_ENCODING)
    except Exception as e:
        print(f"Critical error: Failed to fetch YAML bundle data: {e}. Cannot proceed without fund names.", file=sys.stderr)
        sys.exit(1)

    print("Parsing fund name bundles from YAML...", file=sys.stderr)
    try:
        fund_bundles_from_yaml = yaml.safe_load(fund_name_bundles_yaml_txt)
        if not isinstance(fund_bundles_from_yaml, dict):
            raise ValueError("YAML content did not parse into a dictionary.")

        temp_actual_fund_bundles: Dict[str, List[str]] | None = None
        if 'fund_names' in fund_bundles_from_yaml and isinstance(fund_bundles_from_yaml['fund_names'], dict):
            temp_actual_fund_bundles = fund_bundles_from_yaml['fund_names']
            print("Info: Extracted bundles from 'fund_names' key in YAML.", file=sys.stderr)
        else:
            for key, value in fund_bundles_from_yaml.items():
                if isinstance(value, dict):
                    is_bundle_dict = all(isinstance(sub_value, list) for sub_value in value.values()) if value else False
                    if is_bundle_dict:
                        print(f"Info: Using bundles from YAML key '{key}'.", file=sys.stderr)
                        temp_actual_fund_bundles = value
                        break

        if temp_actual_fund_bundles is not None:
            actual_fund_bundles = temp_actual_fund_bundles
        else:
            raise ValueError("Could not find fund name bundles in YAML. Check 'fund_names' key or overall structure.")

    except Exception as e:
        print(f"Critical error during parsing of YAML: {e}. Aborting.", file=sys.stderr)
        sys.exit(1)


    print("Loading and parsing individual CSV files from tables directory...", file=sys.stderr)
    try:
        raw_prices_df = load_and_parse_individual_csv_files(DEFAULT_TABLES_DIR)
        if raw_prices_df.empty:
            print("Warning: Parsed raw prices DataFrame is empty after processing all CSVs.", file=sys.stderr)
    except Exception as e:
        print(f"Error during loading/parsing of CSV files: {e}. Report will show limited/no data.", file=sys.stderr)
        raw_prices_df = pd.DataFrame()


    print("Bundling fund columns...", file=sys.stderr)
    try:
        processed_prices_df = bundle_funds(raw_prices_df, actual_fund_bundles)
        if processed_prices_df.empty and not raw_prices_df.empty and actual_fund_bundles :
             print("Warning: Prices DataFrame is empty after bundling funds. This might be due to no matching fund names.", file=sys.stderr)
    except Exception as e:
        print(f"Error during fund bundling: {e}. Proceeding with unbundled or empty data for report.", file=sys.stderr)
        processed_prices_df = raw_prices_df if raw_prices_df is not None else pd.DataFrame()


    print("Computing momentum tables...", file=sys.stderr)
    full_perf_df = pd.DataFrame()
    try:
        long_term_top10_df, lag_adj_top10_df, full_perf_df = compute_momentum_tables(processed_prices_df)
    except Exception as e:
        print(f"Error computing momentum tables: {e}. Report will show no data for tables.", file=sys.stderr)
        long_term_top10_df = pd.DataFrame(columns=DISPLAY_COLUMNS)
        lag_adj_top10_df = pd.DataFrame(columns=DISPLAY_COLUMNS)
        full_perf_df = pd.DataFrame(columns=DISPLAY_COLUMNS)

    md_comparison_table = ""
    html_comparison_table = ""
    comparison_funds_perf_df = pd.DataFrame(columns=DISPLAY_COLUMNS)

    if args.compare:
        print(f"Processing comparison funds: {args.compare}", file=sys.stderr)
        f = StringIO(args.compare)
        reader = csv.reader(f, skipinitialspace=True)
        try:
            requested_fund_names = next(reader)
        except StopIteration:
            requested_fund_names = []

        if requested_fund_names:
            if "Fund" in full_perf_df.columns:
                comparison_funds_perf_df = full_perf_df[full_perf_df['Fund'].isin(requested_fund_names)].copy()

            if comparison_funds_perf_df.empty:
                print(f"Warning: None of the requested comparison funds were found or had data: {requested_fund_names}", file=sys.stderr)
            else:
                found_funds = comparison_funds_perf_df['Fund'].tolist()
                missing_funds = [name for name in requested_fund_names if name not in found_funds]
                if missing_funds:
                    print(f"Warning: Could not find data for the following comparison funds: {missing_funds}", file=sys.stderr)

            md_comparison_table = df_to_markdown_table(comparison_funds_perf_df)
            html_comparison_table = df_to_html_table_styled(comparison_funds_perf_df, "comparisonFundTable")
        else:
            print("Warning: --compare flag used but no fund names were provided or parsed.", file=sys.stderr)


    print("Generating HTML and Markdown table outputs...", file=sys.stderr)
    html_long_term_table = df_to_html_table_styled(long_term_top10_df, "longTermGrowthTable")
    html_lag_adj_table = df_to_html_table_styled(lag_adj_top10_df, "lagAdjustedShortTermTable")
    md_long_term_table = df_to_markdown_table(long_term_top10_df)
    md_lag_adj_table = df_to_markdown_table(lag_adj_top10_df)

    if args.email:
        print("Constructing email body...", file=sys.stderr)
        plain_text_email_body = textwrap.dedent(f"""
            {email_subject_prefix} - {current_date_utc_str}

            ## Best Long-Term Growth Assessment (Top 10)
            {md_long_term_table}

            ## Best Lag-Adjusted Short-Term Assessment (Top 10)
            {md_lag_adj_table}
        """)
        if md_comparison_table:
            plain_text_email_body += textwrap.dedent(f"""

            ## Comparison Funds Performance
            {md_comparison_table}
            """)
        plain_text_email_body += textwrap.dedent("""

            ---
            *This report was generated automatically by the Fund Momentum Emailer script.*
            *Fund data is typically lagged by several days. Performance figures are historical.*
            *Always do your own research before making investment decisions.*
        """)

        html_email_body = f"""
        <!DOCTYPE html><html lang="en"><head><meta http-equiv="Content-Type" content="text/html; charset=UTF-8"><title>{final_email_subject}</title>
        <style type="text/css">
            body {{font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 15px; padding: 0; background-color: #f4f7f6; color: #333333; line-height: 1.6;}}
            .email-container {{max-width: 700px; margin: 0 auto; background-color: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.05);}}
            h1 {{color: #2c3e50; font-size: 22px; border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-top: 0;}}
            h2 {{color: #3498db; font-size: 18px; margin-top: 25px; margin-bottom: 10px; border-bottom: 1px solid #e0e0e0; padding-bottom: 5px;}}
            .fund-table {{border-collapse: collapse; width: 100%; margin: 15px 0; font-size: 0.9em; border-radius: 5px; overflow: hidden; box-shadow: 0 0 10px rgba(0,0,0,0.05); border: 1px solid #dddddd;}}
            .fund-table th, .fund-table td {{padding: 10px 12px; border-bottom: 1px solid #dddddd; text-align: right;}}
            .fund-table th {{background-color: #3498db; color: #ffffff; text-align: left; font-weight: bold; border-bottom-width: 2px;}}
            .fund-table td:first-child {{text-align: left; font-weight: 500;}}
            .fund-table tbody tr:nth-of-type(even) {{background-color: #f8f9fa;}}
            .fund-table tbody tr:hover {{background-color: #e9ecef;}}
            .fund-table tbody tr:last-child td {{border-bottom: none;}}
            .footer {{margin-top: 30px; padding-top: 15px; border-top: 1px solid #e0e0e0; font-size: 0.85em; color: #767676; text-align: center;}}
            .footer p {{margin: 5px 0;}}
        </style></head><body><div class="email-container"><h1>{final_email_subject}</h1>
        <h2>Best Long-Term Growth Assessment (Top 10)</h2>{html_long_term_table}
        <h2>Best Lag-Adjusted Short-Term Assessment (Top 10)</h2>{html_lag_adj_table}
        """
        if html_comparison_table:
            html_email_body += f"""<h2>Comparison Funds Performance</h2>{html_comparison_table}"""

        html_email_body += f"""
        <div class="footer"><p>This report was generated automatically by the Fund Momentum Emailer script.</p>
        <p>Fund data is typically lagged by several days. Performance figures are historical.</p>
        <p>Always do your own research before making investment decisions.</p></div></div></body></html>
        """
        print("Attempting to send email...", file=sys.stderr)
        try:
            send_email(final_email_subject, html_email_body, plain_text_email_body)
        except SystemExit:
            sys.exit(1)
        except Exception as e:
            sys.exit(f"An unexpected error occurred during email sending: {e}")
    else:
        print("\n--- Email sending skipped (--email flag not provided) ---", file=sys.stderr)
        print("\n### Best Long-Term Growth Assessment (Top 10)\n", file=sys.stdout)
        print(md_long_term_table, file=sys.stdout)
        print("\n### Best Lag-Adjusted Short-Term Assessment (Top 10)\n", file=sys.stdout)
        print(md_lag_adj_table, file=sys.stdout)
        if md_comparison_table:
            print("\n### Comparison Funds Performance\n", file=sys.stdout)
            print(md_comparison_table, file=sys.stdout)
        print("\n--- End of Report ---", file=sys.stderr)

    script_end_time = datetime.now()
    total_execution_time = script_end_time - script_start_time
    print(f"Script finished successfully at {script_end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}", file=sys.stderr)
    print(f"Total execution time: {total_execution_time}", file=sys.stderr)
    print("Process completed.", file=sys.stderr)

if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected critical error occurred in the main execution block: {e}", file=sys.stderr)
        print("Traceback:", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
