# This script requires Python 3.11+ due to modern type hints.
from __future__ import annotations # For modern type hints

"""fund_momentum_emailer.py

Fetches fund price tables and fund-name bundle map,
computes two momentum screens:
    1. Best Long-Term Growth Assessment (top-20) - Ranks primarily by "All Dates" return,
       penalizing for poor 1-year and very poor recent (2-month) performance.
    2. Best Lag-Adjusted Short-Term Assessment (top-20)

Also displays a table of funds appearing in both top-20 lists.
Optionally, a list of specific funds can be provided via --compare for direct comparison.
Output tables include Rank, Fund, 2-week, 1-month, 2-month, 3-month, 6-month, 1-year, and All Dates performance.
HTML output includes a "Copy CSV" button for each table and sortable columns.

Default file locations (assuming script is in 'bin/' and run from project root):
- CSV Data: Scans for 'tables/fund_tables_*.csv' (expected to contain log10 of normalized prices, ISO-8859-15 encoding)
- YAML Bundles: 'bin/fund_name_bundles.yaml' (expected to be ISO-8859-15 encoding)

Output Behavior:
- Without --email flag: Prints Markdown tables to STDOUT.
- With --email flag: Prints a full HTML document (suitable for an email body) to STDOUT.
  The script itself no longer sends emails. Email sending is expected to be handled externally (e.g., via GitHub Actions).

This script requires Python 3.11 or newer.

Designed to be run regularly, e.g., via cron or GitHub Actions.

Cron example (Europe/Madrid timezone assumed; adjust path as needed for GitHub Actions runner):
    5 6 * * 1-5  /usr/bin/python3.11 /path/to/project/bin/fund_momentum_emailer.py --email > report.html

Usage examples:
    python3.11 bin/fund_momentum_emailer.py
    python3.11 bin/fund_momentum_emailer.py --email > fund_report.html
    python3.11 bin/fund_momentum_emailer.py --compare "Fund Name A","Another Fund, with comma"
    python3.11 bin/fund_momentum_emailer.py --compare "'Fund C','Fund D'" --email > specific_funds_report.html

Environment variables:
    (SMTP variables like SMTP_HOST, SMTP_USER, SMTP_PASS, RECIPIENT, SENDER are no longer
     directly used by the script's primary workflow for the --email flag, as email
     sending has been decoupled. They are kept in the send_email function for potential
     manual use or if direct email sending is re-enabled locally.)

    SUBJECT_PREFIX optional – e-mail subject prefix (default "Daily Fund Momentum Rankings")
                       (This is still used for the HTML title and H1 tag)

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
from email.message import EmailMessage # Kept if send_email is used manually
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
    TWO_WEEK_LOOKBACK_KEY: 10,
    ONE_MONTH_LOOKBACK_KEY: 21,
    TWO_MONTH_LOOKBACK_KEY: 42,
    THREE_MONTH_LOOKBACK_KEY: 63,
    SIX_MONTH_LOOKBACK_KEY: 126,
    ONE_YEAR_LOOKBACK_KEY: 252,
}

LAG_ADJ_WEIGHTS: Dict[str, float] = {
    ONE_MONTH_LOOKBACK_KEY: 0.40,
    THREE_MONTH_LOOKBACK_KEY: 0.35,
    SIX_MONTH_LOOKBACK_KEY: 0.20,
    ONE_YEAR_LOOKBACK_KEY: 0.05,
}
assert abs(sum(LAG_ADJ_WEIGHTS.values()) - 1.0) < 1e-6, "LAG_ADJ_WEIGHTS must sum to 1.0"

LONG_TERM_AD_1Y_THRESHOLD = 0.00
LONG_TERM_AD_1Y_PENALTY_FACTOR = 0.5
LONG_TERM_AD_2M_THRESHOLD = -0.05
LONG_TERM_AD_2M_PENALTY_FACTOR = 0.3

# Updated DISPLAY_COLUMNS to include "Rank"
DISPLAY_COLUMNS = ["Rank", "Fund", TWO_WEEK_LOOKBACK_KEY, ONE_MONTH_LOOKBACK_KEY, TWO_MONTH_LOOKBACK_KEY, THREE_MONTH_LOOKBACK_KEY, SIX_MONTH_LOOKBACK_KEY, ONE_YEAR_LOOKBACK_KEY, ALL_DATES_KEY]

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
                dtype=str # Read all as string initially to handle mixed types or formatting issues
            )

            if df_raw_data.empty:
                continue

            num_fund_cols_from_header = len(column_names_from_header)
            expected_total_cols_in_data = 1 + num_fund_cols_from_header # Date + fund columns

            # Adjust DataFrame shape if it doesn't match header expectations
            if df_raw_data.shape[1] < expected_total_cols_in_data:
                num_actual_fund_cols = df_raw_data.shape[1] - 1
                if num_actual_fund_cols < 0 : # Only date column or less
                    print(f"Warning: File {csv_file_path.name} has no data columns after date. Skipping.", file=sys.stderr)
                    continue
                # Take only the available columns from header, plus date
                current_column_names = ['date_str_temp'] + column_names_from_header[:num_actual_fund_cols]
                # If there are still more data columns than named columns (e.g. malformed CSV)
                # Slice df_raw_data to match the length of current_column_names
                df_segment = df_raw_data.iloc[:, :len(current_column_names)].copy()
                df_segment.columns = current_column_names
            else: # df_raw_data.shape[1] >= expected_total_cols_in_data
                # Take only the expected number of columns
                df_segment = df_raw_data.iloc[:, :expected_total_cols_in_data].copy()
                df_segment.columns = ['date_str_temp'] + column_names_from_header


            df_segment['date'] = df_segment['date_str_temp'].str.strip()
            df_segment["date"] = pd.to_datetime(df_segment["date"], errors='coerce', dayfirst=False, format='%Y-%m-%d') # Ensure correct date parsing
            df_segment.drop(columns=['date_str_temp'], inplace=True)
            df_segment.dropna(subset=["date"], inplace=True) # Remove rows where date parsing failed

            if df_segment.empty: # If all rows had invalid dates
                continue

            # Convert data columns to numeric, coercing errors
            for col in df_segment.columns:
                if col != 'date': # Skip the date column, already datetime
                    if df_segment[col].dtype == 'object': # If it's still object type
                        df_segment[col] = df_segment[col].str.replace(',', '.', regex=False) # Standardize decimal point
                    df_segment[col] = pd.to_numeric(df_segment[col], errors='coerce')

            df_segment.set_index("date", inplace=True)

            if not df_segment.columns.empty: # Check if there are any fund columns left
                all_dfs.append(df_segment)

        except Exception as e:
            print(f"Error processing file {csv_file_path.name}: {e}. Skipping this file.", file=sys.stderr)
            continue

    if not all_dfs:
        print("Warning: No dataframes were successfully parsed from any CSV file.", file=sys.stderr)
        return pd.DataFrame()

    # Concatenate all dataframes. 'outer' join handles different date ranges.
    full_df = pd.concat(all_dfs, axis=1, join='outer').sort_index()

    # Ensure all data columns are numeric after concat (in case some were missed or became object)
    for col in full_df.columns:
        if full_df[col].dtype == 'object':
            full_df[col] = full_df[col].str.replace(',', '.', regex=False)
        full_df[col] = pd.to_numeric(full_df[col], errors='coerce')

    # Remove duplicate columns that might arise from overlapping CSV files, keeping the first occurrence
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
        # Iterate through aliases, taking the first available data for each date
        for alias in alias_names_list:
            if alias in prices_df.columns:
                alias_data_series = prices_df[alias].copy() # Ensure it's a copy
                if current_canonical_series is None:
                    current_canonical_series = alias_data_series
                else:
                    # Fill NaNs in current_canonical_series with values from alias_data_series
                    current_canonical_series = current_canonical_series.combine_first(alias_data_series)

        if current_canonical_series is not None and not current_canonical_series.dropna().empty:
            bundled_cols_dict[canonical_name] = current_canonical_series

    if not bundled_cols_dict:
        print("Warning: No fund data could be bundled. Resulting DataFrame will be empty. Check YAML and CSV column names.", file=sys.stderr)
        return pd.DataFrame(index=prices_df.index) # Return empty DF with original index if any

    result_df = pd.DataFrame(bundled_cols_dict)
    return result_df.sort_index() # Sort by date index


def compute_momentum_tables(log_prices: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Computes momentum tables and returns top-20s and the full performance DataFrame.
    Input 'log_prices' DataFrame contains log10 of normalized prices for each fund.
    Adds 'Rank' column to top-20 tables.
    """
    empty_perf_df = pd.DataFrame(index=log_prices.index if not log_prices.empty else None)
    empty_top_df = pd.DataFrame(columns=DISPLAY_COLUMNS) # For returning empty tables with correct columns

    if log_prices.empty or not isinstance(log_prices.index, pd.DatetimeIndex) or log_prices.columns.empty:
        print("Warning: Input log_prices DataFrame for momentum computation is empty or invalid. Returning empty tables.", file=sys.stderr)
        return empty_top_df.copy(), empty_top_df.copy(), empty_perf_df

    fund_performance_records: List[Dict[str, Any]] = []

    for fund_name in log_prices.columns:
        fund_series_raw = log_prices[fund_name].dropna()
        # Clip values to avoid extreme outliers from affecting log calculations if any persist
        fund_series = fund_series_raw.clip(lower=LOG_VALUE_CLIP_MIN, upper=LOG_VALUE_CLIP_MAX).sort_index()

        if fund_series.empty:
            continue

        fund_latest_date = fund_series.index.max()
        l_current = fund_series.get(fund_latest_date) # log10(Price_latest / Price_latest_normalized_to_1) = log10(1) = 0

        if pd.isna(l_current): # Should not happen if fund_series is not empty and sorted.
            continue

        # Check if the latest log value is indeed close to 0 (as expected for normalized prices)
        if abs(l_current) > 1e-6: # A small tolerance for floating point inaccuracies
             print(f"Warning: For fund {fund_name}, latest log value {l_current:.4f} (after potential clipping) is not close to 0. "
                   "This might affect return calculations if normalization assumption is incorrect.", file=sys.stderr)


        record: Dict[str, Any] = {"Fund": fund_name}
        has_any_valid_period_return = False # Track if any return was calculated for this fund

        # Calculate "All Dates" return
        if not fund_series.empty: # Redundant check, but safe
            fund_earliest_date = fund_series.index.min()
            l_earliest_past = fund_series.get(fund_earliest_date) # log10(Price_earliest / Price_latest_normalized_to_1)

            if not pd.isna(l_earliest_past) and not pd.isna(l_current):
                # log_difference = log(P_curr/P_latest_norm) - log(P_past/P_latest_norm) = log(P_curr/P_past)
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


        # Calculate returns for defined lookback periods
        for period_label, business_days_offset in LOOKBACKS_BD.items():
            # Find the date that is 'business_days_offset' business days before the latest date
            target_past_date_for_lookback = fund_latest_date - pd.tseries.offsets.BDay(business_days_offset)
            # Find the closest available data point on or before this target past date
            valid_past_dates = fund_series.index[fund_series.index <= target_past_date_for_lookback]
            actual_past_data_date = pd.NaT if valid_past_dates.empty else valid_past_dates.max()

            if pd.isna(actual_past_data_date): # No data point found for this lookback period
                record[period_label] = np.nan
                continue

            l_past = fund_series.get(actual_past_data_date) # log10(Price_past_lookback / Price_latest_normalized_to_1)

            if pd.isna(l_past): # Should not happen if actual_past_data_date is valid
                record[period_label] = np.nan
            else:
                log_difference = l_current - l_past # log10(P_curr / P_past_lookback)
                try:
                    period_return = pow(10, log_difference) - 1
                    record[period_label] = period_return
                    has_any_valid_period_return = True
                except OverflowError: # Handle potential math overflow with very large log_differences
                    print(f"Warning: OverflowError calculating return for {fund_name}, period {period_label}. Log diff: {log_difference:.4f}. Setting return to NaN.", file=sys.stderr)
                    record[period_label] = np.nan

        if has_any_valid_period_return: # Only add record if at least one return was computed
            fund_performance_records.append(record)

    if not fund_performance_records:
        print("Warning: No performance records could be calculated for any fund.", file=sys.stderr)
        return empty_top_df.copy(), empty_top_df.copy(), empty_perf_df

    perf_df = pd.DataFrame(fund_performance_records).set_index("Fund")

    # Calculate Long-Term Growth Assessment
    if ALL_DATES_KEY in perf_df.columns:
        perf_df['LongTermAdjustedPerf'] = perf_df[ALL_DATES_KEY].copy()
        perf_df['LongTermAdjustedPerf'] = perf_df['LongTermAdjustedPerf'].fillna(-np.inf) # Ensure NaNs are at the bottom when sorting

        # Penalize for poor 1-year performance
        if ONE_YEAR_LOOKBACK_KEY in perf_df.columns:
            poor_1y_mask = (perf_df[ONE_YEAR_LOOKBACK_KEY].notna()) & \
                           (perf_df[ONE_YEAR_LOOKBACK_KEY] < LONG_TERM_AD_1Y_THRESHOLD)
            if poor_1y_mask.any():
                shortfall_1y = (LONG_TERM_AD_1Y_THRESHOLD - perf_df.loc[poor_1y_mask, ONE_YEAR_LOOKBACK_KEY])
                # Penalize based on the magnitude of "All Dates" return (or 0 if NaN)
                valid_all_dates_for_penalty_1y = perf_df.loc[poor_1y_mask, ALL_DATES_KEY].fillna(0)
                penalty_1y = shortfall_1y * valid_all_dates_for_penalty_1y.abs() * LONG_TERM_AD_1Y_PENALTY_FACTOR
                perf_df.loc[poor_1y_mask, 'LongTermAdjustedPerf'] -= penalty_1y

        # Penalize for significant recent (2-month) losses
        if TWO_MONTH_LOOKBACK_KEY in perf_df.columns:
            significant_2m_loss_mask = (perf_df[TWO_MONTH_LOOKBACK_KEY].notna()) & \
                                       (perf_df[TWO_MONTH_LOOKBACK_KEY] < LONG_TERM_AD_2M_THRESHOLD)
            if significant_2m_loss_mask.any():
                loss_beyond_threshold_2m = (perf_df.loc[significant_2m_loss_mask, TWO_MONTH_LOOKBACK_KEY] - LONG_TERM_AD_2M_THRESHOLD).abs()
                valid_all_dates_for_penalty_2m = perf_df.loc[significant_2m_loss_mask, ALL_DATES_KEY].fillna(0)
                penalty_2m = loss_beyond_threshold_2m * valid_all_dates_for_penalty_2m.abs() * LONG_TERM_AD_2M_PENALTY_FACTOR
                perf_df.loc[significant_2m_loss_mask, 'LongTermAdjustedPerf'] -= penalty_2m

        long_term_top = perf_df.sort_values("LongTermAdjustedPerf", ascending=False).head(20).reset_index()
        if not long_term_top.empty:
            long_term_top.insert(0, 'Rank', range(1, len(long_term_top) + 1))
    else:
        print(f"Warning: Missing '{ALL_DATES_KEY}' column for Long-Term Growth. Using empty table.", file=sys.stderr)
        long_term_top = empty_top_df.copy()


    # Calculate Lag-Adjusted Short-Term Assessment (Z-scores)
    z_scores_df_cols: Dict[str, pd.Series] = {}
    for period in LAG_ADJ_WEIGHTS.keys():
        if period in perf_df.columns:
            period_returns = perf_df[period].dropna() # Use only non-NaN returns for mean/std
            if len(period_returns) >= 2: # Need at least 2 data points to calculate std dev
                mean_return = period_returns.mean()
                std_dev_return = period_returns.std(ddof=0) # Population standard deviation
                if std_dev_return != 0: # Avoid division by zero
                    z_scores_df_cols[period] = (perf_df[period] - mean_return) / std_dev_return
                else: # If std_dev is 0, all returns are the same (or only one non-NaN value)
                    z_scores_df_cols[period] = np.where(perf_df[period].notna(), 0.0, np.nan) # Z-score is 0 for non-NaNs
            else: # Not enough data points for Z-score calculation
                z_scores_df_cols[period] = pd.Series(np.nan, index=perf_df.index, name=period) # Fill with NaNs

    # Calculate weighted LagAdjScore
    if not z_scores_df_cols and not perf_df.empty : # No Z-scores could be calculated
        perf_df["LagAdjScore"] = np.nan # Set to NaN if no Z-scores available
    elif z_scores_df_cols:
        z_scores_df = pd.DataFrame(z_scores_df_cols).reindex(perf_df.index) # Align with perf_df index
        weighted_z_scores_sum = pd.Series(0.0, index=perf_df.index) # Initialize with zeros
        for period_key, weight in LAG_ADJ_WEIGHTS.items():
            if period_key in z_scores_df.columns:
                # Add weighted Z-scores, filling NaNs in Z-scores with 0 for summation
                weighted_z_scores_sum = weighted_z_scores_sum.add(
                    weight * z_scores_df[period_key].fillna(0),
                    fill_value=0 # Ensure addition works even if series are misaligned (should not be due to reindex)
                )
        perf_df["LagAdjScore"] = weighted_z_scores_sum
    # If perf_df is empty, LagAdjScore column won't be added, handled by empty_top_df

    if "LagAdjScore" not in perf_df.columns and not perf_df.empty: # Fallback if somehow not created
        perf_df["LagAdjScore"] = np.nan

    lag_adj_top = perf_df.sort_values("LagAdjScore", ascending=False).head(20).reset_index()
    if not lag_adj_top.empty:
        lag_adj_top.insert(0, 'Rank', range(1, len(lag_adj_top) + 1))
    elif perf_df.empty: # If perf_df was empty to begin with
        lag_adj_top = empty_top_df.copy()
    # If perf_df not empty, but lag_adj_top became empty (e.g. all LagAdjScore NaN), ensure columns
    elif lag_adj_top.empty and not perf_df.empty:
        lag_adj_top = pd.DataFrame(columns=perf_df.reset_index().columns).head(0) # Get columns from perf_df
        if 'Rank' not in lag_adj_top.columns: lag_adj_top.insert(0, 'Rank', pd.Series(dtype='int'))


    return long_term_top, lag_adj_top, perf_df.reset_index()


