import plotly.express as px

def sector_heatmap(df):
    fig = px.treemap(
        df,
        path=["Stock"],
        values="Momentum",
        color="Momentum",
        color_continuous_scale="RdYlGn"
    )
    return fig