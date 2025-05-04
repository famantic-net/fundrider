import os
import re
import glob
import argparse
import pandas as pd
import plotly.graph_objs as go

# Parse command-line arguments
parser = argparse.ArgumentParser(
    description='Generate interactive fund series charts from all CSV files and an index page with iframes.'
)
parser.add_argument(
    '-t', dest='input_dir', default='.',
    help='Directory to read CSV files from'
)
parser.add_argument(
    '-r', dest='output_dir', default='.',
    help='Directory to save the resulting HTML files and index'
)
args = parser.parse_args()

# Discover all CSV files matching fund_tables_<n>.csv
def find_csv_files(input_dir):
    pattern = re.compile(r'fund_tables_(\d+)\.csv$')
    files = []
    for fname in os.listdir(input_dir):
        m = pattern.match(fname)
        if m:
            idx = int(m.group(1))
            files.append((idx, fname))
    files.sort(key=lambda x: x[0])
    return files

csv_files = find_csv_files(args.input_dir)
if not csv_files:
    print(f"No CSV files found matching 'fund_tables_<n>.csv' in {args.input_dir}")
    exit(1)

# JavaScript snippet for hover: bold legend and thicken line
hover_js = '''<script>
(function() {
    document.querySelectorAll('.plotly-graph-div').forEach(function(gd) {
        gd.on('plotly_hover', function(data) {
            var traceName = data.points[0].fullData.name;
            var ci = data.points[0].curveNumber;
            gd.querySelectorAll('.legendtext').forEach(function(item) {
                if (item.textContent === traceName) item.style.fontWeight = 'bold';
            });
            Plotly.restyle(gd, { 'line.width': 3 }, [ci]);
        });
        gd.on('plotly_unhover', function(data) {
            gd.querySelectorAll('.legendtext').forEach(function(item) {
                item.style.fontWeight = 'normal';
            });
            Plotly.restyle(gd, { 'line.width': 2 }, Array.from({ length: gd.data.length }, (_,i) => i));
        });
    });
})();
</script>'''

# Ensure output directory exists
os.makedirs(args.output_dir, exist_ok=True)

# Collect generated HTML filenames
generated_htmls = []

# Process each CSV and generate individual HTML
for idx, fname in csv_files:
    csv_path = os.path.join(args.input_dir, fname)
    out_name = f'fund_series_chart_{idx}.html'
    out_path = os.path.join(args.output_dir, out_name)

    # Read and preprocess the CSV
    df = pd.read_csv(
        csv_path,
        sep=';', decimal=',', skiprows=2,
        header=0, parse_dates=[0], dayfirst=True,
        na_values=[''], encoding='latin1'
    )
    df.rename(columns={df.columns[0]: 'Date'}, inplace=True)
    df.dropna(axis=1, how='all', inplace=True)
    df.set_index('Date', inplace=True)
    full_idx = pd.date_range(start=df.index.min(), end=df.index.max(), freq='D')
    df = df.reindex(full_idx).interpolate()
    df.reset_index(inplace=True)
    df.rename(columns={'index': 'Date'}, inplace=True)

    # Build Plotly figure
    fig = go.Figure()
    for col in df.columns:
        if col == 'Date':
            continue
        fig.add_trace(
            go.Scatter(
                x=df['Date'], y=df[col], mode='lines', name=col,
                line=dict(width=2),
                hovertemplate=(
                    '<b>Series:</b> %{fullData.name}<br>'
                    '<b>Date:</b> %{x|%Y-%m-%d}<br>'
                    '<b>Value:</b> %{y:.3f}<extra></extra>'
                )
            )
        )
    fig.update_layout(
        title=f'Fund Series Chart {idx}',
        xaxis_title='Date', yaxis_title='Value',
        hovermode='closest', template='plotly_white'
    )

    # Generate HTML and inject hover JS
    html_str = fig.to_html(include_plotlyjs='cdn', full_html=True)
    final_html = html_str.replace('</body>', hover_js + '\n</body>')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(final_html)
    print(f"Saved chart for {fname} to {out_path}")
    generated_htmls.append(out_name)

# Create index HTML embedding each chart via iframes
index_path = os.path.join(args.output_dir, 'fund_series_charts.html')
index_lines = [
    '<!DOCTYPE html>',
    '<html lang="en">',
    '<head>',
    '  <meta charset="utf-8">',
    '  <meta name="viewport" content="width=device-width, initial-scale=1">',
    '  <title>Aggregated Fund Series Charts</title>',
    '</head>',
    '<body>'
]
for html_file in generated_htmls:
    index_lines.append(
        f'  <iframe src="{html_file}" style="width:100%; height:600px; border:none; margin-bottom:80px;"></iframe>'
    )
    index_lines.append(
        '  <hr style="border:none; border-top:3px solid #ccc; margin:100px 0;">'
    )
index_lines += ['</body>', '</html>']
with open(index_path, 'w', encoding='utf-8') as f:
    f.write("\n".join(index_lines))
print(f"Generated index with iframes at {index_path}")
