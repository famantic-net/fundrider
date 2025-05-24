import os
import re
import sys
import argparse
import json
import numpy as np
import pandas as pd
import plotly.graph_objs as go

# Parse command-line arguments
parser = argparse.ArgumentParser(
    description='Generate fund series charts from CSVs; supports time-series, bar-score mode, and stdin.'
)
parser.add_argument(
    '-t', dest='input_dir', default='.',
    help='Directory containing fund_tables_<n>.csv'
)
parser.add_argument(
    '-r', dest='output_dir', default='.',
    help='Directory to save HTML or ":internal:" to output HTML to stdout'
)
parser.add_argument(
    '--bar', dest='bar_mode', action='store_true',
    help='Generate performance bar chart instead of time-series'
)
parser.add_argument(
    '--trace', dest='trace_mode', action='store_true',
    help='Enable diagnostic trace messages to STDERR for bar chart mode calculations.'
)
args = parser.parse_args()

# Determine modes
internal_only = (args.output_dir == ':internal:')
use_stdin = (args.input_dir == '.' and not sys.stdin.isatty())
if not internal_only and not use_stdin:
    os.makedirs(args.output_dir, exist_ok=True)

# Common pandas CSV options
# Changed dayfirst to False to match common YYYY-MM-DD date format and avoid warnings
df_kwargs = dict(
    sep=';', decimal=',', skiprows=2, header=0,
    parse_dates=[0], dayfirst=False, na_values=[''], encoding='latin1'
)

# JS snippet for hover interactions (for time-series charts)
hover_js = '''<script>
(function() {
  document.querySelectorAll('.plotly-graph-div').forEach(function(gd) {
    // Trace hover
    gd.on('plotly_hover', function(data) {
      var ci = data.points[0].curveNumber;
      // Bold legend entry by index
      var legendTexts = gd.querySelectorAll('.legendtext');
      if (gd.data[ci] && legendTexts.length > ci) {
        var traceName = gd.data[ci].name; // Get name from trace data
        // Attempt to bold by matching name, then fall back to index if needed
        var foundMatchByName = false;
        legendTexts.forEach(el => {
          if(el.textContent.startsWith(traceName.split('<br>')[0])) { // Match primary name part if <br> is used
            el.style.fontWeight='bold';
            foundMatchByName = true;
          }
        });
        if (!foundMatchByName && legendTexts[ci]) {
             legendTexts[ci].style.fontWeight = 'bold';
        }
      } else if (legendTexts.length > ci && legendTexts[ci]) {
        legendTexts[ci].style.fontWeight = 'bold'; // Fallback if gd.data[ci] is undefined
      }
      // Thicken hovered line
      Plotly.restyle(gd, {'line.width':3}, [ci]);
    });
    gd.on('plotly_unhover', function() {
      // Reset legend text
      var texts = gd.querySelectorAll('.legendtext');
      texts.forEach(el => el.style.fontWeight = 'normal');
      // Reset all lines
      Plotly.restyle(gd, {'line.width':2}, Array.from({length:gd.data.length}, (_,j) => j));
    });
    // Legend hover
    function bindLegendHover() {
      var texts = gd.querySelectorAll('.legendtext');
      texts.forEach(function(el, i) {
        el.onmouseenter = function() {
          el.style.fontWeight = 'bold';
          Plotly.restyle(gd, {'line.width':3}, [i]);
        };
        el.onmouseleave = function() {
          el.style.fontWeight = 'normal';
          Plotly.restyle(gd, {'line.width':2}, Array.from({length:gd.data.length}, (_,j) => j));
        };
      });
    }
    gd.on('plotly_afterplot', bindLegendHover);
    gd.on('plotly_legendclick', function() { setTimeout(bindLegendHover, 0); });
  });
})();
</script>'''

# Helper: build HTML for time-series chart
def df_to_html(df, title=None, last_dates=None):
    num_series = len(df.columns) - 1 if 'Date' in df.columns else len(df.columns)
    base_h = max(500, num_series*25 + 100)
    height_px = int(base_h * 1.5)
    fig = go.Figure()
    for col in df.columns:
        if col=='Date': continue
        name = col
        if last_dates and col in last_dates:
            name = f"{col}<br>{last_dates[col]}"
        # Ensure data is numeric
        series_data = pd.to_numeric(df[col], errors='coerce')

        custom_hover_data = 10 ** series_data * 100

        fig.add_trace(go.Scatter(
            x=df['Date'], y=series_data, mode='lines', name=name, customdata=custom_hover_data,
            line=dict(width=2), hovertemplate=(
                '<b>Series:</b> %{fullData.name}<br>'
                '<b>Date:</b> %{x|%Y-%m-%d}<br>'
                '<b>Value (log10):</b> %{y:.3f}<br>'
                '<b>Relative Change:</b> %{customdata:.1f}%<extra></extra>'
            )
        ))
    layout = dict(hovermode='closest', template='plotly_white', height=height_px,
                  yaxis=dict(zeroline=True, zerolinewidth=3, title='Normalized Value (log10 scale, 0 = Last Date)'),
                  xaxis=dict(title='Date'),
                  legend=dict(traceorder='normal'))
    if title: layout['title'] = dict(text=title, x=0.5, xanchor='center')
    fig.update_layout(**layout)

    # Use a specific version of Plotly.js
    plotly_cdn_script = '<script src="https://cdn.plot.ly/plotly-3.0.1.min.js"></script>'

    # Get the chart div and the newPlot script from Plotly
    chart_div_and_script = fig.to_html(include_plotlyjs=False, full_html=False)

    # Construct the full HTML page manually
    html_output = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title if title else 'Fund Series Chart'}</title>
    {plotly_cdn_script}
