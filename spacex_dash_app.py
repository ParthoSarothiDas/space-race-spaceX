# spacex_dash_app.py
import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px

# --- Read dataset ---
# Make sure spacex_launch_dash.csv is in the same directory
spacex_df = pd.read_csv("spacex_launch_dash.csv")

# Basic sanity: ensure expected column names exist
expected_cols = {'Launch Site', 'Payload Mass (kg)', 'class', 'Booster Version Category'}
if not expected_cols.issubset(set(spacex_df.columns)):
    raise ValueError(f"Dataset is missing expected columns. Found columns: {spacex_df.columns.tolist()}")

# Compute payload min & max for range slider defaults
min_payload = int(spacex_df['Payload Mass (kg)'].min())
max_payload = int(spacex_df['Payload Mass (kg)'].max())

# Prepare dropdown options (include "All Sites" as 'ALL')
launch_sites = sorted(spacex_df['Launch Site'].unique().tolist())
dropdown_options = [{'label': 'All Sites', 'value': 'ALL'}] + [
    {'label': site, 'value': site} for site in launch_sites
]

# --- Dash app layout ---
app = dash.Dash(__name__)
app.title = "SpaceX Launch Dashboard"

app.layout = html.Div(children=[
    html.H1(
        "SpaceX Launch Records Dashboard",
        style={'textAlign': 'center', 'font-family': 'Arial', 'margin-bottom': '10px'}
    ),

    # Dropdown for Launch Site selection
    html.Div([
        html.Label("Select Launch Site:", style={'font-weight': 'bold'}),
        dcc.Dropdown(
            id='site-dropdown',
            options=dropdown_options,
            value='ALL',  # default ALL
            placeholder="Select a Launch Site here",
            searchable=True
        ),
    ], style={'width': '50%', 'margin': '0 auto'}),

    html.Br(),

    # Pie chart for success counts
    html.Div([
        dcc.Graph(id='success-pie-chart')
    ], style={'width': '80%', 'margin': '0 auto'}),

    html.Hr(),

    # Range slider for payload selection
    html.Div([
        html.Label("Select Payload Range (kg):", style={'font-weight': 'bold'}),
        dcc.RangeSlider(
            id='payload-slider',
            min=0,
            max=10000,
            step=1000,
            value=[min_payload, max_payload],
            marks={i: str(i) for i in range(0, 10001, 2000)},
            tooltip={"placement": "bottom", "always_visible": False}
        ),
        html.Div(id='payload-range-display', style={'textAlign': 'center', 'marginTop': '8px'})
    ], style={'width': '80%', 'margin': '0 auto'}),

    html.Br(),

    # Scatter chart for payload vs. success colored by booster version
    html.Div([
        dcc.Graph(id='success-payload-scatter-chart')
    ], style={'width': '90%', 'margin': '0 auto'}),

    html.Br(),
    html.Div(
        "Notes: Use the dropdown to filter launch site(s). Use the payload slider to limit payload mass range. "
        "Pie chart shows success counts; scatter shows payload vs. outcome (class = 1 success, 0 failure) colored by Booster Version.",
        style={'textAlign': 'center', 'color': '#555', 'fontSize': '14px', 'width': '80%', 'margin': '0 auto'}
    )
], style={'font-family': 'Verdana, Arial, sans-serif', 'padding': '20px'})


# --- Callbacks ---

# Callback for updating the pie chart based on selected launch site
@app.callback(
    Output(component_id='success-pie-chart', component_property='figure'),
    Input(component_id='site-dropdown', component_property='value')
)
def update_pie_chart(selected_site):
    """
    If 'ALL' selected -> pie chart of total successful launches per launch site.
    If a specific site selected -> pie chart of success vs failure counts for that site.
    """
    if selected_site == 'ALL':
        # Group by Launch Site and count successes (class == 1)
        success_counts = spacex_df[spacex_df['class'] == 1].groupby('Launch Site').size().reset_index(name='success_count')
        # If no successes, still produce a pie (Plotly handles empty gracefully)
        fig = px.pie(
            success_counts,
            values='success_count',
            names='Launch Site',
            title='Total Successful Launches by Site (All Sites)',
        )
    else:
        # Filter for selected site
        filtered_df = spacex_df[spacex_df['Launch Site'] == selected_site]
        # Count success vs failure
        outcome_counts = filtered_df['class'].value_counts().reset_index()
        outcome_counts.columns = ['class', 'count']
        # Map class 0/1 to readable labels
        outcome_counts['outcome'] = outcome_counts['class'].map({1: 'Success', 0: 'Failure'})
        fig = px.pie(
            outcome_counts,
            values='count',
            names='outcome',
            title=f"Launch Outcomes at Site: {selected_site}",
        )

    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20))
    return fig


# Callback for displaying chosen payload range text
@app.callback(
    Output(component_id='payload-range-display', component_property='children'),
    Input(component_id='payload-slider', component_property='value')
)
def display_payload_range(value):
    return f"Selected payload range: {value[0]} kg — {value[1]} kg"


# Callback for updating the scatter plot based on site selection and payload slider
@app.callback(
    Output(component_id='success-payload-scatter-chart', component_property='figure'),
    [
        Input(component_id='site-dropdown', component_property='value'),
        Input(component_id='payload-slider', component_property='value')
    ]
)
def update_scatter_chart(selected_site, payload_range):
    """
    Render scatter plot of Payload Mass (kg) vs class, color-coded by Booster Version Category.
    Apply site filter (if not ALL) and payload range filter.
    """
    low, high = payload_range
    # Base filter by payload range
    mask = (spacex_df['Payload Mass (kg)'] >= low) & (spacex_df['Payload Mass (kg)'] <= high)
    filtered_df = spacex_df[mask]

    # Apply site filter if needed
    if selected_site != 'ALL':
        filtered_df = filtered_df[filtered_df['Launch Site'] == selected_site]

    # If filtered_df is empty, return an empty figure with informative annotation
    if filtered_df.empty:
        fig = px.scatter(
            pd.DataFrame({'Payload Mass (kg)': [], 'class': [], 'Booster Version Category': []}),
            x='Payload Mass (kg)', y='class'
        )
        fig.update_layout(
            title="No data for the selected combination of site & payload range",
            xaxis_title="Payload Mass (kg)",
            yaxis_title="Launch Outcome (class: 1=Success, 0=Failure)"
        )
        fig.add_annotation(
            text="No records match filters",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        return fig

    # Create scatter
    fig = px.scatter(
    filtered_df,
    x='Payload Mass (kg)',
    y='class',
    color='Booster Version Category',
    hover_data=['Launch Site', 'Flight Number', 'Payload Mass (kg)', 'Booster Version'],
    title="Payload vs. Outcome (class) — colored by Booster Version",
    labels={'class': 'Outcome (0=Failure, 1=Success)'}
    )


    # Make y-axis show 0 and 1 clearly
    fig.update_yaxes(tickmode='array', tickvals=[0, 1], ticktext=['Failure (0)', 'Success (1)'])
    fig.update_layout(margin=dict(l=40, r=20, t=60, b=40))
    return fig


# --- Run server ---
if __name__ == '__main__':
    app.run(debug=True)
