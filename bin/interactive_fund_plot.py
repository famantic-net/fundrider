import os
import re
import sys
import argparse
import pandas as pd
import plotly.graph_objs as go

# Parse command-line arguments
parser = argparse.ArgumentParser(
    description='Generate fund series charts from CSVs; stdin support for single-table mode.'
)
parser.add_argument(
    '-t', dest='input_dir', default='.', help='Directory containing fund_tables_<n>.csv'
)
parser.add_argument(
    '-r', dest='output_dir', default='.', help='Directory to save HTML files and index, or use ":internal:" to output chart to STDOUT'
)
args = parser.parse_args()

# Modes
internal_only = (args.output_dir == ':internal:')
use_stdin = (args.input_dir == '.' and not sys.stdin.isatty())
if not internal_only and not use_stdin:
    os.makedirs(args.output_dir, exist_ok=True)

# JS hover snippet
debug_hover_js = '''<script>
(function() {
  document.querySelectorAll('.plotly-graph-div').forEach(function(gd) {
    gd.on('plotly_hover', function(data) {
      var name = data.points[0].fullData.name;
      var ci = data.points[0].curveNumber;
      gd.querySelectorAll('.legendtext').forEach(el => { if(el.textContent===name) el.style.fontWeight='bold'; });
      Plotly.restyle(gd, {'line.width':3}, [ci]);
    });
    gd.on('plotly_unhover', function() {
      gd.querySelectorAll('.legendtext').forEach(el => el.style.fontWeight='normal');
      Plotly.restyle(gd, {'line.width':2}, Array.from({length:gd.data.length}, (_,i)=>i));
    });
  });
})();
</script>'''

# Common pandas options
df_kwargs = dict(
    sep=';', decimal=',', skiprows=2, header=0,
    parse_dates=[0], dayfirst=True, na_values=[''], encoding='latin1'
)

# Single-input from STDIN mode
if use_stdin:
    # Read single CSV from stdin
    df = pd.read_csv(sys.stdin, **df_kwargs)
    df.rename(columns={df.columns[0]:'Date'}, inplace=True)
    df.dropna(axis=1, how='all', inplace=True)
    df.set_index('Date', inplace=True)
    full_idx = pd.date_range(df.index.min(), df.index.max(), freq='D')
    df = df.reindex(full_idx).interpolate()
    df.reset_index(inplace=True)
    df.rename(columns={'index':'Date'}, inplace=True)

    # Build figure
    fig = go.Figure()
    for col in df.columns:
        if col=='Date': continue
        fig.add_trace(go.Scatter(
            x=df['Date'], y=df[col], mode='lines', name=col,
            line=dict(width=2), hovertemplate=(
                '<b>Series:</b> %{fullData.name}<br>'
                '<b>Date:</b> %{x|%Y-%m-%d}<br>'
                '<b>Value:</b> %{y:.3f}<extra></extra>'
            )
        ))
    fig.update_layout(
        title='Fund Series Chart', xaxis_title='Date', yaxis_title='Value',
        hovermode='closest', template='plotly_white'
    )

    # Generate HTML
    html_str = fig.to_html(include_plotlyjs='cdn', full_html=True)
    chart_html = html_str.replace('</body>', debug_hover_js+'\n</body>')

    if internal_only:
        # Print to STDOUT
        print(chart_html)
    else:
        # Write single file
        out_file = os.path.join(args.output_dir, 'fund_series_chart.html')
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(chart_html)
        print(f"Saved {out_file}", file=sys.stderr)
    sys.exit(0)

# Directory mode: discover and sort CSVs
def find_csv_files(input_dir):
    pat = re.compile(r'fund_tables_(\d+)\.csv$')
    files = []
    for fname in os.listdir(input_dir):
        m = pat.match(fname)
        if m:
            idx = int(m.group(1))
            files.append((idx, fname))
    return sorted(files, key=lambda x: x[0])

csv_files = find_csv_files(args.input_dir)
if not csv_files:
    print(f"No CSV files matching 'fund_tables_<n>.csv' in {args.input_dir}")
    sys.exit(1)

# Track outputs
disk_html_files = []
internal_html = {}

# Process multiple CSVs
def process_file(idx, path):
    df = pd.read_csv(path, **df_kwargs)
    df.rename(columns={df.columns[0]:'Date'}, inplace=True)
    df.dropna(axis=1, how='all', inplace=True)
    df.set_index('Date', inplace=True)
    full_idx = pd.date_range(df.index.min(), df.index.max(), freq='D')
    df = df.reindex(full_idx).interpolate()
    df.reset_index(inplace=True)
    df.rename(columns={'index':'Date'}, inplace=True)

    fig = go.Figure()
    for col in df.columns:
        if col=='Date': continue
        fig.add_trace(go.Scatter(x=df['Date'], y=df[col], mode='lines', name=col,
            line=dict(width=2), hovertemplate=(
                '<b>Series:</b> %{fullData.name}<br>'
                '<b>Date:</b> %{x|%Y-%m-%d}<br>'
                '<b>Value:</b> %{y:.3f}<extra></extra>'
            )
        ))
    fig.update_layout(
        title=f'Fund Series Chart {idx}', xaxis_title='Date', yaxis_title='Value',
        hovermode='closest', template='plotly_white'
    )

    html_str = fig.to_html(include_plotlyjs='cdn', full_html=True)
    return html_str.replace('</body>', debug_hover_js+'\n</body>')

# Generate HTML for each file
for idx, fname in csv_files:
    path = os.path.join(args.input_dir, fname)
    chart_html = process_file(idx, path)
    if internal_only:
        internal_html[idx] = chart_html
        print(f"Stored chart {idx} internally", file=sys.stderr)
    else:
        out_name = f'fund_series_chart_{idx}.html'
        out_path = os.path.join(args.output_dir, out_name)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(chart_html)
        print(f"Saved {out_path}")
        disk_html_files.append(out_name)

# Output index
lines = [
    '<!DOCTYPE html>', '<html lang="en">', '<head>',
    '  <meta charset="utf-8">',
    '  <meta name="viewport" content="width=device-width, initial-scale=1">',
    '  <title>Aggregated Fund Series Charts</title>',
    '</head>', '<body>'
]
if internal_only:
    for idx, _ in csv_files:
        content = internal_html[idx].replace('"','&quot;')
        lines.append(f'<iframe srcdoc="{content}" style="width:100%; height:500px; border:none;"></iframe>')
        lines.append('<hr style="border:none; border-top:3px solid #ccc; margin:20px 0;">')
    print("\n".join(lines+['</body>','</html>']))
else:
    for name in disk_html_files:
        lines.append(f'<iframe src="{name}" style="width:100%; height:500px; border:none;"></iframe>')
        lines.append('<hr style="border:none; border-top:3px solid #ccc; margin:20px 0;">')
    lines += ['</body>', '</html>']
    index_path = os.path.join(args.output_dir, 'fund_series_charts.html')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    print(f"Generated index at {index_path}")