def format_df_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """Prepares a DataFrame for display: selects columns, reorders, and formats percentages."""
    if df.empty:
        # Return an empty DataFrame with the correct columns for consistent HTML structure
        return pd.DataFrame(columns=DISPLAY_COLUMNS)

    df_display = df.copy()

    # Ensure "Fund" is a column, not an index
    if "Fund" not in df_display.columns:
        if df_display.index.name == "Fund":
            df_display.reset_index(inplace=True)
        elif "Fund" in df_display.index.names: # For MultiIndex, though not expected here
             df_display.reset_index(level="Fund", inplace=True)

    # Ensure all DISPLAY_COLUMNS are present and in the correct order, fill missing with NaN
    df_display = df_display.reindex(columns=DISPLAY_COLUMNS, fill_value=np.nan)

    # Format percentage columns
    for col_label in DISPLAY_COLUMNS:
        # Skip "Fund" and "Rank" from percentage formatting
        if col_label not in ["Fund", "Rank"] and col_label in df_display.columns:
            # Ensure column is numeric before multiplying; NaNs will propagate.
            # Errors during to_numeric (e.g. if a non-numeric string slipped through) become NaN.
            df_display[col_label] = pd.to_numeric(df_display[col_label], errors='coerce') * 100
    return df_display

def df_to_markdown_table(df: pd.DataFrame) -> str:
    """Converts a DataFrame to a Markdown table string."""
    formatted_df = format_df_for_display(df) # This now includes Rank

    if formatted_df.empty and not df.empty: # Original df had data, but formatting resulted in empty
        return "No data available for this assessment after formatting."
    elif formatted_df.empty and df.empty: # Original df was empty
        return "No data available for this assessment."

    # Apply string formatting for display
    for col_label in DISPLAY_COLUMNS:
        if col_label in formatted_df.columns:
            if col_label not in ["Fund", "Rank"]: # Percentage columns
                formatted_df[col_label] = formatted_df[col_label].apply(
                    lambda x: f"{x:.1f}%" if pd.notnull(x) and not np.isinf(x) else "N/A"
                )
            elif col_label == "Rank": # Rank column
                formatted_df[col_label] = formatted_df[col_label].apply(
                    lambda x: f"{int(x)}" if pd.notnull(x) and isinstance(x, (int, float)) and not np.isinf(x) and not np.isnan(x) else "N/A"
                )
            # "Fund" column requires no special formatting here, tabulate handles strings.
    return tabulate(
        formatted_df, headers="keys", tablefmt="pipe",
        showindex=False, stralign="left", numalign="right"
    )