</head>
<body>
    {chart_div_and_script}
    {hover_js}
</body>
</html>"""
    return html_output

# Bar-chart mode function
def bar_chart_mode(input_dir, output_dir, internal, trace_enabled):
    # Imports are repeated here to make the function potentially more self-contained
    # if it were to be moved or used independently, though not strictly necessary
    # given the global imports.
    import os, re, json, numpy as np, pandas as pd, plotly.graph_objs as go

    py_windows = [5, 10, 21, 64, 129, 261, 390, 522]
    py_init_weights = [0.3, 1.5, 2.5, 4, 3, 2, 1.5, 1]
    py_period_label_map = {
        5: 'Week', 10: 'Fortnight', 21: 'Month', 64: 'Quarter',
        129: 'Half year', 261: 'Year', 390: '1.5 years', 522: '2 years'
    }

    num_gradient_lookback_days = 10 # Static gradient lookback period for Python pre-calculation

    # --- Helper function to calculate window contributions (Python version) ---
    def get_window_contributions_py(ys_series, current_windows, fund_name_for_trace, context_label_for_trace):
        pct_contributions = []
        if not isinstance(ys_series, np.ndarray):
            ys_series = np.array(ys_series)

        for w_idx, w_val in enumerate(current_windows):
            if trace_enabled and context_label_for_trace:
                print(f"PY_TRACE_CONTRIB: Fund: {fund_name_for_trace}, Context: {context_label_for_trace}, Window: {w_val}d - Series len: {len(ys_series)}", file=sys.stderr)

            if len(ys_series) < w_val:
                pct_contributions.append(0.0)
            else:
                # Fit a line to the last w_val points of the series
                m, _ = np.polyfit(np.arange(w_val), ys_series[-w_val:], 1)
                # Calculate raw contribution: slope * (number of points - 1) * 100
                # This represents the total change over the window if the trend continued linearly.
                raw_contrib = m * (w_val - 1) * 100

                contrib = 0.0
                if not np.isfinite(raw_contrib):
                    contrib = 0.0
                    if trace_enabled:
                        print(f"PY_TRACE_CONTRIB_CLEAN: Fund: {fund_name_for_trace}, Context: {context_label_for_trace}, Window: {w_val}d - Slope(m): {m:.6f} non-finite raw_contrib ({raw_contrib}). Contrib set to 0.0", file=sys.stderr)
                else:
                    contrib = raw_contrib
                pct_contributions.append(contrib)
        return pct_contributions
    # --- End Python Helper function ---

    pat = re.compile(r'fund_tables_(\d+)\.csv$')
    all_funds_raw_log_series = {}

    if trace_enabled: print(f"TRACE: Starting data aggregation from input directory: {input_dir}", file=sys.stderr)
    if not os.path.isdir(input_dir):
        print(f"Error: Input directory '{input_dir}' not found.", file=sys.stderr)
        sys.exit(1)

    # Aggregate data from all matching CSV files
    for fname in sorted(f for f in os.listdir(input_dir) if pat.match(f)):
        if trace_enabled: print(f"TRACE: Processing file: {fname}", file=sys.stderr)
        try:
            df_temp = pd.read_csv(os.path.join(input_dir, fname), **df_kwargs)
            if df_temp.empty:
                if trace_enabled: print(f"TRACE: File: {fname} - CSV empty or no data after skiprows. Skipping.", file=sys.stderr)
                continue

            for col_name_raw in df_temp.columns:
                col_name = str(col_name_raw).strip()
                # Skip date columns, unnamed columns, or empty column names
                if (col_name.lower() in ['date', 'datum', '#'] or \
                    col_name.startswith('Unnamed:') or \
                    not col_name):
                    if trace_enabled:
                        print(f"TRACE_AGGREGATION: File: {fname}, Column: '{col_name_raw}' (stripped: '{col_name}') - Skipping (date/unnamed/placeholder/empty).", file=sys.stderr)
                    continue

                current_ys = pd.to_numeric(df_temp[col_name_raw], errors='coerce').dropna().values
                if len(current_ys) > 0:
                    all_funds_raw_log_series[col_name] = current_ys # Store the raw log series
                    if trace_enabled: print(f"TRACE_AGGREGATION: Fund: {col_name} from {fname} - Stored/Updated raw log series. Length: {len(current_ys)}", file=sys.stderr)
                elif trace_enabled:
                    print(f"TRACE_AGGREGATION: Fund: {col_name} from {fname} - No numeric data after cleaning. Skipping fund series.", file=sys.stderr)
        except Exception as e:
            if trace_enabled: print(f"TRACE: File: {fname} - Error during processing: {e}", file=sys.stderr)
            print(f"Error processing file {fname}: {e}", file=sys.stderr)
            continue

    if not all_funds_raw_log_series:
        if trace_enabled: print(f"TRACE: No valid fund data collected from any CSVs in {input_dir}. Exiting bar chart mode.", file=sys.stderr)
        print(f"No valid fund data collected from {input_dir}. Exiting bar chart mode.", file=sys.stderr)
        return

    if trace_enabled: print(f"TRACE: Data aggregation complete. Total unique funds found: {len(all_funds_raw_log_series)}", file=sys.stderr)

    sorted_fund_names = sorted(all_funds_raw_log_series.keys())
    if trace_enabled: print(f"TRACE: Fund names sorted alphabetically for processing.", file=sys.stderr)

    output_fund_names = [] # Fund names for the final output (Plotly chart x-axis)
    main_score_contributions_list_for_js = [] # List of [contrib_w1, contrib_w2, ...] for each fund for JS
    initial_scores_list_py = [] # Calculated initial scores (Python side)
    initial_gradients_list_py = [] # Calculated initial gradients (Python side)
    historical_contributions_for_all_funds_js = {} # Dict: {fund_name: [[hist_contribs_d0], [hist_contribs_d1]...]} for JS

    smallest_window_size = py_windows[0] if py_windows else 5
    # Minimum total length required for a series to calculate gradient over the lookback period
    min_total_length_for_gradient = smallest_window_size + (num_gradient_lookback_days - 1)


    # Process each fund
    for fund_idx, fund_name in enumerate(sorted_fund_names):
        original_ys = all_funds_raw_log_series[fund_name]
        if trace_enabled: print(f"TRACE: Fund: {fund_name} (Sorted Index: {fund_idx}) - Processing for initial scores and historical contributions.", file=sys.stderr)
        output_fund_names.append(fund_name)

        # Calculate main contributions for the current (latest) data point for JS
        main_contributions_py = get_window_contributions_py(original_ys, py_windows, fund_name, "MAIN_CONTRIBS_FOR_JS")
        main_score_contributions_list_for_js.append(main_contributions_py)

        # Calculate initial main score using Python-defined weights
        initial_main_score_py = sum(p * wt for p, wt in zip(main_contributions_py, py_init_weights))
        if not np.isfinite(initial_main_score_py): initial_main_score_py = 0.0 # Handle NaN/Inf
        initial_scores_list_py.append(initial_main_score_py)

        if trace_enabled:
            print(f"TRACE_MAIN_SCORE: Fund: {fund_name} - Main Contributions: {[round(p,2) for p in main_contributions_py]}, Initial Main Score (default weights): {initial_main_score_py:.2f}", file=sys.stderr)

        # Pre-calculate historical contributions for JS gradient calculation
        fund_historical_contrib_sets_for_js = []
        if len(original_ys) < min_total_length_for_gradient:
            if trace_enabled: print(f"TRACE_GRADIENT_PRECALC_JS: Fund: {fund_name} - Series too short for historical contribs. Will use zeros.", file=sys.stderr)
            # Fill with zeros if series is too short
            for _ in range(num_gradient_lookback_days):
                fund_historical_contrib_sets_for_js.append([0.0] * len(py_windows))
        else:
            # Calculate contributions for each of the past `num_gradient_lookback_days`
            for k in range(num_gradient_lookback_days):
                historical_end_index = len(original_ys) - k # Go back k days from the end
                historical_series_segment = original_ys[:historical_end_index]
                current_hist_contribs = [0.0] * len(py_windows) # Default to zeros
                if len(historical_series_segment) >= smallest_window_size:
                    # Renormalize historical segment to its own last point before calculating contributions
                    baseline_val = historical_series_segment[-1]
                    renormalized_historical_segment = historical_series_segment - baseline_val
                    current_hist_contribs = get_window_contributions_py(renormalized_historical_segment, py_windows, fund_name, f"HIST_CONTRIBS_FOR_JS_D-{k}")
                fund_historical_contrib_sets_for_js.append(current_hist_contribs)
        historical_contributions_for_all_funds_js[fund_name] = fund_historical_contrib_sets_for_js

        # Calculate initial gradient (Python side, for initial chart display)
        initial_historical_scores_for_gradient = []
        if len(original_ys) >= min_total_length_for_gradient:
            # Calculate historical scores based on the pre-calculated historical contributions
            for k_init_grad in range(num_gradient_lookback_days):
                hist_contribs_for_day = fund_historical_contrib_sets_for_js[k_init_grad] # Already calculated
                hist_score_for_day = sum(p_hist * wt_init for p_hist, wt_init in zip(hist_contribs_for_day, py_init_weights))
                initial_historical_scores_for_gradient.append(hist_score_for_day if np.isfinite(hist_score_for_day) else 0.0)

            valid_initial_hist_scores = [s for s in initial_historical_scores_for_gradient if np.isfinite(s)]
            if len(valid_initial_hist_scores) == num_gradient_lookback_days: # Ensure enough points for polyfit
                # Fit line to historical scores (reversed for correct time order) to get gradient
                initial_gradient_slope, _ = np.polyfit(np.arange(num_gradient_lookback_days), valid_initial_hist_scores[::-1], 1)
                initial_gradients_list_py.append(initial_gradient_slope)
            else:
                initial_gradients_list_py.append(np.nan) # Not enough data for gradient
        else:
            initial_gradients_list_py.append(np.nan) # Series too short for gradient

    # Clean up initial scores and gradients (replace non-finite with None for JSON)
    cleaned_initial_scores_py = []
    for score_val in initial_scores_list_py:
        cleaned_initial_scores_py.append(None if not np.isfinite(score_val) else score_val)
    initial_scores_list_py = cleaned_initial_scores_py # Use the cleaned list

    cleaned_initial_gradients_py = []
    for grad_val in initial_gradients_list_py:
        cleaned_initial_gradients_py.append(None if not np.isfinite(grad_val) else grad_val)
    # initial_gradients_list_py = cleaned_initial_gradients_py # Assign back the cleaned list

    # Prepare customdata for Plotly (initial gradients)
    custom_data_for_plot_py = []
    for i in range(len(output_fund_names)):
        grad_val = cleaned_initial_gradients_py[i] if i < len(cleaned_initial_gradients_py) else None
        custom_data_for_plot_py.append([grad_val]) # Plotly expects customdata as a list of lists


    # Create the initial bar chart figure
    fig = go.Figure(go.Bar(
        x=output_fund_names,
        y=initial_scores_list_py,
        customdata=custom_data_for_plot_py, # Store initial gradients here
        marker_color='steelblue',
        name='Fund Scores',
        hovertemplate=(
            '<b>Fund:</b> %{x}<br>'
            '<b>Score:</b> %{y:.2f}<br>'
            f'<b>Score Trend ({num_gradient_lookback_days}d):</b> %{{customdata[0]:.2f}}<extra></extra>'
        )
    ))
    fig.update_layout(
        title='Current fund performance', template='plotly_white', height=600,
        xaxis=dict(showticklabels=False, title='Funds (Scroll/Isolate to see names)'), # Hide x-axis labels initially
        yaxis=dict(title='Score', autorange=True, type='linear'), # Ensure y-axis autoranges
        barmode='group'
    )
    fig_dict = fig.to_dict()

    # Recursively clean NaN/Inf from the figure dictionary for valid JSON
    def clean_fig_dict_infs_nans(obj):
        if isinstance(obj, dict):
            return {k: clean_fig_dict_infs_nans(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean_fig_dict_infs_nans(elem) for elem in obj]
        elif isinstance(obj, float) and not np.isfinite(obj):
            return None # Replace non-finite floats with None
        return obj

    cleaned_fig_dict = clean_fig_dict_infs_nans(fig_dict)
    fig_json = json.dumps(cleaned_fig_dict) # Serialize to JSON for embedding in HTML

    # HTML body for the chart
    # Updated to use specific Plotly.js version
    body = (
        '<div id="bar-chart" style="width:100%; height:600px; margin-bottom:30px;"></div>'
        '<script src="https://cdn.plot.ly/plotly-3.0.1.min.js"></script>' # Include Plotly.js CDN
        f'<script>var figDataInit={fig_json};Plotly.newPlot("bar-chart",figDataInit.data,figDataInit.layout);</script>' # Initialize chart
    )

    # HTML for weight sliders
    slider_html = '<table style="margin:auto; width:90%; border-spacing: 5px;"><tr>'
    for i, w_days in enumerate(py_windows):
        period_name = py_period_label_map.get(w_days, f"{w_days}d")
        slider_html += (
            '<td style="text-align:center; padding:8px; vertical-align:top; border: 1px solid #ddd; border-radius: 5px; min-width:100px;">'
            f'<div>Window {w_days}d</div>'
            f'<div>{period_name}</div>'
            f'<div>Weight: <span id="v{i}" style="font-weight:bold;">{py_init_weights[i]:.1f}</span></div>'
            f'<div><input id="w{i}" data-index="{i}" class="weight-slider" type="range" min="0" max="10" step="0.1" '
            f'value="{py_init_weights[i]:.1f}" style="width:100%;"></div></td>'
        )
    slider_html += '</tr></table>'

    # HTML for fund isolation controls and dynamic table
    dropdown_funds_for_select = sorted(output_fund_names) # Ensure sorted for dropdown
    controls_and_table_html = (
        '<div style="display: flex; justify-content: space-around; margin: 20px 0; align-items: flex-start; flex-wrap: wrap;">'
        '  <div id="fund-isolation-controls" style="flex: 1; min-width: 320px; padding:10px;">' # Flex item for controls
        '    <h3 style="text-align:center; color:#555;">Isolate Funds</h3>'
        f'   <select id="fund-select" multiple size="{min(len(dropdown_funds_for_select), 10)}" ' # Multi-select dropdown
        '    style="width:100%; height:200px; overflow-y:auto; border: 1px solid #ccc; border-radius: 5px; padding: 5px;"></select><br/>'
        '    <div style="text-align:center; margin-top:10px;">'
        '      <button id="isolate" style="margin:5px; padding: 8px 15px; border-radius:5px; background-color:#4CAF50; color:white; border:none; cursor:pointer;">Isolate</button>'
        '      <button id="reset" style="margin:5px; padding: 8px 15px; border-radius:5px; background-color:#f44336; color:white; border:none; cursor:pointer;">Reset</button>'
        '    </div>'
        '  </div>'
        '  <div id="dynamic-fund-table-container" style="flex: 1.5; min-width: 400px; padding:10px;">' # Flex item for table
        '    <h3 style="text-align:center; color:#555;">Top Funds</h3>'
        '  </div>'
        '</div>'
    )

    # JavaScript data embedded in the HTML
    js_data_script = f"""
