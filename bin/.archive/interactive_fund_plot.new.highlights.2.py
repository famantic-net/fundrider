import os
import re
import sys
import argparse
import json
import html # Added for HTML escaping
import numpy as np
import pandas as pd
import plotly.graph_objs as go
import plotly.utils # Added this import for PlotlyJSONEncoder

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
    parse_dates=[0], dayfirst=False, na_values=[''], encoding='latin1'
)

# --- JavaScript snippets for individual charts OR single page ---

styling_constants_js = """
<script>
    // [JS STYLING CONSTANTS] Loaded
    const defaultLineWidth = 2;
    const selectedLineWidth = 4; // For globally selected funds
    const dimmedLineWidth = 1.5;   // For non-selected or in dimmed charts
    const hoverLineWidth = 5;      // For mouse hover, distinctly thicker
    const defaultOpacity = 1.0;
    const dimmedOpacity = 0.4;
</script>
"""

# This script will be used by individual chart files OR by the single large HTML in internal_only mode
selection_and_hover_js_logic = """
<script>
    // [JS SELECTION/HOVER LOGIC] Script block started.
    console.log('!!! [JS SELECTION/HOVER LOGIC] SCRIPT BLOCK EXECUTING !!! Title:', document.title);

    let currentGlobalSelectedFunds = []; // Master state for selected funds, shared across all charts on a single page

    function applyGlobalFundSelectionStyle(gd, fundsToUse) {
        if (gd._isApplyingStyles) {
            console.log('[JS applyGlobalFundSelectionStyle] Skipping for gd.id:', gd.id, 'due to _isApplyingStyles flag.');
            return;
        }
        console.log('[JS applyGlobalFundSelectionStyle] Called for chart. GD id:', gd.id, 'fundsToUse:', JSON.parse(JSON.stringify(fundsToUse)));
        if (!gd || !gd.data || !gd.layout) {
            console.warn('[JS applyGlobalFundSelectionStyle] GD, gd.data, or gd.layout not ready for gd.id:', gd ? gd.id : 'undefined_gd');
            return;
        }

        const legendTexts = gd.querySelectorAll('.legendtext');
        const restyleUpdate = {
            'line.width': [],
            'opacity': []
        };
        const traceIndicesToUpdate = Array.from({length: gd.data.length}, (_, k) => k);

        gd.data.forEach((trace, i) => {
            const baseTraceName = (trace.name || '').split('<br>')[0];
            let targetLineWidth = defaultLineWidth;
            let targetOpacity = defaultOpacity;
            let legendFontWeight = 'normal';

            if (fundsToUse && fundsToUse.length > 0) {
                if (fundsToUse.includes(baseTraceName)) {
                    targetLineWidth = selectedLineWidth;
                    targetOpacity = defaultOpacity;
                    legendFontWeight = 'bold';
                } else {
                    targetLineWidth = dimmedLineWidth;
                    targetOpacity = dimmedOpacity;
                    legendFontWeight = 'normal';
                }
            }

            restyleUpdate['line.width'][i] = targetLineWidth;
            restyleUpdate['opacity'][i] = targetOpacity;

            if (legendTexts && legendTexts[i]) {
                legendTexts[i].style.fontWeight = legendFontWeight;
            }
            // console.log(`[JS applyGlobalFundSelectionStyle] Chart ${gd.id}, Trace ${i} (${baseTraceName}): NewLineWidth: ${targetLineWidth}, NewOpacity: ${targetOpacity}, LegendWeight: ${legendFontWeight}`);
        });

        if (traceIndicesToUpdate.length > 0) {
            gd._isApplyingStyles = true;
            console.log('[JS applyGlobalFundSelectionStyle] PRE-RESTYLE for gd.id:', gd.id, 'Update Object:', JSON.stringify(restyleUpdate));
            Plotly.restyle(gd, restyleUpdate, traceIndicesToUpdate).then(function() {
                 console.log('[JS applyGlobalFundSelectionStyle] Restyle successful for gd.id:', gd.id);
            }).catch(function(err) {
                 console.error('[JS applyGlobalFundSelectionStyle] Restyle FAILED for gd.id:', gd.id, err);
            }).finally(function() {
                setTimeout(() => { // Use setTimeout to ensure this runs after Plotly's internal event processing
                    gd._isApplyingStyles = false;
                    console.log('[JS applyGlobalFundSelectionStyle] Reset _isApplyingStyles flag for gd.id:', gd.id);
                }, 100); // Increased timeout slightly
            });
        } else {
             console.log('[JS applyGlobalFundSelectionStyle] No traces found to update for gd.id:', gd.id);
        }
    }

    // For IFRAME mode (when not internal_only)
    if (window.parent && window.parent !== window) {
        window.addEventListener('message', function(event) {
            if (event.data && event.data.type === 'fundSelectionUpdate') {
                currentGlobalSelectedFunds = event.data.selectedFunds || [];
                document.querySelectorAll('.plotly-graph-div').forEach(function(gdNode) {
                    if (gdNode.data && gdNode.layout) {
                         applyGlobalFundSelectionStyle(gdNode, currentGlobalSelectedFunds);
                    }
                });
            }
        });
    }

    // For SINGLE-PAGE mode, called by internal_master_js
    function updateAllChartsOnPage(selectedFunds) {
        console.log('!!! [JS SELECTION/HOVER LOGIC] updateAllChartsOnPage called with funds:', selectedFunds);
        currentGlobalSelectedFunds = selectedFunds || [];

        document.querySelectorAll('.plotly-graph-div').forEach(function(gdNode) {
            if (gdNode.data && gdNode.layout) {
                console.log(`[JS updateAllChartsOnPage] Calling applyGlobalFundSelectionStyle directly for ${gdNode.id}`);
                applyGlobalFundSelectionStyle(gdNode, currentGlobalSelectedFunds);
            } else {
                console.warn(`[JS updateAllChartsOnPage] Skipped ${gdNode.id} because it's not a full Plotly graph object yet.`);
            }
        });
    }

    document.addEventListener('DOMContentLoaded', function() {
        console.log('[JS SELECTION/HOVER LOGIC] DOMContentLoaded in:', document.title);
        document.querySelectorAll('.plotly-graph-div').forEach(function(gdNode) {
             gdNode._isApplyingStyles = false;

             gdNode.on('plotly_afterplot', function(){
                console.log('[JS SELECTION/HOVER LOGIC] plotly_afterplot event for GD ID:', gdNode.id, 'isApplyingStyles:', gdNode._isApplyingStyles);
                if (!gdNode._isApplyingStyles) {
                    applyGlobalFundSelectionStyle(gdNode, currentGlobalSelectedFunds);
                }
             });

             if (gdNode.data && gdNode.layout) {
                 console.log('[JS SELECTION/HOVER LOGIC] Chart seems ready on DOMContentLoaded, applying initial style for GD ID:', gdNode.id);
                 applyGlobalFundSelectionStyle(gdNode, currentGlobalSelectedFunds);
             }

            if (!gdNode.on) return;

            gdNode.on('plotly_hover', function(data) {
              var ci = data.points[0].curveNumber;
              var legendTexts = gdNode.querySelectorAll('.legendtext');
              Plotly.restyle(gdNode, {'line.width': hoverLineWidth, opacity: defaultOpacity}, [ci]);
              if (gdNode.data && gdNode.data[ci] && legendTexts && legendTexts.length > ci) {
                var traceName = gdNode.data[ci].name || '';
                var foundMatchByName = false;
                legendTexts.forEach(el => {
                  if(el.textContent.startsWith(traceName.split('<br>')[0])) {
                    el.style.fontWeight='bold';
                    foundMatchByName = true;
                  }
                });
                if (!foundMatchByName && legendTexts[ci]) { legendTexts[ci].style.fontWeight = 'bold';}
              } else if (legendTexts && legendTexts.length > ci && legendTexts[ci]) {
                legendTexts[ci].style.fontWeight = 'bold';
              }
            });

            gdNode.on('plotly_unhover', function() {
              if (typeof applyGlobalFundSelectionStyle === 'function') {
                applyGlobalFundSelectionStyle(gdNode, currentGlobalSelectedFunds);
              }
            });

            gdNode.on('plotly_legendclick', function() {
                setTimeout(function() {
                    if (typeof applyGlobalFundSelectionStyle === 'function' && !gdNode._isApplyingStyles) {
                        applyGlobalFundSelectionStyle(gdNode, currentGlobalSelectedFunds);
                    }
                }, 0);
            });
        });

        if (window.parent && window.parent !== window) {
            try {
                 window.parent.postMessage({ type: 'iframeReady', title: document.title }, '*');
            } catch (e) { /* ignore */ }
        }
    });
</script>
"""