def df_to_html_table_styled(df: pd.DataFrame, table_id: str | None = None) -> str:
    """Converts a DataFrame to an HTML table string with a copy button."""
    # format_df_for_display ensures Rank is present and other columns are ready (percentages multiplied by 100)
    formatted_df = format_df_for_display(df)

    # Define float_format for to_html to handle percentage columns
    # Rank column should be int, pandas to_html usually handles this well if dtype is int.
    # If Rank is float (e.g. due to NaNs), it will be formatted by float_format if not excluded.
    # We handle Rank separately if needed, or ensure its dtype is int/object for N/A.
    # For simplicity, float_format will apply to all float columns.
    # We ensure Rank is not float for percentage display.
    def custom_float_format(x):
        if pd.isnull(x) or np.isinf(x):
            return "N/A"
        return f"{x:,.1f}%" # Applies to performance columns that were multiplied by 100

    html_render_df = formatted_df.copy()
    # For Rank column, ensure it's displayed as integer or N/A
    if 'Rank' in html_render_df.columns:
        html_render_df['Rank'] = html_render_df['Rank'].apply(lambda x: int(x) if pd.notnull(x) and not np.isinf(x) else "N/A")


    if html_render_df.empty:
        # Create an empty table structure with headers for JS to attach to
        # The "No data" message will be inside tbody.
        temp_empty_df_for_headers = pd.DataFrame(columns=DISPLAY_COLUMNS)
        if 'Rank' in temp_empty_df_for_headers.columns: # Ensure Rank column type for empty df if needed
             temp_empty_df_for_headers['Rank'] = temp_empty_df_for_headers['Rank'].astype(object)

        table_html = temp_empty_df_for_headers.to_html(
            index=False,
            na_rep="N/A",
            border=0,
            classes="fund-table", # Add class for JS targeting
            table_id=table_id,
            escape=True # Escape HTML characters in data
        )
        # Replace empty tbody with a "No data" message
        num_cols = len(DISPLAY_COLUMNS)
        no_data_row = f"<tbody><tr><td colspan='{num_cols}' style='text-align:center;'>No data available for this assessment.</td></tr></tbody>"
        table_html = table_html.replace("<tbody>\n    \n  </tbody>", no_data_row) # Pandas 1.x
        table_html = table_html.replace("<tbody>\n    \n</tbody>", no_data_row)   # Pandas 2.x
        table_html = table_html.replace("<tbody></tbody>", no_data_row) # General case
    else:
        # Select columns for .to_html, applying custom formatter for float columns (percentages)
        # Other columns (Rank, Fund) will use default formatting.
        formatters = {}
        for col in DISPLAY_COLUMNS:
            if col not in ["Fund", "Rank"]: # These are our percentage columns
                formatters[col] = custom_float_format

        table_html = html_render_df.to_html(
            index=False,
            na_rep="N/A",
            formatters=formatters, # Apply custom formatters
            border=0,
            classes="fund-table", # Add class for JS targeting
            table_id=table_id,
            escape=True # Escape HTML characters in data
        )

    feedback_id = f"feedback-{table_id}" if table_id else f"feedback-unknown-{np.random.randint(1000)}"
    button_table_id = table_id if table_id else "" # Ensure table_id is not None for JS
    copy_button_html = f"""
    <div class="copy-button-container">
      <button onclick="copyTableAsCsv('{button_table_id}', '{feedback_id}')" title="Copy table data as CSV">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-clipboard" viewBox="0 0 16 16">
          <path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1v-1z"/>
          <path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5h3zm-3-1A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0h-3z"/>
        </svg> Copy CSV
      </button>
      <span id="{feedback_id}" class="copy-feedback"></span>
    </div>
    """
    return f"<div class='table-wrapper'>{table_html}{copy_button_html}</div>"