<script>
  const mainContributionsJS = {json.dumps(main_score_contributions_list_for_js)};
  const historicalContributionsDataJS = {json.dumps(historical_contributions_for_all_funds_js)};
  const pyInitialWeightsJS = {json.dumps(py_init_weights)};
  const allFundNamesJS = {json.dumps(output_fund_names)}; // Sorted list of all fund names
  const numGradientLookbackDaysJS = {json.dumps(num_gradient_lookback_days)};
  // initialGradientsFromPython is not explicitly used here anymore as JS recalculates gradients dynamically
</script>
"""

    # Main JavaScript logic for interactivity
    main_js_logic = """
<script>
  const weightSliders = Array.from(document.querySelectorAll('input.weight-slider'));
  let currentSortColumn = 'score'; // Default sort for the table
  let currentSortAscending = false; // Default sort order (descending for score)
  let currentlyIsolatedFundNames = null; // To store names of funds if isolated

  function calculateScore(contributions, weights) {
      if (!contributions || !Array.isArray(contributions)) return null;
      let scoreSum = 0;
      for (let i = 0; i < contributions.length; i++) {
          const perfPoint = typeof contributions[i] === 'number' ? contributions[i] : 0;
          scoreSum += perfPoint * weights[i];
      }
      return Number.isFinite(scoreSum) ? scoreSum : null;
  }

  function calculateSlope(y_values) {
      if (!y_values || y_values.length < 2) return null;
      const n = y_values.length;
      const x_values = Array.from({length: n}, (_, i) => i);

      let sum_x = 0, sum_y = 0, sum_xy = 0, sum_xx = 0;
      let validPoints = 0;
      for (let i = 0; i < n; i++) {
          if (typeof y_values[i] === 'number' && Number.isFinite(y_values[i])) {
              sum_x += x_values[i];
              sum_y += y_values[i];
              sum_xy += x_values[i] * y_values[i];
              sum_xx += x_values[i] * x_values[i];
              validPoints++;
          }
      }
      if (validPoints < 2) return null;

      const denominator = (validPoints * sum_xx - sum_x * sum_x);
      if (denominator === 0) return null; // Avoid division by zero
      const slope = (validPoints * sum_xy - sum_x * sum_y) / denominator;
      return Number.isFinite(slope) ? slope : null;
  }

  function renderDynamicTable(fundDataToDisplay) {
    const tableContainer = document.getElementById('dynamic-fund-table-container');
    const existingTitle = tableContainer.querySelector('h3'); // Preserve title
    tableContainer.innerHTML = ''; // Clear previous table
    if(existingTitle) tableContainer.appendChild(existingTitle); // Add title back


    if (!fundDataToDisplay || fundDataToDisplay.length === 0) {
        const p = document.createElement('p');
        p.textContent = 'No funds to display.';
        p.style.textAlign = 'center';
        tableContainer.appendChild(p);
        return;
    }

    // Sort data based on current settings
    fundDataToDisplay.sort((a, b) => {
        let valA = currentSortColumn === 'score' ? a.score : a.gradient;
        let valB = currentSortColumn === 'score' ? b.score : b.gradient;

        // Handle null or NaN values by pushing them to the end or beginning based on sort order
        valA = (valA === null || isNaN(valA)) ? (currentSortAscending ? Infinity : -Infinity) : valA;
        valB = (valB === null || isNaN(valB)) ? (currentSortAscending ? Infinity : -Infinity) : valB;

        if (valA < valB) return currentSortAscending ? -1 : 1;
        if (valA > valB) return currentSortAscending ? 1 : -1;
        return 0;
    });

    const top20Data = fundDataToDisplay.slice(0, 20); // Display top 20

    const table = document.createElement('table');
    table.style.width = '100%';
    table.style.borderCollapse = 'collapse';
    table.style.marginTop = '10px';

    const thead = table.createTHead();
    const headerRow = thead.insertRow();
    const headers = [
        {text: 'Fund Name', key: 'name'},
        {text: 'Fund Score', key: 'score'},
        {text: 'Fund Score Gradient (' + numGradientLookbackDaysJS + 'd)', key: 'gradient'}
    ];

    headers.forEach(headerInfo => {
        const th = document.createElement('th');
        th.textContent = headerInfo.text;
        th.style.border = '1px solid #ddd';
        th.style.padding = '8px';
        th.style.textAlign = 'left';
        th.style.backgroundColor = '#f0f0f0';
        th.style.fontWeight = 'bold';
        if (headerInfo.key === 'score' || headerInfo.key === 'gradient') {
            th.style.cursor = 'pointer';
            th.addEventListener('click', () => {
                if (currentSortColumn === headerInfo.key) {
                    currentSortAscending = !currentSortAscending;
                } else {
                    currentSortColumn = headerInfo.key;
                    currentSortAscending = false; // Default to descending when changing column
                }
                updateScoresAndGradients(); // Re-render with new sort
            });
            if (currentSortColumn === headerInfo.key) {
                th.style.fontStyle = 'italic'; // Indicate sorted column
                th.innerHTML += currentSortAscending ? ' &uarr;' : ' &darr;'; // Add sort arrow
            }
        }
        headerRow.appendChild(th);
    });

    const tbody = table.createTBody();
    top20Data.forEach(fund => {
        const row = tbody.insertRow();
        const cellName = row.insertCell();
        cellName.textContent = fund.name;
        cellName.style.border = '1px solid #ddd';
        cellName.style.padding = '8px';

        const cellScore = row.insertCell();
        cellScore.textContent = fund.score !== null && !isNaN(fund.score) ? fund.score.toFixed(2) : 'N/A';
        cellScore.style.border = '1px solid #ddd';
        cellScore.style.padding = '8px';
        cellScore.style.textAlign = 'right';

        const cellGradient = row.insertCell();
        cellGradient.textContent = fund.gradient !== null && !isNaN(fund.gradient) ? fund.gradient.toFixed(2) : 'N/A';
        cellGradient.style.border = '1px solid #ddd';
        cellGradient.style.padding = '8px';
        cellGradient.style.textAlign = 'right';
    });
    tableContainer.appendChild(table);
  }


  function updateScoresAndGradients(fundNamesToProcessARG = null) {
    const currentWeights = weightSliders.map(el => parseFloat(el.value));

    // Update weight display values
    currentWeights.forEach((val,i) => {
        const vElement = document.getElementById('v'+i);
        if (vElement) { vElement.textContent = val.toFixed(1); }
    });

    let newYScores = []; // Scores for the bar chart
    let newCustomData = []; // Gradients for the bar chart hover
    let tableDataPayload = []; // Data for the dynamic table [{name, score, gradient}, ...]

    // Determine which set of fund names to use for processing
    // If fundNamesToProcessARG is provided (isolation), use that.
    // Otherwise, use currentlyIsolatedFundNames if set, or allFundNamesJS as a fallback.
    let currentFundNamesForProcessing = fundNamesToProcessARG ? fundNamesToProcessARG : (currentlyIsolatedFundNames || allFundNamesJS);


    currentFundNamesForProcessing.forEach(fundName => {
        const originalIndex = allFundNamesJS.indexOf(fundName); // Find original index to get data
        if (originalIndex === -1) return; // Should not happen if data is consistent

        const fundMainContribs = mainContributionsJS[originalIndex];
        const mainScore = calculateScore(fundMainContribs, currentWeights);

        // Add to newYScores and newCustomData for the chart.
        // The chart's x-axis will be updated with currentFundNamesForProcessing.
        newYScores.push(mainScore);


        const fundHistContribSets = historicalContributionsDataJS[fundName];
        let historicalScoresForGradient = [];
        let gradient = null;

        if (fundHistContribSets && fundHistContribSets.length === numGradientLookbackDaysJS) {
            for (let i = 0; i < numGradientLookbackDaysJS; i++) {
                const histContribsForDay = fundHistContribSets[i];
                const histScoreForDay = calculateScore(histContribsForDay, currentWeights);
                historicalScoresForGradient.push(histScoreForDay);
            }
            // Calculate slope on reversed historical scores (oldest to newest)
            gradient = calculateSlope(historicalScoresForGradient.slice().reverse());
        }
        newCustomData.push([gradient]); // Plotly customdata format

        // Always add to tableDataPayload, the table rendering will decide what to show
        // based on whether it's an isolated view or full view.
        tableDataPayload.push({name: fundName, score: mainScore, gradient: gradient});
    });

    const updateData = {};
    // The x-axis of the chart should reflect the funds being displayed
    updateData.x = [currentFundNamesForProcessing];
    updateData.y = [newYScores];
    updateData.customdata = [newCustomData];

    Plotly.restyle('bar-chart', updateData, [0]); // Update the first trace of the bar chart

    // For the table, if we are in an isolated state (currentlyIsolatedFundNames is not null),
    // then tableDataPayload is already filtered.
    // If not isolated, we need to rebuild tableDataPayload for *all* funds to allow sorting the full list.
    if (!currentlyIsolatedFundNames) {
        tableDataPayload = []; // Recalculate for all funds if not isolated
        allFundNamesJS.forEach(fundName => {
            const originalIndex = allFundNamesJS.indexOf(fundName);
            const fundMainContribs = mainContributionsJS[originalIndex];
            const mainScore = calculateScore(fundMainContribs, currentWeights);

            const fundHistContribSets = historicalContributionsDataJS[fundName];
            let historicalScoresForGradient = [];
            let gradient = null;
            if (fundHistContribSets && fundHistContribSets.length === numGradientLookbackDaysJS) {
                for (let i = 0; i < numGradientLookbackDaysJS; i++) {
                    const histContribsForDay = fundHistContribSets[i];
                    const histScoreForDay = calculateScore(histContribsForDay, currentWeights);
                    historicalScoresForGradient.push(histScoreForDay);
                }
                gradient = calculateSlope(historicalScoresForGradient.slice().reverse());
            }
            tableDataPayload.push({name: fundName, score: mainScore, gradient: gradient});
        });
    }
    renderDynamicTable(tableDataPayload); // Render table with potentially filtered or full data
  }

  weightSliders.forEach(slider => {
    slider.addEventListener('input', () => updateScoresAndGradients());
    // Add mouse wheel support for sliders
    slider.addEventListener('wheel', function(event) {
      event.preventDefault(); // Prevent page scrolling
      const step = parseFloat(slider.step) || 0.1;
      let currentValue = parseFloat(slider.value);
      const minVal = parseFloat(slider.min) || 0;
      const maxVal = parseFloat(slider.max) || 10;

      if (event.deltaY < 0) { // Wheel up
        currentValue += step;
      } else { // Wheel down
        currentValue -= step;
      }
      currentValue = Math.max(minVal, Math.min(maxVal, currentValue)); // Clamp value
      slider.value = currentValue.toFixed(1); // Update slider and display
      updateScoresAndGradients(); // Recalculate and re-render
    });
  });

  // Initialize on DOM load
  document.addEventListener('DOMContentLoaded', () => {
    // Set initial slider values from Python data
    pyInitialWeightsJS.forEach((val, i) => {
        const slider = document.getElementById('w' + i);
        if (slider) { slider.value = val.toFixed(1); }
    });
    updateScoresAndGradients(); // Initial calculation and render
  });
