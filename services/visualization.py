"""
visualization.py
------------------
Builds Plotly figures on demand based on user-selected chart type and
columns. Returns figures as plain dicts (data + layout) that the
frontend feeds straight into Plotly.newPlot().
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .cleaning import detect_column_types
from .json_utils import to_jsonable

TEMPLATE = "plotly_white"
COLOR_SEQUENCE = px.colors.qualitative.Set2


class ChartError(ValueError):
    """Raised when the requested chart cannot be built from the given columns."""
    pass


def _fig_to_payload(fig: go.Figure) -> dict:
    fig.update_layout(
        template=TEMPLATE,
        margin=dict(l=40, r=20, t=50, b=40),
        font=dict(family="Inter, -apple-system, sans-serif", size=12, color="#1f2937"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    payload = {
        "data": [trace.to_plotly_json() for trace in fig.data],
        "layout": fig.layout.to_plotly_json(),
    }
    # Plotly figures often contain numpy arrays/scalars (e.g. histogram bins,
    # correlation matrices) which the default Flask JSON encoder can't
    # serialize - round-trip through our NumPy-aware encoder to normalize them.
    return to_jsonable(payload)


def build_chart(df: pd.DataFrame, chart_type: str, x=None, y=None, color=None, agg="mean") -> dict:
    types = detect_column_types(df)
    numeric_cols = set(types["numeric"])

    if chart_type == "bar":
        if not x or x not in df.columns:
            raise ChartError("Please select a column for the X axis.")
        if y and y in df.columns:
            if y not in numeric_cols:
                raise ChartError(f"'{y}' must be a numeric column to aggregate for a bar chart.")
            grouped = df.groupby(x)[y].agg(agg).sort_values(ascending=False).head(25).reset_index()
            fig = px.bar(grouped, x=x, y=y, color=x, color_discrete_sequence=COLOR_SEQUENCE,
                         title=f"{agg.title()} of {y} by {x}")
        else:
            counts = df[x].value_counts().head(25).reset_index()
            counts.columns = [x, "count"]
            fig = px.bar(counts, x=x, y="count", color=x, color_discrete_sequence=COLOR_SEQUENCE,
                         title=f"Count of records by {x}")
        fig.update_layout(showlegend=False)

    elif chart_type == "line":
        if not x or not y or x not in df.columns or y not in df.columns:
            raise ChartError("Please select both X and Y columns for a line chart.")
        if y not in numeric_cols:
            raise ChartError(f"'{y}' must be numeric for a line chart.")
        plot_df = df[[x, y]].dropna().sort_values(x)
        if plot_df.empty:
            raise ChartError("No data available to plot after removing missing values.")
        fig = px.line(plot_df, x=x, y=y, markers=True, title=f"{y} over {x}",
                      color_discrete_sequence=COLOR_SEQUENCE)

    elif chart_type == "pie":
        if not x or x not in df.columns:
            raise ChartError("Please select a column for the pie chart.")
        vc = df[x].value_counts()
        top = vc.head(8)
        if len(vc) > 8:
            other_sum = vc.iloc[8:].sum()
            top = pd.concat([top, pd.Series({"Other": other_sum})])
        fig = px.pie(names=top.index.astype(str), values=top.values,
                     title=f"Distribution of {x}", color_discrete_sequence=COLOR_SEQUENCE, hole=0.35)

    elif chart_type == "histogram":
        if not x or x not in df.columns:
            raise ChartError("Please select a numeric column for the histogram.")
        if x not in numeric_cols:
            raise ChartError(f"'{x}' must be a numeric column for a histogram.")
        fig = px.histogram(df, x=x, nbins=30, title=f"Distribution of {x}",
                           color_discrete_sequence=COLOR_SEQUENCE)

    elif chart_type == "scatter":
        if not x or not y or x not in df.columns or y not in df.columns:
            raise ChartError("Please select both X and Y columns for a scatter plot.")
        if x not in numeric_cols or y not in numeric_cols:
            raise ChartError("Both X and Y must be numeric columns for a scatter plot.")
        color_arg = color if (color and color in df.columns) else None
        fig = px.scatter(df, x=x, y=y, color=color_arg, title=f"{y} vs {x}",
                         color_discrete_sequence=COLOR_SEQUENCE, opacity=0.75)

    elif chart_type == "heatmap":
        num_df = df[types["numeric"]]
        if num_df.shape[1] < 2:
            raise ChartError("Need at least two numeric columns to build a correlation heatmap.")
        corr = num_df.corr(numeric_only=True).round(2)
        fig = px.imshow(corr, text_auto=True, color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
                        title="Correlation Heatmap", aspect="auto")

    else:
        raise ChartError(f"Unknown chart type: {chart_type}")

    return _fig_to_payload(fig)