def send_email(subject: str, html_body: str, text_body: str) -> None:
    """Sends an email with HTML and plain text alternatives.
    Note: This function is currently not called by the main script workflow if --email is used,
    as output is directed to STDOUT for external email handling.
    """
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
    sender = os.getenv("SENDER", smtp_user) # Default sender to user if not specified

    missing_env_vars = [var for var, val in [("SMTP_USER", smtp_user), ("SMTP_PASS", smtp_pass), ("RECIPIENT", recipient)] if not val]
    if missing_env_vars:
        print(f"Error: Missing required SMTP env vars for send_email function: {', '.join(missing_env_vars)}", file=sys.stderr)
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(text_body) # Plain text part
    msg.add_alternative(html_body, subtype="html") # HTML part

    try:
        context = ssl.create_default_context() # For TLS
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls(context=context) # Secure the connection
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        print(f"Email sent successfully to {recipient} (if send_email was called directly).", file=sys.stderr)
    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTP Auth Error (if send_email was called directly): {e}. Check credentials/app password.", file=sys.stderr)
    except smtplib.SMTPException as e:
        print(f"SMTP Error (if send_email was called directly): {e}", file=sys.stderr)
    except Exception as e: # Catch any other exceptions
        print(f"Unexpected email error (if send_email was called directly): {e}", file=sys.stderr)

