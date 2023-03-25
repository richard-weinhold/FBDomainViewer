import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.offline import plot

def create_fb_domain_plot(fb_domain, exchange, zones, lta_domain, show_plot=True, filepath=None):
    """Create FlowBased Domain plot. 

    This is a copy of the previous :meth:`~pomato.visualization.FBDomain.create_fbmc_figure`
    using plotly instead of matplotlib. This allows for proper integration in the Dashboard
    functionality including interaction with the geo plot. 

    Input argument remains an instance of :class:`~pomato.visualization.FBDomain` which can be
    created by utilizing :meth:`~pomato.visualization.FBDomainPlots` module. 
    """
    fig = go.Figure()
    n0_lines_x, n0_lines_y = [], []
    n1_lines_x, n1_lines_y = [], []
    iva_x, iva_y = [], []
    hover_data_n0, hover_data_n1, hover_data_iva = [], [], []

    hover_points = len(fb_domain.domain_equations[0][1])
    tmp = fb_domain.domain_data.reset_index(drop=True)
    for i in tmp[tmp.co == "basecase"].index:
        n0_lines_x.extend(fb_domain.domain_equations[i][0])
        n0_lines_y.extend(fb_domain.domain_equations[i][1])
        n0_lines_x.append(None)
        n0_lines_y.append(None)
        data = [tmp.loc[i, "cb"], tmp.loc[i, "co"], tmp.loc[i, "ram"]]
        hover_data_n0.append(np.vstack([[data for n in range(0, hover_points)], [None]*len(data)]))
    
    for i in tmp[(tmp.iva > 0)].index:
        iva_x.extend(fb_domain.domain_equations[i][0])
        iva_y.extend(fb_domain.domain_equations[i][1])
        iva_x.append(None)
        iva_y.append(None)
        data = [tmp.loc[i, "cb"], tmp.loc[i, "co"], tmp.loc[i, "ram"]]
        hover_data_iva.append(np.vstack([[data for n in range(0, hover_points)], [None]*len(data)]))
    
    for i in tmp[(tmp.co != "basecase")&(tmp.iva == 0)].index:
        n1_lines_x.extend(fb_domain.domain_equations[i][0])
        n1_lines_y.extend(fb_domain.domain_equations[i][1])
        n1_lines_x.append(None)
        n1_lines_y.append(None)
        data = [tmp.loc[i, "cb"], tmp.loc[i, "co"], tmp.loc[i, "ram"]]
        hover_data_n1.append(np.vstack([[data for n in range(0, hover_points)], [None]*len(data)]))
    
    hovertemplate = "<br>".join(
        [
            "cb: %{customdata[0]}", 
            "co: %{customdata[1]}", 
            "ram: %{customdata[2]:.2f}"
        ]) + "<extra></extra>"

    if len(hover_data_n0) > 0:
        fig.add_trace(
            go.Scatter(
                x=n0_lines_x, y=n0_lines_y, name='N-0 Constraints',
                line = dict(width = 1.5, color="dimgray"),
                mode="lines",
                customdata=np.vstack(hover_data_n0),
                hovertemplate=hovertemplate
            )
        )

    if len(hover_data_iva) > 0:
        fig.add_trace(
            go.Scatter(
                x=iva_x, y=iva_y, name='IVA',
                line = dict(dash='dash', width = 1.5, color="royalblue"),
                customdata=np.vstack(hover_data_iva),
                hovertemplate=hovertemplate
            )
        )
    if len(hover_data_n1) > 0:
        fig.add_trace(
            go.Scatter(
                x=n1_lines_x, y=n1_lines_y, name='N-1 Constraints',
                line = dict(width = 1.5, color="lightgray"),
                opacity=0.8,
                customdata=np.vstack(hover_data_n1),
                hovertemplate=hovertemplate
            )
        )
    fig.add_trace(
            go.Scatter(
                x=fb_domain.feasible_region_vertices[:, 0], 
                y=fb_domain.feasible_region_vertices[:, 1],
                line = dict(width = 1, color="red"),
                opacity=1, name=f"FB Domain",
                mode='lines', hoverinfo="none"
            )
        )
    
    # exchange.set_index(["from", "to"], inplace=True)
    for col, name in [("Flow", "Market Outcome (inkl. ELI)"), ("FlowFB", "FB Market Outcome")]:
        nex_x = exchange.loc[tuple(fb_domain.domain_x), col] - exchange.loc[tuple(fb_domain.domain_x[::-1]), col]
        nex_y = exchange.loc[tuple(fb_domain.domain_y), col] - exchange.loc[tuple(fb_domain.domain_y[::-1]), col]
        fig.add_trace(go.Scatter(x=[nex_x], y=[nex_y], mode="markers", line=dict(width = 1, color="red"), name=name))
    
    if isinstance(lta_domain, pd.DataFrame):
        fig.add_trace(
            go.Scatter(x=lta_domain.x, y=lta_domain.y, name='LTA Domain', mode="lines", opacity=0.8,
                        line=dict(width=1.5, color="cyan")
                        )
            )

    fig.update_layout(
        xaxis_range=[fb_domain.x_min, fb_domain.x_max],
        yaxis_range=[fb_domain.y_min, fb_domain.y_max],
        template='simple_white',
        hovermode="closest",
        xaxis_title=" > ".join(fb_domain.domain_x),
        yaxis_title=" > ".join(fb_domain.domain_y),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
        )
    )


    if filepath:
        fig.write_html(str(filepath))
    if show_plot:
        plot(fig)
    else:
        return fig
