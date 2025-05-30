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
df_kwargs = dict(
    sep=';', decimal=',', skiprows=2, header=0,
    parse_dates=[0], dayfirst=True, na_values=[''], encoding='latin1'
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
    html = fig.to_html(include_plotlyjs='cdn', full_html=True)
    if '</body>' in html:
        html = html.replace('</body>', hover_js + '\n</body>')
    else:
        html += hover_js
    return html

# Bar-chart mode function
def bar_chart_mode(input_dir, output_dir, internal, trace_enabled):
    import os, re, json, numpy as np, pandas as pd, plotly.graph_objs as go

    py_windows = [5, 10, 21, 64, 129, 261, 390, 522]
    py_init_weights = [0.3, 1.5, 2.5, 4, 3, 2, 1.5, 1]
    py_period_label_map = {
        5: 'Week', 10: 'Fortnight', 21: 'Month', 64: 'Quarter',
        129: 'Half year', 261: 'Year', 390: '1.5 years', 522: '2 years'
    }

    num_gradient_lookback_days = 10 # Static gradient lookback period

    # --- Helper function to calculate window contributions (Python version) ---
    # This helper now ONLY returns contributions, score is calculated from these.
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
                m, _ = np.polyfit(np.arange(w_val), ys_series[-w_val:], 1)
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

    for fname in sorted(f for f in os.listdir(input_dir) if pat.match(f)):
        if trace_enabled: print(f"TRACE: Processing file: {fname}", file=sys.stderr)
        try:
            df_temp = pd.read_csv(os.path.join(input_dir, fname), **df_kwargs)
            if df_temp.empty:
                if trace_enabled: print(f"TRACE: File: {fname} - CSV empty or no data after skiprows. Skipping.", file=sys.stderr)
                continue

            for col_name_raw in df_temp.columns:
                col_name = str(col_name_raw).strip()
                if (col_name.lower() in ['date', 'datum', '#'] or \
                    col_name.startswith('Unnamed:') or \
                    not col_name):
                    if trace_enabled:
                        print(f"TRACE_AGGREGATION: File: {fname}, Column: '{col_name_raw}' (stripped: '{col_name}') - Skipping (date/unnamed/placeholder/empty).", file=sys.stderr)
                    continue

                current_ys = pd.to_numeric(df_temp[col_name_raw], errors='coerce').dropna().values
                if len(current_ys) > 0:
                    all_funds_raw_log_series[col_name] = current_ys
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

    output_fund_names = []
    main_score_contributions_list_for_js = []
    initial_scores_list_py = []
    score_gradients_list_py = []

    smallest_window_size = py_windows[0] if py_windows else 5
    min_total_length_for_gradient = smallest_window_size + (num_gradient_lookback_days - 1)

    for fund_idx, (fund_name, original_ys) in enumerate(all_funds_raw_log_series.items()):
        if trace_enabled: print(f"TRACE: Processing fund {fund_idx+1}/{len(all_funds_raw_log_series)}: {fund_name} with series length {len(original_ys)}", file=sys.stderr)
        output_fund_names.append(fund_name)

        main_contributions_py = get_window_contributions_py(original_ys, py_windows, fund_name, "MAIN_CONTRIBS")
        main_score_contributions_list_for_js.append(main_contributions_py)

        initial_main_score_py = sum(p * wt for p, wt in zip(main_contributions_py, py_init_weights))
        if not np.isfinite(initial_main_score_py): initial_main_score_py = 0.0
        initial_scores_list_py.append(initial_main_score_py)

        if trace_enabled:
            print(f"TRACE_MAIN_SCORE: Fund: {fund_name} - Main Contributions: {[round(p,2) for p in main_contributions_py]}, Initial Main Score (default weights): {initial_main_score_py:.2f}", file=sys.stderr)

        historical_scores_for_fund_py = []
        if len(original_ys) < min_total_length_for_gradient:
            if trace_enabled: print(f"TRACE_GRADIENT_PY: Fund: {fund_name} - Series too short ({len(original_ys)} < {min_total_length_for_gradient}) for {num_gradient_lookback_days}-day score gradient. Gradient will be NaN.", file=sys.stderr)
            score_gradients_list_py.append(np.nan)
        else:
            for k in range(num_gradient_lookback_days):
                historical_end_index = len(original_ys) - k
                historical_series_segment = original_ys[:historical_end_index]

                current_hist_score = 0.0
                if len(historical_series_segment) >= smallest_window_size:
                    baseline_val = historical_series_segment[-1]
                    renormalized_historical_segment = historical_series_segment - baseline_val
                    hist_contribs = get_window_contributions_py(renormalized_historical_segment, py_windows, fund_name, f"PY_HIST_D-{k}")
                    hist_score_py = sum(p * wt for p, wt in zip(hist_contribs, py_init_weights))
                    if not np.isfinite(hist_score_py): hist_score_py = 0.0
                    current_hist_score = hist_score_py
                elif trace_enabled:
                    print(f"TRACE_GRADIENT_PY: Fund: {fund_name}, HistDay D-{k} - Segment too short ({len(historical_series_segment)} < {smallest_window_size}) for score calc. Using 0 score for this day.", file=sys.stderr)
                historical_scores_for_fund_py.append(current_hist_score)

            valid_historical_scores_py = [s for s in historical_scores_for_fund_py if np.isfinite(s)]
            if trace_enabled: print(f"TRACE_GRADIENT_PY: Fund: {fund_name} - Collected historical scores (D-0 to D-{num_gradient_lookback_days-1}): {[round(s,2) if np.isfinite(s) else 'NonFinite' for s in historical_scores_for_fund_py]}", file=sys.stderr)

            if len(valid_historical_scores_py) == num_gradient_lookback_days:
                gradient_slope_py, _ = np.polyfit(np.arange(num_gradient_lookback_days), valid_historical_scores_py[::-1], 1)
                score_gradients_list_py.append(gradient_slope_py)
                if trace_enabled: print(f"TRACE_GRADIENT_PY: Fund: {fund_name} - Calculated {num_gradient_lookback_days}-day score gradient: {gradient_slope_py:.2f}", file=sys.stderr)
            else:
                score_gradients_list_py.append(np.nan)
                if trace_enabled: print(f"TRACE_GRADIENT_PY: Fund: {fund_name} - Not enough valid historical scores ({len(valid_historical_scores_py)}/{num_gradient_lookback_days}) to calculate gradient. Gradient set to NaN.", file=sys.stderr)

    cleaned_initial_scores_py = []
    if trace_enabled: print(f"TRACE_PY_INIT_SCORE_CLEAN: Cleaning initial_scores_list_py (length {len(initial_scores_list_py)}).", file=sys.stderr)
    for score_idx, score_val in enumerate(initial_scores_list_py):
        fund_name_for_trace_clean = output_fund_names[score_idx] if score_idx < len(output_fund_names) else "Unknown Fund"
        if not np.isfinite(score_val):
            cleaned_initial_scores_py.append(None)
            if trace_enabled:
                print(f"TRACE_PY_INIT_SCORE_CLEAN: Fund: {fund_name_for_trace_clean} - Original score '{score_val}' was non-finite/NaN, set to None for plotting.", file=sys.stderr)
        else:
            cleaned_initial_scores_py.append(score_val)
    initial_scores_list_py = cleaned_initial_scores_py
    if trace_enabled: print(f"TRACE_PY_INIT_SCORE_CLEAN: Finished cleaning initial_scores_list_py.", file=sys.stderr)

    cleaned_score_gradients_py = []
    if trace_enabled: print(f"TRACE_GRADIENT_CLEAN_PY: Cleaning score_gradients_list_py (length {len(score_gradients_list_py)}).", file=sys.stderr)
    for grad_idx, grad_val in enumerate(score_gradients_list_py):
        fund_name_for_grad_clean = output_fund_names[grad_idx] if grad_idx < len(output_fund_names) else "Unknown Fund"
        if not np.isfinite(grad_val):
            cleaned_score_gradients_py.append(None)
            if trace_enabled:
                print(f"TRACE_GRADIENT_CLEAN_PY: Fund: {fund_name_for_grad_clean} - Original gradient '{grad_val}' was non-finite/NaN, set to None for customdata.", file=sys.stderr)
        else:
            cleaned_score_gradients_py.append(grad_val)

    custom_data_for_plot_py = [[cleaned_score_gradients_py[i] if i < len(cleaned_score_gradients_py) else None] for i in range(len(output_fund_names))]
    if trace_enabled: print(f"TRACE_GRADIENT_CLEAN_PY: Finished cleaning score_gradients_list_py and forming custom_data_for_plot_py.", file=sys.stderr)

    fig = go.Figure(go.Bar(
        x=output_fund_names,
        y=initial_scores_list_py,
        customdata=custom_data_for_plot_py,
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
        xaxis=dict(showticklabels=False, title='Funds (Scroll/Isolate to see names)'),
        yaxis=dict(title='Score', autorange=True, type='linear'),
        barmode='group'
    )
    fig_dict = fig.to_dict()
    def clean_fig_dict_infs_nans(obj):
        if isinstance(obj, dict):
            return {k: clean_fig_dict_infs_nans(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean_fig_dict_infs_nans(elem) for elem in obj]
        elif isinstance(obj, float) and not np.isfinite(obj):
            return None
        return obj

    cleaned_fig_dict = clean_fig_dict_infs_nans(fig_dict)
    fig_json = json.dumps(cleaned_fig_dict)

    body = (
        '<div id="bar-chart" style="width:100%; height:600px; margin-bottom:30px;"></div>'
        '<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>'
        f'<script>var figDataInit={fig_json};Plotly.newPlot("bar-chart",figDataInit.data,figDataInit.layout);</script>'
    )

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

    dropdown_funds_for_select = sorted(output_fund_names)
    select_html = (
        '<div style="text-align:center; margin:20px 0;">'
        f'<select id="fund-select" multiple size="{min(len(dropdown_funds_for_select), 10)}" '
        'style="width:300px; height:200px; overflow-y:auto; border: 1px solid #ccc; border-radius: 5px; padding: 5px;"></select><br/>'
        '<button id="isolate" style="margin:10px 5px; padding: 8px 15px; border-radius:5px; background-color:#4CAF50; color:white; border:none; cursor:pointer;">Isolate</button>'
        '<button id="reset" style="margin:10px 5px; padding: 8px 15px; border-radius:5px; background-color:#f44336; color:white; border:none; cursor:pointer;">Reset</button>'
        '</div>'
    )

    js_data_script = f"""
<script>
  const mainContributionsJS = {json.dumps(main_score_contributions_list_for_js)};
  const pyInitialWeightsJS = {json.dumps(py_init_weights)};
  const allFundNamesJS = {json.dumps(output_fund_names)};
  const staticCustomDataJS = {json.dumps(custom_data_for_plot_py)}; // Static gradients from Python
</script>
"""

    main_js_logic = """
<script>
  const weightSliders = Array.from(document.querySelectorAll('input.weight-slider'));

  function updateScores() {
    const currentWeights = weightSliders.map(el => parseFloat(el.value));

    currentWeights.forEach((val,i) => {
        const vElement = document.getElementById('v'+i);
        if (vElement) { vElement.textContent = val.toFixed(1); }
    });

    const newYScores = mainContributionsJS.map(fundContribs => {
      if (!fundContribs || !Array.isArray(fundContribs)) return null;
      let scoreSum = 0;
      for (let i = 0; i < fundContribs.length; i++) {
        const perfPoint = typeof fundContribs[i] === 'number' ? fundContribs[i] : 0;
        scoreSum += perfPoint * currentWeights[i];
      }
      return Number.isFinite(scoreSum) ? scoreSum : null;
    });

    Plotly.restyle('bar-chart', {'y': [newYScores]}, [0]);
  }

  weightSliders.forEach(slider => {
    slider.addEventListener('input', updateScores);
    slider.addEventListener('wheel', function(event) {
      event.preventDefault();
      const step = parseFloat(slider.step) || 0.1;
      let currentValue = parseFloat(slider.value);
      const minVal = parseFloat(slider.min) || 0;
      const maxVal = parseFloat(slider.max) || 10;
      if (event.deltaY < 0) { currentValue += step; }
      else { currentValue -= step; }
      currentValue = Math.max(minVal, Math.min(maxVal, currentValue));
      slider.value = currentValue.toFixed(1);
      updateScores();
    });
  });

  document.addEventListener('DOMContentLoaded', () => {
    pyInitialWeightsJS.forEach((val, i) => {
        const slider = document.getElementById('w' + i);
        if (slider) { slider.value = val.toFixed(1); }
    });
    updateScores();
  });
</script>
"""

    isolate_js = f"""
<script>
  const fundSelectElement_iso = document.getElementById('fund-select');
  const fundsForDropdownIsolate_iso = {json.dumps(dropdown_funds_for_select)};

  fundsForDropdownIsolate_iso.forEach(fundName => {{
    const optionElement = document.createElement('option');
    optionElement.value = fundName; optionElement.text = fundName;
    fundSelectElement_iso.appendChild(optionElement);
  }});

  document.getElementById('isolate').addEventListener('click', function() {{
    const selectedFundNames = Array.from(fundSelectElement_iso.selectedOptions).map(opt => opt.value);
    if (selectedFundNames.length === 0) {{ return; }}

    const currentWeights_iso = weightSliders.map(el => parseFloat(el.value));

    let isolatedXValues = [];
    let isolatedYScores = [];
    let isolatedCustomData = [];

    selectedFundNames.forEach(name => {{
        const originalIndex = allFundNamesJS.indexOf(name);
        if (originalIndex !== -1) {{
            isolatedXValues.push(name);

            const fundContribs = mainContributionsJS[originalIndex];
            let currentScore = 0;
            if (fundContribs) {{
                 currentScore = fundContribs.reduce((sum, p, i) => sum + (typeof p === 'number' ? p : 0) * currentWeights_iso[i], 0);
            }}
            isolatedYScores.push(Number.isFinite(currentScore) ? currentScore : null);
            isolatedCustomData.push(staticCustomDataJS[originalIndex]);
        }}
    }});

    Plotly.restyle('bar-chart', {{
        'x': [isolatedXValues],
        'y': [isolatedYScores],
        'customdata': [isolatedCustomData]
    }}, [0]);
  }});

  document.getElementById('reset').addEventListener('click', function() {{
    fundSelectElement_iso.selectedIndex = -1;
    const currentWeights_iso = weightSliders.map(el => parseFloat(el.value));

    const allRecalculatedScores = mainContributionsJS.map(fundContribs => {{
        if (!fundContribs) return null;
        let scoreSum = 0;
        for (let i = 0; i < fundContribs.length; i++) {{
            const perfPoint = typeof fundContribs[i] === 'number' ? perfPoint : 0;
            scoreSum += perfPoint * currentWeights_iso[i];
        }}
        return Number.isFinite(scoreSum) ? scoreSum : null;
    }});

    Plotly.restyle('bar-chart', {{
        'x': [allFundNamesJS],
        'y': [allRecalculatedScores],
        'customdata': [staticCustomDataJS]
    }}, [0]);
  }});
</script>
"""

    full_html = (
        '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Fund Scores</title>'
        '<style>body {{ font-family: Arial, sans-serif; }}</style></head><body>'
        '<h1 style="text-align:center; color:#333;">Fund Performance Dashboard</h1>'
        '<h3 style="text-align:center; color:#555;">Adjust Scoring Weights</h3>'
        + slider_html
        + '<h3 style="text-align:center; margin-top:30px; color:#555;">Fund Scores Bar Chart</h3>'
        + body
        + '<div style="clear:both; margin-top:20px;"></div>'
        + '<h3 style="text-align:center; color:#555;">Isolate Funds</h3>'
        + select_html
        + js_data_script
        + main_js_logic
        + isolate_js
        + '</body></html>'
    )
    if internal:
        print(full_html)
    else:
        out = os.path.join(output_dir, 'fund_series_scores.html')
        with open(out, 'w', encoding='utf-8') as f:
            f.write(full_html)
        print(f"Saved score chart to {out}", file=sys.stderr)

# STDIN single time-series
if use_stdin and not args.bar_mode:
    try:
        df0 = pd.read_csv(sys.stdin, **df_kwargs)
    except Exception as e:
        print(f"Error reading from stdin: {e}", file=sys.stderr)
        sys.exit(1)

    if df0.empty:
        print("Received empty or all-NA data from stdin after skiprows.", file=sys.stderr)
        sys.exit(1)

    df0.rename(columns={df0.columns[0]:'Date'}, inplace=True)
    df0.dropna(axis=1, how='all', inplace=True)
    df0.dropna(subset=['Date'], how='all', inplace=True)
    if df0.empty:
        print("Data became empty after initial NA handling from stdin.", file=sys.stderr)
        sys.exit(1)
    df0.set_index('Date', inplace=True)

    df0 = df0.dropna(axis=1, how='all')
    if df0.empty:
        print("No valid data series found after initial processing from stdin.", file=sys.stderr)
        sys.exit(1)

    last_dates={c:df0[c].last_valid_index().strftime('%Y-%m-%d') for c in df0.columns if pd.notna(df0[c].last_valid_index())}

    if not df0.index.is_monotonic_increasing:
        df0 = df0.sort_index()

    df0.index = pd.to_datetime(df0.index, errors='coerce')
    df0 = df0[pd.notna(df0.index)]

    if df0.empty:
        print("No valid dates found in stdin data after conversion.", file=sys.stderr)
        sys.exit(1)

    min_date, max_date = df0.index.min(), df0.index.max()
    if pd.isna(min_date) or pd.isna(max_date):
        print("Could not determine a valid date range from stdin data.", file=sys.stderr)
        sys.exit(1)

    idx=pd.date_range(min_date, max_date, freq='D')
    df=df0.reindex(idx).interpolate(method='time').reset_index()
    if 'index' in df.columns and 'Date' not in df.columns:
        df.rename(columns={'index':'Date'}, inplace=True)

    if 'Date' in df.columns:
        date_column_data = df['Date']
        other_columns_df = df.drop(columns=['Date'])
        cleaned_other_columns_df = other_columns_df.dropna(axis=1, how='all')
        df = pd.concat([date_column_data, cleaned_other_columns_df], axis=1)

        if len(df.columns) <= 1 :
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

if args.bar_mode:
    if use_stdin:
        print("Bar mode cannot be used with stdin input. Please provide an input directory with -t.", file=sys.stderr)
        sys.exit(1)
    bar_chart_mode(args.input_dir, args.output_dir, internal_only, args.trace_mode)
    sys.exit(0)

pat=re.compile(r'fund_tables_(\d+)\.csv$')
csv_files = []
if os.path.isdir(args.input_dir):
    csv_files = sorted(
        (int(m.group(1)), os.path.join(args.input_dir, f))
        for f in os.listdir(args.input_dir)
        for m in [pat.match(f)] if m
    )
else:
    if not (use_stdin or args.bar_mode):
        print(f"Error: Input directory '{args.input_dir}' not found or is not a directory.", file=sys.stderr)
        sys.exit(1)


if not csv_files and not (use_stdin or args.bar_mode):
    print(f"No CSVs matching 'fund_tables_<n>.csv' found in {args.input_dir}", file=sys.stderr)
    sys.exit(1)

htmls=[]
internal_html={}
for idx_num, filepath in csv_files:
    try:
        df0=pd.read_csv(filepath,**df_kwargs)
    except Exception as e:
        print(f"Error reading CSV file {filepath}: {e}", file=sys.stderr)
        continue

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
    df0 = df0[pd.notna(df0.index)]

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

        if len(df.columns) <= 1:
            print(f"No valid data series to plot in {filepath} after interpolation and cleaning (only Date column or empty).", file=sys.stderr)
            continue
    else:
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

if not use_stdin and not args.bar_mode and (htmls or internal_html):
    base=['</body>','</html>']
    lines=['<!DOCTYPE html>','<html lang="en">','<head>','  <meta charset="utf-8">',
           '  <meta name="viewport" content="width=device-width, initial-scale=1">',
           '  <title>Aggregated Fund Series Charts</title>',
           '  <style>body { font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; } iframe { border: 1px solid #ccc; margin-bottom: 10px; } hr { display: none; }</style>',
           '</head>','<body>']
    lines.append('<h1 style="text-align:center; margin-top:20px; margin-bottom:20px;">Aggregated Fund Series Charts</h1>')

    if internal_only:
        for idx_num in sorted(internal_html.keys()):
            c=internal_html[idx_num].replace('"','&quot;')
            lines.append(f'<iframe title="Fund Series Chart {idx_num}" srcdoc="{c}" style="width:100%; height:850px; border:none;"></iframe>')
        print("\n".join(lines+base))
    else:
        for name in htmls:
            lines.append(f'<iframe title="{name}" src="{name}" style="width:100%; height:850px; border:none;"></iframe>')
        lines+=base
        idxp=os.path.join(args.output_dir,'fund_series_charts_index.html')
        with open(idxp,'w',encoding='utf-8') as f:f.write("\n".join(lines))
        print(f"Generated index at {idxp}")
elif not use_stdin and not args.bar_mode:
    print("No charts to include in master index.", file=sys.stderr)