# ------------------- Main Execution --------------------------------------- #

def main() -> None:
    """Main function to orchestrate fetching, processing, and optionally emailing."""

    parser = argparse.ArgumentParser(
        description="Fund Momentum Emailer: Fetches fund data, computes momentum, and reports.",
        formatter_class=argparse.RawTextHelpFormatter # Preserves formatting in help text
    )
    parser.add_argument(
        "--email",
        action="store_true", # Sets to True if flag is present
        help="Output the report as a full HTML document to STDOUT (for external email sending).\n"
             "If not set, Markdown tables are printed to STDOUT."
    )
    parser.add_argument(
        "--compare",
        type=str,
        default=None, # Default is no comparison
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

    # Initialize DataFrames
    raw_prices_df = pd.DataFrame()
    processed_prices_df = pd.DataFrame()
    actual_fund_bundles: Dict[str, List[str]] = {}

    print("Fetching YAML bundle data...", file=sys.stderr)
    try:
        fund_name_bundles_yaml_txt = fetch_data(YAML_URL, expected_encoding=YAML_ENCODING)
    except Exception as e:
        print(f"Critical error: Failed to fetch YAML bundle data: {e}. Cannot proceed without fund names.", file=sys.stderr)
        sys.exit(1) # Exit if YAML fetching fails

    print("Parsing fund name bundles from YAML...", file=sys.stderr)
    try:
        fund_bundles_from_yaml = yaml.safe_load(fund_name_bundles_yaml_txt)
        if not isinstance(fund_bundles_from_yaml, dict):
            raise ValueError("YAML content did not parse into a dictionary.")

        # Try to find the fund bundles within the YAML structure
        temp_actual_fund_bundles: Dict[str, List[str]] | None = None
        if 'fund_names' in fund_bundles_from_yaml and isinstance(fund_bundles_from_yaml['fund_names'], dict):
            temp_actual_fund_bundles = fund_bundles_from_yaml['fund_names']
            print("Info: Extracted bundles from 'fund_names' key in YAML.", file=sys.stderr)
        else: # Fallback: iterate through top-level keys to find a suitable dictionary of bundles
            for key, value in fund_bundles_from_yaml.items():
                if isinstance(value, dict):
                    # Check if this dictionary looks like a bundle map (values are lists)
                    is_bundle_dict = all(isinstance(sub_value, list) for sub_value in value.values()) if value else False
                    if is_bundle_dict:
                        print(f"Info: Using bundles from YAML key '{key}'.", file=sys.stderr)
                        temp_actual_fund_bundles = value
                        break # Found a suitable bundle map

        if temp_actual_fund_bundles is not None:
            actual_fund_bundles = temp_actual_fund_bundles
        else:
            raise ValueError("Could not find fund name bundles in YAML. Check for 'fund_names' key or a top-level dictionary where values are lists of fund aliases.")

    except Exception as e:
        print(f"Critical error during parsing of YAML: {e}. Aborting.", file=sys.stderr)
        sys.exit(1) # Exit if YAML parsing fails


    print("Loading and parsing individual CSV files from tables directory...", file=sys.stderr)
    try:
        raw_prices_df = load_and_parse_individual_csv_files(DEFAULT_TABLES_DIR)
        if raw_prices_df.empty:
            # This is a warning, script can proceed but tables will likely be empty.
            print("Warning: Parsed raw prices DataFrame is empty after processing all CSVs.", file=sys.stderr)
    except Exception as e:
        print(f"Error during loading/parsing of CSV files: {e}. Report will show limited/no data.", file=sys.stderr)
        raw_prices_df = pd.DataFrame() # Ensure it's an empty DataFrame on error


    print("Bundling fund columns...", file=sys.stderr)
    try:
        processed_prices_df = bundle_funds(raw_prices_df, actual_fund_bundles)
        if processed_prices_df.empty and not raw_prices_df.empty and actual_fund_bundles :
             print("Warning: Prices DataFrame is empty after bundling funds. This might be due to no matching fund names between CSVs and YAML.", file=sys.stderr)
    except Exception as e:
        print(f"Error during fund bundling: {e}. Proceeding with unbundled or empty data for report.", file=sys.stderr)
        # Fallback to raw_prices_df if bundling fails, or empty if raw_prices_df is also problematic
        processed_prices_df = raw_prices_df if raw_prices_df is not None else pd.DataFrame()


    print("Computing momentum tables...", file=sys.stderr)
    # Initialize with empty DataFrames having correct columns for graceful failure
    empty_display_df = pd.DataFrame(columns=DISPLAY_COLUMNS)
    long_term_top_df = empty_display_df.copy()
    lag_adj_top_df = empty_display_df.copy()
    full_perf_df = pd.DataFrame(columns=DISPLAY_COLUMNS + ['LongTermAdjustedPerf', 'LagAdjScore']) # Include score cols

    try:
        long_term_top_df, lag_adj_top_df, full_perf_df = compute_momentum_tables(processed_prices_df)
    except Exception as e:
        print(f"Error computing momentum tables: {e}. Report will show no data for tables.", file=sys.stderr)
        # Already initialized to empty display DFs

    # --- Overlap Funds Logic ---
    md_overlap_table = ""
    html_overlap_table = ""
    overlap_funds_df = pd.DataFrame(columns=DISPLAY_COLUMNS) # Initialize empty with correct columns

    if not long_term_top_df.empty and not lag_adj_top_df.empty and "Fund" in full_perf_df.columns:
        long_term_fund_names = set(long_term_top_df['Fund'])
        lag_adj_fund_names = set(lag_adj_top_df['Fund'])
        common_fund_names = list(long_term_fund_names.intersection(lag_adj_fund_names))

        if common_fund_names:
            overlap_funds_df = full_perf_df[full_perf_df['Fund'].isin(common_fund_names)].copy()
            if not overlap_funds_df.empty:
                # Sort by LongTermAdjustedPerf by default for overlap, then add Rank
                if 'LongTermAdjustedPerf' in overlap_funds_df.columns:
                    overlap_funds_df.sort_values("LongTermAdjustedPerf", ascending=False, inplace=True)
                overlap_funds_df.insert(0, 'Rank', range(1, len(overlap_funds_df) + 1))

            md_overlap_table = df_to_markdown_table(overlap_funds_df) # Will use DISPLAY_COLUMNS
            html_overlap_table = df_to_html_table_styled(overlap_funds_df, "overlapFundTable")
    # --- End Overlap Funds Logic ---


    # --- Comparison Funds Logic ---
    md_comparison_table = ""
    html_comparison_table = ""
    comparison_funds_perf_df = pd.DataFrame(columns=DISPLAY_COLUMNS) # Initialize empty

    if args.compare:
        print(f"Processing comparison funds: {args.compare}", file=sys.stderr)
        # Use csv module to handle commas within quoted fund names
        f = StringIO(args.compare)
        reader = csv.reader(f, skipinitialspace=True)
        try:
            requested_fund_names = next(reader) # Parses the single line of comma-separated names
        except StopIteration: # Handle empty string for --compare
            requested_fund_names = []

        if requested_fund_names:
            if "Fund" in full_perf_df.columns:
                # Filter full_perf_df for the requested funds
                comparison_funds_perf_df = full_perf_df[full_perf_df['Fund'].isin(requested_fund_names)].copy()

            if not comparison_funds_perf_df.empty:
                # Add Rank based on current order (which is from full_perf_df, typically sorted by Fund name implicitly or by index)
                # Or, could sort them here by a specific metric if desired before ranking.
                # For now, rank reflects the order they appear from full_perf_df filter.
                if 'LongTermAdjustedPerf' in comparison_funds_perf_df.columns: # Optional: sort by a metric
                     comparison_funds_perf_df.sort_values("LongTermAdjustedPerf", ascending=False, inplace=True)
                comparison_funds_perf_df.insert(0, 'Rank', range(1, len(comparison_funds_perf_df) + 1))

                found_funds = comparison_funds_perf_df['Fund'].tolist()
                missing_funds = [name for name in requested_fund_names if name not in found_funds]
                if missing_funds:
                    print(f"Warning: Could not find data for the following comparison funds: {missing_funds}", file=sys.stderr)
            else:
                print(f"Warning: None of the requested comparison funds were found or had data: {requested_fund_names}", file=sys.stderr)

            md_comparison_table = df_to_markdown_table(comparison_funds_perf_df)
            html_comparison_table = df_to_html_table_styled(comparison_funds_perf_df, "comparisonFundTable")
        else:
            print("Warning: --compare flag used but no fund names were provided or parsed.", file=sys.stderr)
    # --- End Comparison Funds Logic ---


    print("Generating HTML and Markdown table outputs...", file=sys.stderr)
    html_long_term_table = df_to_html_table_styled(long_term_top_df, "longTermGrowthTable")
    html_lag_adj_table = df_to_html_table_styled(lag_adj_top_df, "lagAdjustedShortTermTable")
    md_long_term_table = df_to_markdown_table(long_term_top_df)
    md_lag_adj_table = df_to_markdown_table(lag_adj_top_df)

    if args.email:
        # Construct the full HTML body for STDOUT
        html_email_body = f"""
        <!DOCTYPE html><html lang="en"><head><meta http-equiv="Content-Type" content="text/html; charset=UTF-8"><title>{final_email_subject}</title>
        <style type="text/css">
            body {{font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 15px; padding: 0; background-color: #f4f7f6; color: #333333; line-height: 1.6;}}
            .email-container {{max-width: 700px; margin: 0 auto; background-color: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.05);}}
            h1 {{color: #2c3e50; font-size: 22px; border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-top: 0;}}
            h1 a.header-link {{color: inherit; text-decoration: none;}}
            h1 a.header-link:hover {{text-decoration: underline;}}
            h2 {{color: #3498db; font-size: 18px; margin-top: 25px; margin-bottom: 10px; border-bottom: 1px solid #e0e0e0; padding-bottom: 5px;}}
            .table-wrapper {{ margin-bottom: 20px; overflow-x: auto; }} /* Allow horizontal scroll on small screens for tables */
            .fund-table {{border-collapse: collapse; width: 100%; min-width: 600px; /* Min width to prevent excessive squashing */ margin: 0 0 5px 0; font-size: 0.9em; border-radius: 5px; overflow: hidden; box-shadow: 0 0 10px rgba(0,0,0,0.05); border: 1px solid #dddddd;}}
            .fund-table th, .fund-table td {{padding: 10px 12px; border-bottom: 1px solid #dddddd; text-align: right; white-space: nowrap; /* Prevent text wrapping in cells */}}
            .fund-table th {{background-color: #3498db; color: #ffffff; text-align: left; font-weight: bold; border-bottom-width: 2px; cursor: pointer; position: relative;}}
            .fund-table th .sort-arrow {{ margin-left: 5px; font-size: 0.8em; }}
            .fund-table td:first-child, .fund-table th:first-child {{text-align: left; /* Rank and Fund columns left-aligned */}}
            .fund-table td:nth-child(2) {{text-align: left; font-weight: 500; /* Fund name column */}}
            .fund-table tbody tr:nth-of-type(even) {{background-color: #f8f9fa;}}
            .fund-table tbody tr:hover {{background-color: #e9ecef;}}
            .fund-table tbody tr:last-child td {{border-bottom: none;}}
            .copy-button-container {{ text-align: right; margin-bottom: 10px; }}
            .copy-button-container button {{ background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 4px; padding: 5px 10px; cursor: pointer; font-size: 0.8em; color: #333; }}
            .copy-button-container button:hover {{ background-color: #e0e0e0; }}
            .copy-button-container button svg {{ vertical-align: middle; margin-right: 4px; }}
            .copy-feedback {{ margin-left: 10px; font-size: 0.8em; color: green; font-style: italic; }}
            .footer {{margin-top: 30px; padding-top: 15px; border-top: 1px solid #e0e0e0; font-size: 0.85em; color: #767676; text-align: center;}}
            .footer p {{margin: 5px 0;}}
        </style>
        <script>
          function copyTableAsCsv(tableId, feedbackId) {{
            const table = document.getElementById(tableId);
            const feedback = document.getElementById(feedbackId);
            if (!table) {{
              console.error("Table not found for ID:", tableId);
              if(feedback) feedback.textContent = "Error: Table not found!";
              return;
            }}
            let csv = [];
            // Process header row
            const headerRow = table.querySelector('thead tr');
            if (headerRow) {{
                let row = [];
                const cols = headerRow.querySelectorAll("th");
                for (let j = 0; j < cols.length; j++) {{
                    // Get text content, remove sort arrow if present
                    let cellText = cols[j].textContent.replace(/\\s*(?:↑|↓|▲|▼)$/, '').trim();
                    if (cellText.includes(',')) {{
                        cellText = '"' + cellText.replace(/"/g, '""') + '"';
                    }}
                    row.push(cellText);
                }}
                csv.push(row.join(","));
            }}
            // Process body rows
            const bodyRows = table.querySelectorAll('tbody tr');
            bodyRows.forEach(tableRow => {{
                // Skip row if it's the "No data available" message
                if (tableRow.cells.length === 1 && tableRow.cells[0].hasAttribute('colspan')) {{
                    return;
                }}
                let row = [];
                const cols = tableRow.querySelectorAll("td");
                for (let j = 0; j < cols.length; j++) {{
                    let cellText = cols[j].innerText.trim();
                    if (cellText.includes(',')) {{
                        cellText = '"' + cellText.replace(/"/g, '""') + '"';
                    }}
                    row.push(cellText);
                }}
                csv.push(row.join(","));
            }});
            const csvString = csv.join("\\n");

            const textarea = document.createElement("textarea");
            textarea.value = csvString;
            textarea.style.position = "fixed"; document.body.appendChild(textarea);
            textarea.focus(); textarea.select();
            try {{
              const successful = document.execCommand('copy');
              if (successful) {{ if(feedback) feedback.textContent = "Copied!"; }}
              else {{ if(feedback) feedback.textContent = "Copy failed."; console.error("Fallback: Copying failed"); }}
            }} catch (err) {{
              if(feedback) feedback.textContent = "Copy error!"; console.error("Fallback: Error copying text: ", err);
            }}
            document.body.removeChild(textarea);
            if(feedback) {{ setTimeout(() => {{ feedback.textContent = ""; }}, 2000); }}
          }}

          let sortDirections = {{}}; // Stores {{ 'tableId-columnIndex': 'asc'/'desc' }}

          function sortTable(table, columnIndex) {{
            const tableId = table.id;
            const columnKey = `${{tableId}}-${{columnIndex}}`;
            const tbody = table.querySelector('tbody');
            const rowsArray = Array.from(tbody.querySelectorAll('tr'));

            // Skip if only one row or it's the "no data" row
            if (rowsArray.length <= 1 && rowsArray[0]?.cells[0]?.hasAttribute('colspan')) {{
                return;
            }}


            const headerCell = table.querySelectorAll('th')[columnIndex];
            const headerTextClean = headerCell.textContent.replace(/\\s*(?:↑|↓|▲|▼)$/, '').trim();

            let isNumericSort = true;
            let isPercent = false;

            if (headerTextClean === 'Fund') {{ isNumericSort = false; }}
            else if (['{TWO_WEEK_LOOKBACK_KEY}', '{ONE_MONTH_LOOKBACK_KEY}', '{TWO_MONTH_LOOKBACK_KEY}', '{THREE_MONTH_LOOKBACK_KEY}', '{SIX_MONTH_LOOKBACK_KEY}', '{ONE_YEAR_LOOKBACK_KEY}', '{ALL_DATES_KEY}'].includes(headerTextClean)) {{ isPercent = true; }}
            else if (headerTextClean === 'Rank') {{ isPercent = false; /* Numeric, not percent */ }}

            let currentDirection = sortDirections[columnKey] || 'asc';
            if (table.dataset.lastSortColumn === String(columnIndex)) {{
                currentDirection = currentDirection === 'asc' ? 'desc' : 'asc';
            }} else {{
                currentDirection = 'asc';
            }}
            sortDirections[columnKey] = currentDirection;
            table.dataset.lastSortColumn = String(columnIndex);

            table.querySelectorAll('.sort-arrow').forEach(arrow => arrow.textContent = '');
            const arrowElement = headerCell.querySelector('.sort-arrow');
            if (arrowElement) {{
                arrowElement.textContent = currentDirection === 'asc' ? ' ▲' : ' ▼';
            }}

            rowsArray.sort((a, b) => {{
                let valA_text = a.cells[columnIndex]?.textContent.trim() || "";
                let valB_text = b.cells[columnIndex]?.textContent.trim() || "";
                let valA, valB;

                if (isNumericSort) {{
                    valA_text = valA_text.replace(/,/g, ''); // Remove thousands separators for parsing
                    valB_text = valB_text.replace(/,/g, '');

                    if (isPercent) {{
                        valA = parseFloat(valA_text.replace('%', ''));
                        valB = parseFloat(valB_text.replace('%', ''));
                    }} else {{ // For Rank or other direct numeric
                        valA = parseFloat(valA_text);
                        valB = parseFloat(valB_text);
                    }}
                    if (valA_text === "N/A" || isNaN(valA)) valA = (currentDirection === 'asc' ? Infinity : -Infinity);
                    if (valB_text === "N/A" || isNaN(valB)) valB = (currentDirection === 'asc' ? Infinity : -Infinity);
                }} else {{ // Text sort for 'Fund'
                    valA = valA_text.toLowerCase();
                    valB = valB_text.toLowerCase();
                }}

                if (valA < valB) return currentDirection === 'asc' ? -1 : 1;
                if (valA > valB) return currentDirection === 'asc' ? 1 : -1;
                return 0;
            }});

            tbody.innerHTML = ''; // Clear existing rows
            rowsArray.forEach(row => tbody.appendChild(row)); // Append sorted rows
          }}

          function makeTablesSortable() {{
            document.querySelectorAll('.fund-table').forEach(table => {{
                const headers = table.querySelectorAll('th');
                headers.forEach((header, index) => {{
                    if (!header.querySelector('.sort-arrow')) {{ // Add arrow span only if not present
                        const arrowSpan = document.createElement('span');
                        arrowSpan.className = 'sort-arrow';
                        header.appendChild(arrowSpan);
                    }}
                    header.addEventListener('click', () => {{
                        sortTable(table, index);
                    }});
                }});
            }});
          }}
          window.addEventListener('DOMContentLoaded', makeTablesSortable);
        </script>
        </head><body><div class="email-container">
        <h1><a href="https://famantic-net.github.io/fundrider-pages/" class="header-link">{final_email_subject}</a></h1>
        """
        if html_overlap_table: # Check if there's content to display
             html_email_body += f"""<h2>Funds Appearing in Both Top 20 Assessments</h2>{html_overlap_table}"""

        html_email_body += f"""
        <h2>Best Long-Term Growth Assessment (Top 20)</h2>{html_long_term_table}
        <h2>Best Lag-Adjusted Short-Term Assessment (Top 20)</h2>{html_lag_adj_table}
        """
        if html_comparison_table: # Check if there's content for comparison table
            html_email_body += f"""<h2>Comparison Funds Performance</h2>{html_comparison_table}"""

        html_email_body += f"""
        <div class="footer"><p>This report was generated automatically by the Fund Momentum Emailer script.</p>
        <p>Fund data is typically lagged by several days. Performance figures are historical.</p>
        <p>Always do your own research before making investment decisions.</p></div></div></body></html>
        """
        print(html_email_body, file=sys.stdout) # Print the complete HTML to STDOUT
    else:
        # Output Markdown to STDOUT if --email is not used
        print("\n--- Email sending skipped (--email flag not provided) ---", file=sys.stderr)
        if md_overlap_table:
            print("\n### Funds Appearing in Both Top 20 Assessments\n", file=sys.stdout)
            print(md_overlap_table, file=sys.stdout)

        print(f"\n### Best Long-Term Growth Assessment (Top 20) - {current_date_utc_str}\n", file=sys.stdout)
        print(md_long_term_table, file=sys.stdout)
        print(f"\n### Best Lag-Adjusted Short-Term Assessment (Top 20) - {current_date_utc_str}\n", file=sys.stdout)
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
    except SystemExit: # Allow sys.exit() to propagate for controlled exits
        raise
    except Exception as e: # Catch any other unexpected errors in main execution
        print(f"An unexpected critical error occurred in the main execution block: {e}", file=sys.stderr)
        print("Traceback:", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr) # Print full traceback
        sys.exit(1) # Exit with error status
