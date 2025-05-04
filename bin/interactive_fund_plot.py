import os
import re
import glob
import argparse
import pandas as pd
import plotly.graph_objs as go

# Parse command-line arguments
parser = argparse.ArgumentParser(
    description='Generate interactive fund series charts from CSV files and an embedded-master index.'
)
parser.add_argument('-t', dest='input_dir', default='.', help='Directory containing fund_tables_<n>.csv')
parser.add_argument('-r', dest='output_dir', default='.', help='Directory to save HTML files and master index')
args = parser.parse_args()

# Helper to find and sort CSV files by numeric suffix
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
    exit(1)

# Ensure output directory exists
os.makedirs(args.output_dir, exist_ok=True)

# JavaScript to bold legend and thicken line on hover
hover_js = '''<script>
(function() {
  document.querySelectorAll('.plotly-graph-div').forEach(function(gd) {
    gd.on('plotly_hover', function(data) {
      var name = data.points[0].fullData.name;
      var ci = data.points[0].curveNumber;
      gd.querySelectorAll('.legendtext').forEach(function(el) {
        if (el.textContent === name) el.style.fontWeight='bold';
      });
      Plotly.restyle(gd, {'line.width':3}, [ci]);
    });
    gd.on('plotly_unhover', function() {
      gd.querySelectorAll('.legendtext').forEach(function(el) {
        el.style.fontWeight='normal';
      });
      Plotly.restyle(gd, {'line.width':2}, Array.from({length:gd.data.length}, (_,i)=>i));
    });
  });
})();
</script>'''

# Pandas read options
df_kwargs = dict(sep=';', decimal=',', skiprows=2, header=0,
                 parse_dates=[0], dayfirst=True, na_values=[''], encoding='latin1')

# Track generated HTML filenames
html_files = []

# Generate individual chart HTML files
for idx, fname in csv_files:
    csv_path = os.path.join(args.input_dir, fname)
    out_name = f'fund_series_chart_{idx}.html'
    out_path = os.path.join(args.output_dir, out_name)

    # Load and preprocess data
    df = pd.read_csv(csv_path, **df_kwargs)
    df.rename(columns={df.columns[0]: 'Date'}, inplace=True)
    df.dropna(axis=1, how='all', inplace=True)
    df.set_index('Date', inplace=True)
    full_idx = pd.date_range(df.index.min(), df.index.max(), freq='D')
    df = df.reindex(full_idx).interpolate()
    df.reset_index(inplace=True)
    df.rename(columns={'index': 'Date'}, inplace=True)

    # Build Plotly figure
    fig = go.Figure()
    for col in df.columns:
        if col == 'Date': continue
        fig.add_trace(go.Scatter(
            x=df['Date'], y=df[col], mode='lines', name=col,
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

    # Export HTML and inject hover JS
    html_str = fig.to_html(include_plotlyjs='cdn', full_html=True)
    final_html = html_str.replace('</body>', hover_js + '\n</body>')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(final_html)
    print(f"Saved {out_name}")
    html_files.append(out_name)

# Create master index embedding individual HTMLs via srcdoc iframes
index_path = os.path.join(args.output_dir, 'fund_series_charts.html')
lines = [
    '<!DOCTYPE html>', '<html lang="en">', '<head>',
    '  <meta charset="utf-8">',
    '  <meta name="viewport" content="width=device-width, initial-scale=1">',
    '  <title>Aggregated Fund Series Charts</title>',
    '</head>', '<body>'
]
for html_file in html_files:
    path = os.path.join(args.output_dir, html_file)
    with open(path, 'r', encoding='utf-8') as hf:
        content = hf.read().replace('"', '&quot;')
    # Embed via srcdoc
    lines.append(
        f'  <iframe srcdoc="{content}" '
        'style="width:100%; height:600px; border:none; margin-bottom:80px;"></iframe>'
    )
    lines.append('  <hr style="border:none; border-top:3px solid #ccc; margin:100px 0;">')
lines += ['</body>', '</html>']

with open(index_path, 'w', encoding='utf-8') as f:
    f.write("\n".join(lines))
print(f"Generated master index with embedded charts at {index_path}")