# Helper: build HTML for time-series chart (for individual files)
def df_to_html_individual_file(df, title=None, last_dates=None):
    num_series = len(df.columns) - 1 if 'Date' in df.columns else len(df.columns)
    base_h = max(500, num_series*25 + 100)
    height_px = int(base_h * 1.5)
    fig = go.Figure()
    for col in df.columns:
        if col=='Date': continue
        name = col
        if last_dates and col in last_dates:
            name = f"{col}<br>{last_dates[col]}"
        series_data = pd.to_numeric(df[col], errors='coerce')
        custom_hover_data = 10 ** series_data * 100
        fig.add_trace(go.Scatter(
            x=df['Date'], y=series_data, mode='lines', name=name, customdata=custom_hover_data,
            line=dict(width=2), # Initial default width
            hovertemplate=(
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

    plotly_cdn_script = '<script src="https://cdn.plot.ly/plotly-3.0.1.min.js"></script>'
    chart_div_and_script = fig.to_html(include_plotlyjs=False, full_html=False)

    escaped_title = html.escape(title if title else "Fund Series Chart")

    html_output = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{escaped_title}</title>
    {plotly_cdn_script}
    {styling_constants_js}
    {selection_and_hover_js_logic}
</head>
<body>
    {chart_div_and_script}
</body>
</html>"""
    return html_output

# Helper: build ONLY chart div and its newPlot script (for internal_only single page)
def df_to_html_chart_content_internal(df, chart_id_suffix, title=None, last_dates=None):
    num_series = len(df.columns) - 1 if 'Date' in df.columns else len(df.columns)
    base_h = max(500, num_series*25 + 100)
    height_px = int(base_h * 1.5)
    div_id = f"plotlyChartDiv_{chart_id_suffix}"

    fig = go.Figure()
    for col in df.columns:
        if col=='Date': continue
        name = col
        if last_dates and col in last_dates: name = f"{col}<br>{last_dates[col]}"
        series_data = pd.to_numeric(df[col], errors='coerce')
        custom_hover_data = 10 ** series_data * 100
        fig.add_trace(go.Scatter(
            x=df['Date'], y=series_data, mode='lines', name=name, customdata=custom_hover_data,
            line=dict(width=2), hovertemplate=('<b>Series:</b> %{fullData.name}<br><b>Date:</b> %{x|%Y-%m-%d}<br><b>Value (log10):</b> %{y:.3f}<br><b>Relative Change:</b> %{customdata:.1f}%<extra></extra>')
        ))
    layout = dict(hovermode='closest', template='plotly_white', height=height_px,
                  yaxis=dict(zeroline=True, zerolinewidth=3, title='Normalized Value (log10 scale, 0 = Last Date)'),
                  xaxis=dict(title='Date'), legend=dict(traceorder='normal'))
    if title: layout['title'] = dict(text=title, x=0.5, xanchor='center')
    fig.update_layout(**layout)

    chart_div_html = f'<div id="{div_id}" class="plotly-graph-div" style="height:{height_px}px; width:100%;"></div>'
    fig_data_json = json.dumps(fig.data, cls=plotly.utils.PlotlyJSONEncoder)
    fig_layout_json = json.dumps(fig.layout, cls=plotly.utils.PlotlyJSONEncoder)

    plotly_script_html = f"""
<script type="text/javascript">
    var data_{div_id} = {fig_data_json};
    var layout_{div_id} = {fig_layout_json};
    var gd_{div_id} = document.getElementById('{div_id}');
    Plotly.newPlot(gd_{div_id}, data_{div_id}, layout_{div_id});
</script>
"""
    return chart_div_html + "\n" + plotly_script_html


# Bar-chart mode function
def bar_chart_mode(input_dir, output_dir, internal, trace_enabled):
    import os, re, json, numpy as np, pandas as pd, plotly.graph_objs as go

    py_windows = [5, 10, 21, 64, 129, 261, 390, 522]
    py_init_weights = [0.3, 1.5, 2.5, 4, 3, 2, 1.5, 1]
    py_period_label_map = {
        5: 'Week', 10: 'Fortnight', 21: 'Month', 64: 'Quarter',
        129: 'Half year', 261: 'Year', 390: '1.5 years', 522: '2 years'
    }
    num_gradient_lookback_days = 10

    def get_window_contributions_py(ys_series, current_windows, fund_name_for_trace, context_label_for_trace):
        pct_contributions = []
        if not isinstance(ys_series, np.ndarray): ys_series = np.array(ys_series)
        for w_val in current_windows:
            if len(ys_series) < w_val:
                pct_contributions.append(0.0)
            else:
                m, _ = np.polyfit(np.arange(w_val), ys_series[-w_val:], 1)
                raw_contrib = m * (w_val - 1) * 100
                pct_contributions.append(raw_contrib if np.isfinite(raw_contrib) else 0.0)
        return pct_contributions

    pat = re.compile(r'fund_tables_(\d+)\.csv$')
    all_funds_raw_log_series = {}
    if not os.path.isdir(input_dir): sys.exit(f"Error: Input directory '{input_dir}' not found.")

    for fname in sorted(f for f in os.listdir(input_dir) if pat.match(f)):
        try:
            df_temp = pd.read_csv(os.path.join(input_dir, fname), **df_kwargs)
            if df_temp.empty: continue
            for col_name_raw in df_temp.columns:
                col_name = str(col_name_raw).strip()
                if col_name.lower() in ['date', 'datum', '#'] or col_name.startswith('Unnamed:') or not col_name: continue
                current_ys = pd.to_numeric(df_temp[col_name_raw], errors='coerce').dropna().values
                if len(current_ys) > 0: all_funds_raw_log_series[col_name] = current_ys
        except Exception as e: print(f"Error processing file {fname}: {e}", file=sys.stderr)

    if not all_funds_raw_log_series: sys.exit(f"No valid fund data collected from {input_dir}.")

    sorted_fund_names = sorted(all_funds_raw_log_series.keys())
    output_fund_names, main_score_contributions_list_for_js, initial_scores_list_py, initial_gradients_list_py = [], [], [], []
    historical_contributions_for_all_funds_js = {}
    min_total_length_for_gradient = (py_windows[0] if py_windows else 5) + (num_gradient_lookback_days - 1)

    for fund_name in sorted_fund_names:
        original_ys = all_funds_raw_log_series[fund_name]
        output_fund_names.append(fund_name)
        main_contributions_py = get_window_contributions_py(original_ys, py_windows, fund_name, "MAIN")
        main_score_contributions_list_for_js.append(main_contributions_py)
        initial_main_score_py = sum(p * wt for p, wt in zip(main_contributions_py, py_init_weights))
        initial_scores_list_py.append(initial_main_score_py if np.isfinite(initial_main_score_py) else 0.0)

        fund_historical_contrib_sets_for_js = []
        if len(original_ys) < min_total_length_for_gradient:
            for _ in range(num_gradient_lookback_days): fund_historical_contrib_sets_for_js.append([0.0] * len(py_windows))
        else:
            for k in range(num_gradient_lookback_days):
                historical_series_segment = original_ys[:len(original_ys) - k]
                current_hist_contribs = [0.0] * len(py_windows)
                if len(historical_series_segment) >= (py_windows[0] if py_windows else 5):
                    renormalized_historical_segment = historical_series_segment - historical_series_segment[-1]
                    current_hist_contribs = get_window_contributions_py(renormalized_historical_segment, py_windows, fund_name, f"HIST_D-{k}")
                fund_historical_contrib_sets_for_js.append(current_hist_contribs)
        historical_contributions_for_all_funds_js[fund_name] = fund_historical_contrib_sets_for_js

        initial_historical_scores_for_gradient = []
        if len(original_ys) >= min_total_length_for_gradient:
            for k_init_grad in range(num_gradient_lookback_days):
                hist_score = sum(p * wt for p, wt in zip(fund_historical_contrib_sets_for_js[k_init_grad], py_init_weights))
                initial_historical_scores_for_gradient.append(hist_score if np.isfinite(hist_score) else 0.0)
            if len([s for s in initial_historical_scores_for_gradient if np.isfinite(s)]) == num_gradient_lookback_days:
                slope, _ = np.polyfit(np.arange(num_gradient_lookback_days), initial_historical_scores_for_gradient[::-1], 1)
                initial_gradients_list_py.append(slope)
            else: initial_gradients_list_py.append(np.nan)
        else: initial_gradients_list_py.append(np.nan)

    initial_scores_list_py = [s if np.isfinite(s) else None for s in initial_scores_list_py]
    cleaned_initial_gradients_py = [g if np.isfinite(g) else None for g in initial_gradients_list_py]
    custom_data_for_plot_py = [[cleaned_initial_gradients_py[i] if i < len(cleaned_initial_gradients_py) else None] for i in range(len(output_fund_names))]

    fig = go.Figure(go.Bar(x=output_fund_names, y=initial_scores_list_py, customdata=custom_data_for_plot_py, marker_color='steelblue', name='Fund Scores',
                           hovertemplate='<b>Fund:</b> %{x}<br><b>Score:</b> %{y:.2f}<br><b>Score Trend (' + str(num_gradient_lookback_days) + 'd):</b> %{customdata[0]:.2f}<extra></extra>'))
    fig.update_layout(title='Current fund performance', template='plotly_white', height=600, xaxis=dict(showticklabels=False, title='Funds (Scroll/Isolate to see names)'), yaxis=dict(title='Score', autorange=True, type='linear'), barmode='group')

    def clean_fig_dict_infs_nans(obj):
        if isinstance(obj, dict): return {k: clean_fig_dict_infs_nans(v) for k, v in obj.items()}
        if isinstance(obj, list): return [clean_fig_dict_infs_nans(elem) for elem in obj]
        return None if isinstance(obj, float) and not np.isfinite(obj) else obj
    fig_json = json.dumps(clean_fig_dict_infs_nans(fig.to_dict()))

    body = (f'<div id="bar-chart" style="width:100%; height:600px; margin-bottom:30px;"></div>'
            f'<script src="https://cdn.plot.ly/plotly-3.0.1.min.js"></script>'
            f'<script>var figDataInit={fig_json};Plotly.newPlot("bar-chart",figDataInit.data,figDataInit.layout);</script>')

    slider_html = '<table style="margin:auto; width:90%; border-spacing: 5px;"><tr>' + "".join([
        f'<td style="text-align:center; padding:8px; vertical-align:top; border: 1px solid #ddd; border-radius: 5px; min-width:100px;">'
        f'<div>Window {d}d</div><div>{py_period_label_map.get(d, f"{d}d")}</div>'
        f'<div>Weight: <span id="v{i}" style="font-weight:bold;">{py_init_weights[i]:.1f}</span></div>'
        f'<div><input id="w{i}" data-index="{i}" class="weight-slider" type="range" min="0" max="10" step="0.1" value="{py_init_weights[i]:.1f}" style="width:100%;"></div></td>'
        for i, d in enumerate(py_windows)]) + '</tr></table>'

    controls_and_table_html = (
        '<div style="display: flex; justify-content: space-around; margin: 20px 0; align-items: flex-start; flex-wrap: wrap;">'
        '  <div id="fund-isolation-controls" style="flex: 1; min-width: 320px; padding:10px;">'
        '    <h3 style="text-align:center; color:#555;">Isolate Funds</h3>'
        f'   <select id="fund-select" multiple size="{min(len(output_fund_names), 10)}" style="width:100%; height:200px; overflow-y:auto; border: 1px solid #ccc; border-radius: 5px; padding: 5px;"></select><br/>'
        '    <div style="text-align:center; margin-top:10px;">'
        '      <button id="isolate" style="margin:5px; padding: 8px 15px; border-radius:5px; background-color:#4CAF50; color:white; border:none; cursor:pointer;">Isolate</button>'
        '      <button id="reset" style="margin:5px; padding: 8px 15px; border-radius:5px; background-color:#f44336; color:white; border:none; cursor:pointer;">Reset</button>'
        '    </div></div>'
        '  <div id="dynamic-fund-table-container" style="flex: 1.5; min-width: 400px; padding:10px;"><h3 style="text-align:center; color:#555;">Top Funds</h3></div></div>')

    js_data_script = f"""<script>
  const mainContributionsJS = {json.dumps(main_score_contributions_list_for_js)};
  const historicalContributionsDataJS = {json.dumps(historical_contributions_for_all_funds_js)};
  const pyInitialWeightsJS = {json.dumps(py_init_weights)};
  const allFundNamesJS = {json.dumps(output_fund_names)};
  const numGradientLookbackDaysJS = {json.dumps(num_gradient_lookback_days)};
</script>"""
    main_js_logic = """<script>
  const weightSliders = Array.from(document.querySelectorAll('input.weight-slider'));
  let currentSortColumn = 'score', currentSortAscending = false, currentlyIsolatedFundNames = null;
  function calculateScore(contribs, weights) {
    if (!contribs || !Array.isArray(contribs)) return null;
    let score = 0; contribs.forEach((c,j) => score += (typeof c === 'number' ? c : 0) * weights[j]);
    return Number.isFinite(score) ? score : null;
  }
  function calculateSlope(yVals) {
    if (!yVals || yVals.length < 2) return null;
    const n = yVals.length, xVals = Array.from({length:n},(_,i)=>i);
    let sumX=0, sumY=0, sumXY=0, sumXX=0, validPts=0;
    for(let i=0;i<n;i++){if(typeof yVals[i]==='number'&&Number.isFinite(yVals[i])){sumX+=xVals[i];sumY+=yVals[i];sumXY+=xVals[i]*yVals[i];sumXX+=xVals[i]*xVals[i];validPts++;}}
    if(validPts<2)return null; const denom=(validPts*sumXX-sumX*sumX); if(denom===0)return null;
    return Number.isFinite(slope=(validPts*sumXY-sumX*sumY)/denom)?slope:null;
  }
  function renderDynamicTable(fundData) {
    const container=document.getElementById('dynamic-fund-table-container'),title=container.querySelector('h3'); container.innerHTML=''; if(title)container.appendChild(title);
    if(!fundData||fundData.length===0){const p=document.createElement('p');p.textContent='No funds to display.';p.style.textAlign='center';container.appendChild(p);return;}
    fundData.sort((a,b)=>{let vA=currentSortColumn==='score'?a.score:a.gradient,vB=currentSortColumn==='score'?b.score:b.gradient;vA=(vA===null||isNaN(vA))?(currentSortAscending?Infinity:-Infinity):vA;vB=(vB===null||isNaN(vB))?(currentSortAscending?Infinity:-Infinity):vB;if(vA<vB)return currentSortAscending?-1:1;if(vA>vB)return currentSortAscending?1:-1;return 0;});
    const top20=fundData.slice(0,20),table=document.createElement('table');table.style.cssText='width:100%;border-collapse:collapse;margin-top:10px;';
    const head=table.createTHead().insertRow(),headers=[{t:'Fund Name',k:'name'},{t:'Fund Score',k:'score'},{t:`Fund Score Gradient (${numGradientLookbackDaysJS}d)`,k:'gradient'}];
    headers.forEach(h=>{const th=document.createElement('th');th.textContent=h.t;th.style.cssText='border:1px solid #ddd;padding:8px;text-align:left;background-color:#f0f0f0;font-weight:bold;';if(h.k==='score'||h.k==='gradient'){th.style.cursor='pointer';th.addEventListener('click',()=>{currentSortColumn===h.k?currentSortAscending=!currentSortAscending:(currentSortColumn=h.k,currentSortAscending=false);updateScoresAndGradients();});if(currentSortColumn===h.k){th.style.fontStyle='italic';th.innerHTML+=currentSortAscending?' &uarr;':' &darr;';}}head.appendChild(th);});
    const tbody=table.createTBody();top20.forEach(f=>{const r=tbody.insertRow(),s=f.score,g=f.gradient;r.insertCell().textContent=f.name;r.insertCell().textContent=s!==null&&!isNaN(s)?s.toFixed(2):'N/A';r.insertCell().textContent=g!==null&&!isNaN(g)?g.toFixed(2):'N/A';Array.from(r.cells).forEach(c=>{c.style.border='1px solid #ddd';c.style.padding='8px';if(c!==r.cells[0])c.style.textAlign='right';});});container.appendChild(table);
  }
  function updateScoresAndGradients(fundsToProc=null){
    const weights=weightSliders.map(el=>parseFloat(el.value));weights.forEach((v,i)=>{const el=document.getElementById('v'+i);if(el)el.textContent=v.toFixed(1);});
    let yScores=[],customData=[],tableData=[]; const namesToUse=fundsToProc?fundsToProc:(currentlyIsolatedFundNames||allFundNamesJS);
    namesToUse.forEach(fundName=>{const idx=allFundNamesJS.indexOf(fundName);if(idx===-1)return; const mainContribs=mainContributionsJS[idx],mainScore=calculateScore(mainContribs,weights);yScores.push(mainScore);
      const histSets=historicalContributionsDataJS[fundName];let histScores=[],grad=null;
      if(histSets&&histSets.length===numGradientLookbackDaysJS){for(let i=0;i<numGradientLookbackDaysJS;i++)histScores.push(calculateScore(histSets[i],weights));grad=calculateSlope(histScores.slice().reverse());}
      customData.push([grad]);tableData.push({name:fundName,score:mainScore,gradient:grad});});
    Plotly.restyle('bar-chart',{x:[namesToUse],y:[yScores],customdata:[customData]},[0]);
    if(!currentlyIsolatedFundNames){tableData=[];allFundNamesJS.forEach(fN=>{const idx=allFundNamesJS.indexOf(fN),mC=mainContributionsJS[idx],mS=calculateScore(mC,weights);const hS=historicalContributionsDataJS[fN];let hScrs=[],gr=null;if(hS&&hS.length===numGradientLookbackDaysJS){for(let i=0;i<numGradientLookbackDaysJS;i++)hScrs.push(calculateScore(hS[i],weights));gr=calculateSlope(hScrs.slice().reverse());}tableData.push({name:fN,score:mS,gradient:gr});});}
    renderDynamicTable(tableData);
  }
  weightSliders.forEach(s=>{s.addEventListener('input',()=>updateScoresAndGradients());s.addEventListener('wheel',function(e){e.preventDefault();const step=parseFloat(s.step)||0.1;let cur=parseFloat(s.value),min=parseFloat(s.min)||0,max=parseFloat(s.max)||10;e.deltaY<0?cur+=step:cur-=step;s.value=Math.max(min,Math.min(max,cur)).toFixed(1);updateScoresAndGradients();});});
  document.addEventListener('DOMContentLoaded',()=>{pyInitialWeightsJS.forEach((v,i)=>{const s=document.getElementById('w'+i);if(s)s.value=v.toFixed(1);});updateScoresAndGradients();});
</script>"""
    isolate_js = f"""<script>
  const fundSel=document.getElementById('fund-select'),fundsDrop={json.dumps(output_fund_names)};
  fundsDrop.forEach(fN=>{{
    const opt=document.createElement('option');
    opt.value=fN;
    opt.text=fN;
    fundSel.appendChild(opt);
  }});

  document.getElementById('isolate').addEventListener('click',()=>{{
    const sel=Array.from(fundSel.selectedOptions).map(o=>o.value);
    if(sel.length===0){{
        currentlyIsolatedFundNames=null;
        updateScoresAndGradients();
        return;
    }}
    currentlyIsolatedFundNames=sel;
    updateScoresAndGradients(sel);
  }});

  document.getElementById('reset').addEventListener('click',()=>{{
    fundSel.selectedIndex=-1;
    currentlyIsolatedFundNames=null;
    updateScoresAndGradients();
  }});
</script>"""

    full_html = ('<!DOCTYPE html><html><head><meta charset="utf-8"><title>Fund Scores</title><style>body{font-family:Arial,sans-serif;}</style></head><body>'
                 '<h1 style="text-align:center;color:#333;">Fund Performance Dashboard</h1><h3 style="text-align:center;color:#555;">Adjust Scoring Weights</h3>' +
                 slider_html + '<h3 style="text-align:center;margin-top:30px;color:#555;">Fund Scores Bar Chart</h3>' + body + controls_and_table_html +
                 js_data_script + main_js_logic + isolate_js + '</body></html>')
    if internal: print(full_html)
    else:
        out_path = os.path.join(output_dir, 'fund_series_scores.html')
        with open(out_path, 'w', encoding='utf-8') as f: f.write(full_html)
        print(f"Saved score chart to {out_path}", file=sys.stderr)

# --- Main script execution logic ---
all_unique_fund_names = set()

# STDIN single time-series mode
if use_stdin and not args.bar_mode:
    try:
        df0 = pd.read_csv(sys.stdin, **df_kwargs)
        if df0.empty: sys.exit("Received empty data from stdin.")
        df0.rename(columns={df0.columns[0]:'Date'}, inplace=True)
        df0.dropna(axis=1, how='all', inplace=True)
        df0.dropna(subset=['Date'], how='all', inplace=True)
        if df0.empty: sys.exit("Data empty after initial NA handling from stdin.")
        df0.set_index('Date', inplace=True)
        df0 = df0.dropna(axis=1, how='all')
        if df0.empty: sys.exit("No valid data series in stdin.")

        last_dates={c:df0[c].last_valid_index().strftime('%Y-%m-%d') for c in df0.columns if pd.notna(df0[c].last_valid_index())}
        if not df0.index.is_monotonic_increasing: df0 = df0.sort_index()
        df0.index = pd.to_datetime(df0.index, errors='coerce')
        df0 = df0[pd.notna(df0.index)]
        if df0.empty: sys.exit("No valid dates in stdin after conversion.")

        min_date, max_date = df0.index.min(), df0.index.max()
        if pd.isna(min_date) or pd.isna(max_date): sys.exit("Invalid date range from stdin.")

        idx=pd.date_range(min_date, max_date, freq='D')
        df=df0.reindex(idx).interpolate(method='time').reset_index(names=['Date'])

        if 'Date' in df.columns:
            date_col = df['Date']
            other_cols = df.drop(columns=['Date']).dropna(axis=1, how='all')
            if other_cols.empty : sys.exit("No valid data series to plot from stdin.")
            df = pd.concat([date_col, other_cols], axis=1)
        else: sys.exit("Date column missing after processing stdin.")

        html_content=df_to_html_individual_file(df,title='Fund Series Chart (from stdin)',last_dates=last_dates)
        print(html_content)
        if not internal_only:
             outf=os.path.join(args.output_dir,'fund_series_chart_stdin.html')
             with open(outf,'w',encoding='utf-8') as f: f.write(html_content)
             print(f"Saved {outf}",file=sys.stderr)

    except Exception as e:
        print(f"Error processing stdin: {e}", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)

# Bar chart mode
if args.bar_mode:
    if use_stdin: sys.exit("Bar mode cannot be used with stdin. Provide an input directory with -t.")
    bar_chart_mode(args.input_dir, args.output_dir, internal_only, args.trace_mode)
    sys.exit(0)

# Default mode: Process multiple CSVs for time-series charts
pat=re.compile(r'fund_tables_(\d+)\.csv$')
csv_files = []
if os.path.isdir(args.input_dir):
    csv_files = sorted(
        (int(m.group(1)), os.path.join(args.input_dir, f))
        for f in os.listdir(args.input_dir) for m in [pat.match(f)] if m
    )
else:
    if not (use_stdin or args.bar_mode): sys.exit(f"Error: Input directory '{args.input_dir}' not found.")

if not csv_files and not (use_stdin or args.bar_mode):
    sys.exit(f"No CSVs matching 'fund_tables_<n>.csv' found in {args.input_dir}")

chart_html_parts = []
html_file_outputs_for_index=[]
generated_any_chart = False

for idx_num, filepath in csv_files:
    try:
        df0=pd.read_csv(filepath,**df_kwargs)
        if df0.empty: print(f"Warning: CSV {filepath} empty. Skipping.", file=sys.stderr); continue
        df0.rename(columns={df0.columns[0]:'Date'},inplace=True)
        df0.dropna(axis=1,how='all',inplace=True)
        df0.dropna(subset=['Date'], how='all', inplace=True)
        if df0.empty: print(f"Data empty for {filepath} after NA handling. Skipping.", file=sys.stderr); continue
        df0.set_index('Date',inplace=True)
        df0 = df0.dropna(axis=1, how='all')
        if df0.empty: print(f"No valid series in {filepath}. Skipping.", file=sys.stderr); continue

        for fund_col in df0.columns:
            all_unique_fund_names.add(str(fund_col).strip())

        last_dates={c:df0[c].last_valid_index().strftime('%Y-%m-%d') for c in df0.columns if pd.notna(df0[c].last_valid_index())}
        if not df0.index.is_monotonic_increasing: df0 = df0.sort_index()
        df0.index = pd.to_datetime(df0.index, errors='coerce')
        df0 = df0[pd.notna(df0.index)]
        if df0.empty: print(f"No valid dates in {filepath}. Skipping.", file=sys.stderr); continue

        min_date, max_date = df0.index.min(), df0.index.max()
        if pd.isna(min_date) or pd.isna(max_date): print(f"Invalid date range in {filepath}. Skipping.", file=sys.stderr); continue

        idxr=pd.date_range(min_date,max_date,freq='D')
        df=df0.reindex(idxr).interpolate(method='time').reset_index().rename(columns={'index':'Date'})

        if 'Date' in df.columns:
            date_column_data = df['Date']
            other_columns_df = df.drop(columns=['Date']).dropna(axis=1, how='all')
            if other_columns_df.empty: print(f"No data series to plot in {filepath}. Skipping.", file=sys.stderr); continue
            df = pd.concat([date_column_data, other_columns_df], axis=1)
        else: print(f"Date column missing in {filepath}. Skipping.", file=sys.stderr); continue

        chart_title = f'Fund Series Chart {idx_num}'
        if internal_only:
            chart_content_html = df_to_html_chart_content_internal(df, chart_id_suffix=str(idx_num), title=chart_title, last_dates=last_dates)
            chart_html_parts.append(chart_content_html)
        else:
            full_chart_html=df_to_html_individual_file(df,title=chart_title,last_dates=last_dates)
            name=f'fund_series_chart_{idx_num}.html'
            p=os.path.join(args.output_dir,name)
            with open(p,'w',encoding='utf-8') as ff: ff.write(full_chart_html)
            print(f"Saved {p}"); html_file_outputs_for_index.append({'type': 'src', 'content': name, 'title': chart_title})
        generated_any_chart = True
    except Exception as e:
        print(f"Error processing file {filepath}: {e}", file=sys.stderr)
        continue

if not generated_any_chart and not (use_stdin or args.bar_mode) :
    print("No charts were generated from directory processing.", file=sys.stderr)


# --- Assemble and print/save the final output ---

if not use_stdin and not args.bar_mode and generated_any_chart:

    final_html_lines=['<!DOCTYPE html>','<html lang="en">','<head>','  <meta charset="utf-8">',
           '  <meta name="viewport" content="width=device-width, initial-scale=1">',
           '  <title>Aggregated Fund Series Charts</title>',
           '  <style>',
           '    body { font-family: Arial, sans-serif; margin: 10px; padding: 0; background-color: #f4f4f4; }',
           '    iframe { border: 1px solid #ccc; margin-bottom: 10px; width:100%; height:850px; }',
           '    .chart-container { margin-bottom: 20px; padding:10px; background-color: #fff; border: 1px solid #ddd; border-radius: 5px;}',
           '    #fund-selector-container { display: flex; align-items: flex-start; background-color: #fff; padding: 15px; margin-bottom: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }',
           '    #global-fund-selector { flex-grow: 1; min-height: 100px; max-height: 150px; border: 1px solid #ccc; border-radius: 4px; padding: 8px; margin-right: 10px; }',
           '    #fund-selector-buttons { display: flex; flex-direction: column; }',
           '    .selector-button { padding: 10px 15px; border-radius: 4px; border: none; cursor: pointer; font-size: 14px; color: white; margin-bottom: 10px; width: 150px; text-align: center;}',
           '    #apply-fund-selection { background-color: #5cb85c; }',
           '    #apply-fund-selection:hover { background-color: #4cae4c; }',
           '    #reset-fund-selection { background-color: #d9534f; }',
           '    #reset-fund-selection:hover { background-color: #c9302c; }',
           '  </style>',
           '<script src="https://cdn.plot.ly/plotly-3.0.1.min.js"></script>'] # Plotly CDN

    if internal_only: # Add main JS logic to head for single-page mode
        final_html_lines.append(styling_constants_js)
        final_html_lines.append(selection_and_hover_js_logic)

    final_html_lines.extend(['</head>','<body>'])
    final_html_lines.append('<h1 style="text-align:center; margin-top:20px; margin-bottom:20px;">Aggregated Fund Series Charts</h1>')

    if all_unique_fund_names:
        final_html_lines.append('<div id="fund-selector-container">')
        final_html_lines.append('  <select id="global-fund-selector" multiple>')
        for fund_name in sorted(list(all_unique_fund_names)):
            json_string_value = json.dumps(fund_name)
            html_escaped_value = html.escape(json_string_value)
            final_html_lines.append(f'    <option value="{html_escaped_value}">{fund_name}</option>')
        final_html_lines.append('  </select>')
        final_html_lines.append('  <div id="fund-selector-buttons">')
        final_html_lines.append('    <button id="apply-fund-selection" class="selector-button">Apply Selection</button>')
        final_html_lines.append('    <button id="reset-fund-selection" class="selector-button" title="Clear fund selection">Reset Selection</button>')
        final_html_lines.append('  </div>')
        final_html_lines.append('</div>')

    if internal_only:
        for chart_html_part in chart_html_parts:
            final_html_lines.append('<div class="chart-container">')
            final_html_lines.append(chart_html_part)
            final_html_lines.append('</div>')

        internal_master_js = r"""
<script>
    // [SINGLE-PAGE MASTER JS] Loaded
    document.addEventListener('DOMContentLoaded', function() {
        console.log('[SINGLE-PAGE] DOMContentLoaded.');
        const globalFundSelector = document.getElementById('global-fund-selector');
        const applyFundSelectionButton = document.getElementById('apply-fund-selection');
        const resetFundSelectionButton = document.getElementById('reset-fund-selection');

        if (globalFundSelector) {
            console.log('[SINGLE-PAGE] Clearing globalFundSelector on DOMContentLoaded.');
            Array.from(globalFundSelector.options).forEach(opt => opt.selected = false);
        }

        function handleSelectionChange() {
            console.log('[SINGLE-PAGE] handleSelectionChange called.');
            const selectedOptionsRaw = globalFundSelector ? Array.from(globalFundSelector.selectedOptions).map(opt => opt.value) : [];
            const selectedFunds = selectedOptionsRaw.map(val => {
                try { return JSON.parse(val); } catch (e) { console.error('[SINGLE-PAGE] Error parsing option value:', val, e); return null; }
            }).filter(value => value !== null);
            console.log('[SINGLE-PAGE] Parsed selected funds:', selectedFunds);

            if (typeof updateAllChartsOnPage === 'function') {
                 updateAllChartsOnPage(selectedFunds);
            } else {
                console.error('[SINGLE-PAGE] updateAllChartsOnPage function not found.');
            }
        }

        if (applyFundSelectionButton) {
            applyFundSelectionButton.addEventListener('click', handleSelectionChange);
        }
        if (resetFundSelectionButton) {
            resetFundSelectionButton.addEventListener('click', function() {
                if (globalFundSelector) {
                    Array.from(globalFundSelector.options).forEach(opt => opt.selected = false);
                }
                handleSelectionChange();
            });
        }
        console.log('[SINGLE-PAGE] Applying initial (empty) selection.');
        handleSelectionChange();
    });
</script>
"""
        final_html_lines.append(internal_master_js)

    else: # For file output mode (not internal_only) - uses iframes
        fund_selector_master_js = r"""
<script>
    // [PARENT IFRAME MASTER JS] Loaded
    document.addEventListener('DOMContentLoaded', function() {
        console.log('[PARENT IFRAME] DOMContentLoaded.');
        const globalFundSelector = document.getElementById('global-fund-selector');
        const applyFundSelectionButton = document.getElementById('apply-fund-selection');
        const resetFundSelectionButton = document.getElementById('reset-fund-selection');
        const iframes = document.querySelectorAll('iframe');
        console.log('[PARENT IFRAME] Found iframes:', iframes.length);

        if (globalFundSelector) {
            console.log('[PARENT IFRAME] Clearing globalFundSelector on DOMContentLoaded.');
            Array.from(globalFundSelector.options).forEach(opt => opt.selected = false);
        }

        function dispatchSelectionUpdate() {
            console.log('[PARENT IFRAME] dispatchSelectionUpdate called.');
            const selectedOptionsRaw = globalFundSelector ? Array.from(globalFundSelector.selectedOptions).map(opt => opt.value) : [];
            const selectedFunds = selectedOptionsRaw.map(val => {
                try { return JSON.parse(val); } catch (e) { console.error('[PARENT IFRAME] Error parsing option value:', val, e); return null; }
            }).filter(value => value !== null);
            console.log('[PARENT IFRAME] Parsed selected funds for dispatch:', selectedFunds);

            const message = { type: 'fundSelectionUpdate', selectedFunds: selectedFunds };
            iframes.forEach((iframe, index) => {
                if (iframe.contentWindow) {
                    iframe.contentWindow.postMessage(message, '*');
                }
            });
        }

        if (applyFundSelectionButton) {
            applyFundSelectionButton.addEventListener('click', dispatchSelectionUpdate);
        }
        if (resetFundSelectionButton) {
            resetFundSelectionButton.addEventListener('click', function() {
                if (globalFundSelector) {
                    Array.from(globalFundSelector.options).forEach(opt => opt.selected = false);
                }
                dispatchSelectionUpdate();
            });
        }

        window.addEventListener('message', function(event) {
            if (event.data && event.data.type === 'iframeReady') {
                console.log(`[PARENT IFRAME] Received iframeReady message from: ${event.data.title}`);
                if (event.source && globalFundSelector) {
                    const selectedOptionsRaw = Array.from(globalFundSelector.selectedOptions).map(opt => opt.value);
                    const selectedFunds = selectedOptionsRaw.map(val => {
                        try { return JSON.parse(val); } catch (e) { return null; }
                    }).filter(value => value !== null);
                    event.source.postMessage({ type: 'fundSelectionUpdate', selectedFunds: selectedFunds }, '*');
                }
            }
        });

        console.log('[PARENT IFRAME] Dispatching initial (empty) selection update after DOMContentLoaded setup.');
        dispatchSelectionUpdate();
    });
</script>
"""
        final_html_lines.append(fund_selector_master_js)
        for chart_info in html_file_outputs_for_index:
            final_html_lines.append(f'<iframe title="{html.escape(chart_info["title"])}" src="{html.escape(chart_info["content"])}" sandbox="allow-scripts allow-same-origin"></iframe>')

    final_html_lines.extend(['</body>','</html>'])

    if internal_only:
        print("\n".join(final_html_lines))
        print(f"Printed single aggregated HTML page to stdout.", file=sys.stderr)
    else:
        idxp=os.path.join(args.output_dir,'fund_series_charts_index.html')
        with open(idxp,'w',encoding='utf-8') as f:f.write("\n".join(index_html_lines))
        print(f"Generated index at {idxp}")

elif not use_stdin and not args.bar_mode and not generated_any_chart:
     print("No charts to include in master index (no charts were generated).", file=sys.stderr)