</script>
"""

    # JavaScript for fund isolation functionality
    isolate_js = f"""
<script>
  const fundSelectElement_iso = document.getElementById('fund-select');
  const fundsForDropdownIsolate_iso = {json.dumps(dropdown_funds_for_select)}; // Already sorted

  // Populate the fund selection dropdown
  fundsForDropdownIsolate_iso.forEach(fundName => {{
    const optionElement = document.createElement('option');
    optionElement.value = fundName; optionElement.text = fundName;
    fundSelectElement_iso.appendChild(optionElement);
  }});

  document.getElementById('isolate').addEventListener('click', function() {{
    const selectedFundNames = Array.from(fundSelectElement_iso.selectedOptions).map(opt => opt.value);
    if (selectedFundNames.length === 0) {{
        // If selection is cleared, effectively a reset for the chart and table's content source
        currentlyIsolatedFundNames = null;
        updateScoresAndGradients(); // This will use allFundNamesJS for chart and table
        return;
    }}
    currentlyIsolatedFundNames = selectedFundNames; // Set global isolation state
    updateScoresAndGradients(selectedFundNames); // Pass selected names to update functions
  }});

  document.getElementById('reset').addEventListener('click', function() {{
    fundSelectElement_iso.selectedIndex = -1; // Clear selection in dropdown
    currentlyIsolatedFundNames = null; // Clear global isolation state
    updateScoresAndGradients(); // Update with all funds
  }});
