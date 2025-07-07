import pandas as pd
import numpy as np
import plotly.graph_objects as go

def create_fb_domain_plot(fb_domain, exchange, zones, lta_domain, alpha, show_plot=True, filepath=None):
    """Create FlowBased Domain plot. 
    This is a copy from POMATO. 
    """
    fig = go.Figure()
    n0_lines_x, n0_lines_y = [], []
    n1_lines_x, n1_lines_y = [], []

    iva_x, iva_y = [], []
    hover_data_n0, hover_data_n1, hover_data_iva = [], [], []

    hover_points = len(fb_domain.domain_equations[0][1])
    tmp = fb_domain.domain_data.reset_index(drop=True)
    cond_basecase = tmp.co == "basecase"
    cond_iva = (tmp.iva > 0)

    for i in tmp[cond_basecase].index:
        n0_lines_x.extend(fb_domain.domain_equations[i][0])
        n0_lines_y.extend(fb_domain.domain_equations[i][1])
        n0_lines_x.append(None)
        n0_lines_y.append(None)
        data = [tmp.loc[i, "cb"], tmp.loc[i, "co"], tmp.loc[i, "tso"], tmp.loc[i, "ram"]]
        hover_data_n0.append(np.vstack([[data for n in range(0, hover_points)], [None]*len(data)]))
    
    for i in tmp[cond_iva].index:
        iva_x.extend(fb_domain.domain_equations[i][0])
        iva_y.extend(fb_domain.domain_equations[i][1])
        iva_x.append(None)
        iva_y.append(None)
        data = [tmp.loc[i, "cb"], tmp.loc[i, "co"], tmp.loc[i, "tso"], tmp.loc[i, "ram"]]
        hover_data_iva.append(np.vstack([[data for n in range(0, hover_points)], [None]*len(data)]))
    
    for i in tmp[(~cond_basecase)&(~cond_iva)].index:
        n1_lines_x.extend(fb_domain.domain_equations[i][0])
        n1_lines_y.extend(fb_domain.domain_equations[i][1])
        n1_lines_x.append(None)
        n1_lines_y.append(None)
        data = [tmp.loc[i, "cb"], tmp.loc[i, "co"], tmp.loc[i, "tso"], tmp.loc[i, "ram"]]
        hover_data_n1.append(np.vstack([[data for n in range(0, hover_points)], [None]*len(data)]))


    print("Anz N-1 Constraints", sum((~cond_basecase)&(~cond_iva)))
    print("Anz N-0 Constraints", sum(cond_basecase))

    hovertemplate = "<br>".join(
        [
            "cb: %{customdata[0]}", 
            "co: %{customdata[1]}", 
            "tso: %{customdata[2]}", 
            "ram: %{customdata[3]:.2f}"
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
    
    if len(hover_data_n1) > 0:
        fig.add_trace(
            go.Scatter(
                x=n1_lines_x, y=n1_lines_y, name='N-1 Constraints',
                line = dict(width = 1.5, color="lightgray"),
                mode="lines",
                customdata=np.vstack(hover_data_n1),
                hovertemplate=hovertemplate
            )
        )

    if len(hover_data_iva) > 0:
        fig.add_trace(
            go.Scatter(
                x=iva_x, 
                y=iva_y,
                name='IVA',
                mode ="lines",
                line = dict(dash='dash', width = 1.5, color="royalblue"),
                customdata=np.vstack(hover_data_iva),
                hovertemplate=hovertemplate
            )
        )
    

    fig.add_trace(
        go.Scatter(
            x=fb_domain.feasible_region_vertices[:, 0], 
            y=fb_domain.feasible_region_vertices[:, 1],
            line = dict(width = 1, color="red"),
            opacity=1, name="FB Domain",
            mode='lines', hoverinfo="none"
        )
    )
    
    # exchange.set_index(["from", "to"], inplace=True)
    for col, name in [("Flow", f"ELI MCP (Alpha={round(float(alpha), 3)})"), ("FlowFB", "FB MCP")]:
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
    return fig