</script>
"""

    # Construct the full HTML page
    full_html = (
        '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Fund Scores</title>'
        '<style>body {{ font-family: Arial, sans-serif; }} </style></head><body>'
        '<h1 style="text-align:center; color:#333;">Fund Performance Dashboard</h1>'
        '<h3 style="text-align:center; color:#555;">Adjust Scoring Weights</h3>'
        + slider_html
        + '<h3 style="text-align:center; margin-top:30px; color:#555;">Fund Scores Bar Chart</h3>'
        + body # Contains the Plotly chart div and its initialization script
        + controls_and_table_html # Contains isolation controls and table container
        + js_data_script # Contains data passed from Python to JS
        + main_js_logic # Contains core JS functions for updates and rendering
        + isolate_js # Contains JS for fund isolation
        + '</body></html>'
    )
    if internal:
        print(full_html)
    else:
        out = os.path.join(output_dir, 'fund_series_scores.html')
        with open(out, 'w', encoding='utf-8') as f:
            f.write(full_html)
        print(f"Saved score chart to {out}", file=sys.stderr)

# --- Main script execution logic starts here ---

# STDIN single time-series mode (if not --bar mode)
if use_stdin and not args.bar_mode:
    try:
        df0 = pd.read_csv(sys.stdin, **df_kwargs)
    except Exception as e:
        print(f"Error reading from stdin: {e}", file=sys.stderr)
        sys.exit(1)

    if df0.empty:
        print("Received empty or all-NA data from stdin after skiprows.", file=sys.stderr)
        sys.exit(1)

    df0.rename(columns={df0.columns[0]:'Date'}, inplace=True) # Assume first column is Date
    df0.dropna(axis=1, how='all', inplace=True) # Drop fully empty columns
    df0.dropna(subset=['Date'], how='all', inplace=True) # Drop rows where Date is NA
    if df0.empty:
        print("Data became empty after initial NA handling from stdin.", file=sys.stderr)
        sys.exit(1)
    df0.set_index('Date', inplace=True)

    df0 = df0.dropna(axis=1, how='all') # Drop columns that are entirely NA after setting index
    if df0.empty:
        print("No valid data series found after initial processing from stdin.", file=sys.stderr)
        sys.exit(1)

    # Get last valid dates for legend
    last_dates={c:df0[c].last_valid_index().strftime('%Y-%m-%d') for c in df0.columns if pd.notna(df0[c].last_valid_index())}

    if not df0.index.is_monotonic_increasing:
        df0 = df0.sort_index()

    df0.index = pd.to_datetime(df0.index, errors='coerce') # Convert index to datetime
    df0 = df0[pd.notna(df0.index)] # Remove rows with invalid dates

    if df0.empty:
        print("No valid dates found in stdin data after conversion.", file=sys.stderr)
        sys.exit(1)

    min_date, max_date = df0.index.min(), df0.index.max()
    if pd.isna(min_date) or pd.isna(max_date): # Check if date range is valid
        print("Could not determine a valid date range from stdin data.", file=sys.stderr)
        sys.exit(1)

    # Reindex to daily frequency and interpolate
    idx=pd.date_range(min_date, max_date, freq='D')
    df=df0.reindex(idx).interpolate(method='time').reset_index()
    if 'index' in df.columns and 'Date' not in df.columns: # Rename 'index' to 'Date' if necessary
        df.rename(columns={'index':'Date'}, inplace=True)

    # Final check for valid data columns after processing
    if 'Date' in df.columns:
        date_column_data = df['Date']
        other_columns_df = df.drop(columns=['Date'])
        cleaned_other_columns_df = other_columns_df.dropna(axis=1, how='all')
        df = pd.concat([date_column_data, cleaned_other_columns_df], axis=1)

        if len(df.columns) <= 1 : # Only Date column left or empty
            print("No valid data series to plot after interpolation and cleaning from stdin (only Date column).", file=sys.stderr)
            sys.exit(1)
    else:
        print("Critical: 'Date' column missing after processing stdin. Cannot proceed.", file=sys.stderr)
        sys.exit(1)

    html=df_to_html(df,title='Fund Series Chart (from stdin)',last_dates=last_dates)
    if internal_only:
        print(html)
    else:
        outf=os.path.join(args.output_dir,'fund_series_chart_stdin.html')
        with open(outf,'w',encoding='utf-8') as f: f.write(html)
        print(f"Saved {outf}",file=sys.stderr)
    sys.exit(0)

# Bar chart mode (if --bar is specified)
if args.bar_mode:
    if use_stdin:
        print("Bar mode cannot be used with stdin input. Please provide an input directory with -t.", file=sys.stderr)
        sys.exit(1)
    bar_chart_mode(args.input_dir, args.output_dir, internal_only, args.trace_mode)
    sys.exit(0)

# --- Default mode: Process multiple CSVs from a directory for time-series charts ---
pat=re.compile(r'fund_tables_(\d+)\.csv$') # Regex to find and extract number from filename
csv_files = []
if os.path.isdir(args.input_dir):
    csv_files = sorted(
        (int(m.group(1)), os.path.join(args.input_dir, f)) # Tuple of (number, filepath)
        for f in os.listdir(args.input_dir)
        for m in [pat.match(f)] if m # Ensure match and extract group
    )
else:
    # This condition should only be an error if not using stdin and not in bar_mode,
    # as those modes might not require a valid input_dir.
    if not (use_stdin or args.bar_mode):
        print(f"Error: Input directory '{args.input_dir}' not found or is not a directory.", file=sys.stderr)
        sys.exit(1)


if not csv_files and not (use_stdin or args.bar_mode): # No files found and not other modes
    print(f"No CSVs matching 'fund_tables_<n>.csv' found in {args.input_dir}", file=sys.stderr)
    sys.exit(1)

htmls=[] # List of generated HTML filenames (for index page)
internal_html={} # Dictionary for internal HTML content {idx_num: html_content}

for idx_num, filepath in csv_files: # Process each found CSV
    try:
        df0=pd.read_csv(filepath,**df_kwargs)
    except Exception as e:
        print(f"Error reading CSV file {filepath}: {e}", file=sys.stderr)
        continue # Skip to next file

    if df0.empty:
        print(f"Warning: CSV file {filepath} is empty or has no data after skiprows. Skipping.", file=sys.stderr)
        continue

    df0.rename(columns={df0.columns[0]:'Date'},inplace=True)
    df0.dropna(axis=1,how='all',inplace=True)
    df0.dropna(subset=['Date'], how='all', inplace=True)
    if df0.empty:
        print(f"Data became empty for {filepath} after initial NA handling.", file=sys.stderr)
        continue
    df0.set_index('Date',inplace=True)

    df0 = df0.dropna(axis=1, how='all')
    if df0.empty:
        print(f"No valid data series in {filepath} after initial processing.", file=sys.stderr)
        continue

    last_dates={c:df0[c].last_valid_index().strftime('%Y-%m-%d') for c in df0.columns if pd.notna(df0[c].last_valid_index())}

    if not df0.index.is_monotonic_increasing:
        df0 = df0.sort_index()

    df0.index = pd.to_datetime(df0.index, errors='coerce')
    df0 = df0[pd.notna(df0.index)] # Keep only valid dates

    if df0.empty:
        print(f"No valid dates in {filepath} after conversion. Skipping.", file=sys.stderr)
        continue

    min_date, max_date = df0.index.min(), df0.index.max()
    if pd.isna(min_date) or pd.isna(max_date):
        print(f"Could not determine a valid date range from {filepath}. Skipping.", file=sys.stderr)
        continue

    idxr=pd.date_range(min_date,max_date,freq='D')
    df=df0.reindex(idxr).interpolate(method='time').reset_index()
    if 'index' in df.columns and 'Date' not in df.columns:
        df.rename(columns={'index':'Date'}, inplace=True)

    if 'Date' in df.columns:
        date_column_data = df['Date']
        other_columns_df = df.drop(columns=['Date'])
        cleaned_other_columns_df = other_columns_df.dropna(axis=1, how='all')
        df = pd.concat([date_column_data, cleaned_other_columns_df], axis=1)

        if len(df.columns) <= 1: # Only Date column or empty
            print(f"No valid data series to plot in {filepath} after interpolation and cleaning (only Date column or empty).", file=sys.stderr)
            continue
    else:
        # This case should ideally not be reached if 'Date' was present before reindex
        print(f"Warning: 'Date' column not found in DataFrame for {filepath} after reset_index. Skipping this file.", file=sys.stderr)
        continue

    html=df_to_html(df,title=f'Fund Series Chart {idx_num}',last_dates=last_dates)
    if internal_only:
        internal_html[idx_num]=html; print(f"Stored chart {idx_num} internally",file=sys.stderr)
    else:
        name=f'fund_series_chart_{idx_num}.html'
        p=os.path.join(args.output_dir,name)
        with open(p,'w',encoding='utf-8') as ff: ff.write(html)
        print(f"Saved {p}"); htmls.append(name)

if not (use_stdin or args.bar_mode) and not htmls and not internal_html :
    print("No charts were generated from directory processing.", file=sys.stderr)

# Generate index HTML page if multiple charts were created (and not stdin/bar mode)
if not use_stdin and not args.bar_mode and (htmls or internal_html):
    base=['</body>','</html>'] # Common closing tags
    lines=['<!DOCTYPE html>','<html lang="en">','<head>','  <meta charset="utf-8">',
           '  <meta name="viewport" content="width=device-width, initial-scale=1">',
           '  <title>Aggregated Fund Series Charts</title>',
           '  <style>body { font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; } iframe { border: 1px solid #ccc; margin-bottom: 10px; } hr { display: none; }</style>',
           '</head>','<body>']
    lines.append('<h1 style="text-align:center; margin-top:20px; margin-bottom:20px;">Aggregated Fund Series Charts</h1>')

    if internal_only:
        # Embed HTML directly using srcdoc for internal mode
        for idx_num in sorted(internal_html.keys()):
            c=internal_html[idx_num].replace('"','&quot;') # Escape quotes for srcdoc
            lines.append(f'<iframe title="Fund Series Chart {idx_num}" srcdoc="{c}" style="width:100%; height:850px; border:none;"></iframe>')
        print("\n".join(lines+base)) # Print combined HTML to stdout
    else:
        # Link to separate HTML files using src for file output mode
        for name in htmls:
            lines.append(f'<iframe title="{name}" src="{name}" style="width:100%; height:850px; border:none;"></iframe>')
        lines+=base
        idxp=os.path.join(args.output_dir,'fund_series_charts_index.html')
        with open(idxp,'w',encoding='utf-8') as f:f.write("\n".join(lines))
        print(f"Generated index at {idxp}")
elif not use_stdin and not args.bar_mode:
    # This message is for the case where directory processing was attempted but yielded no charts
    print("No charts to include in master index.", file=sys.stderr)
