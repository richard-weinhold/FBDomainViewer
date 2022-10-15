import numpy as np
import plotly.graph_objects as go
from plotly.offline import plot
from FBMCViewer.fbmc_data import lta_constraints
import cvxpy as cp


def sort_vertices(vertices_x,vertices_y):
    vertices_sorted = []
    for idx in range(0, len(vertices_x)):
        radius = np.sqrt(np.power(vertices_y[idx], 2) + np.power(vertices_x[idx], 2))
        if vertices_x[idx] >= 0 and vertices_y[idx] >= 0:
            vertices_sorted.append([vertices_x[idx], vertices_y[idx],
                               np.arcsin(vertices_y[idx]/radius)*180/(2*np.pi)])
        elif vertices_x[idx] < 0 and vertices_y[idx] > 0:
            vertices_sorted.append([vertices_x[idx], vertices_y[idx],
                               180 - np.arcsin(vertices_y[idx]/radius)*180/(2*np.pi)])
        elif vertices_x[idx] <= 0 and vertices_y[idx] <= 0:
            vertices_sorted.append([vertices_x[idx], vertices_y[idx],
                               180 - np.arcsin(vertices_y[idx]/radius)*180/(2*np.pi)])
        elif vertices_x[idx] > 0 and vertices_y[idx] < 0:
            vertices_sorted.append([vertices_x[idx], vertices_y[idx],
                               360 + np.arcsin(vertices_y[idx]/radius)*180/(2*np.pi)])
    from operator import itemgetter
    vertices_sorted = sorted(vertices_sorted, key=itemgetter(2))
    
    ## Add first element to draw complete circle
    vertices_sorted.append(vertices_sorted[0])
    vertices_sorted = np.array(vertices_sorted)   
    return vertices_sorted[:, 0], vertices_sorted[:, 1]

def lta_bounds(lta, zones, domain_x, domain_y):
    domain_x = ["BE", "FR"]
    domain_y = ["DE", "FR"]
    lta_constr = lta_constraints(lta, zones)
    A = lta_constr.loc[:, zones].values
    b = lta_constr.lta.values
    domain_x_indices = [zones.index(z) for z in domain_x]
    domain_y_indices = [zones.index(z) for z in domain_y]
    ex = cp.Variable(len(b))
    netpos = cp.Variable(len(zones))
    
    print(f"LTA Limits for {'>'.join(domain_x)} and {'>'.join(domain_y)}")
    x,y = [],[]
    
    for i in [1, -1]:
        constraints = [
            # sum(netpos) == 0, 
            netpos[:1] == 0, 
            ex <= b,
            ex >= 0,
            # sum(netpos[domain_x_indices]) == 0,
            # sum(netpos[domain_y_indices]) == 0,
            netpos == A.T@ex
            ]
        obj = i*netpos[domain_x_indices]@(np.array([1, -1])) 
        objective = cp.Maximize(obj)
        prob = cp.Problem(objective, constraints)
        prob.solve()
        x.append(netpos[domain_x_indices[0]].value)
        y.append(0)
            
    for i in [1, -1]:
        constraints = [
            # sum(netpos) == 0, 
            netpos[:1] == 0, 
            ex <= b,
            ex >= 0,
            # sum(netpos[domain_x_indices]) == 0,
            # sum(netpos[domain_y_indices]) == 0,
            netpos == A.T@ex
            ]
        
        obj = i*netpos[domain_y_indices]@(np.array([1, -1])) 
        objective = cp.Maximize(obj)
        prob = cp.Problem(objective, constraints)
        prob.solve()
        y.append(netpos[domain_y_indices[0]].value)
        x.append(0)
        print(netpos[domain_y_indices[0]].value)
    x,y = sort_vertices(x,y)
    
    return x,y

def create_fb_domain_plot(fb_domain, exchange, zones, lta=None, show_plot=True, filepath=None):
        """Create FlowBased Domain plot. 

        This is a copy of the previous :meth:`~pomato.visualization.FBDomain.create_fbmc_figure`
        using plotly instead of matplotlib. This allows for proper integration in the Dashboard
        functionality including interaction with the geo plot. 

        Input argument remains an instance of :class:`~pomato.visualization.FBDomain` which can be
        created by utilizing :meth:`~pomato.visualization.FBDomainPlots` module. 
        """
        # fb_domain = domain_plot
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
        
        hovertemplate = "<br>".join(["cb: %{customdata[0]}", 
                                     "co: %{customdata[1]}", 
                                     "ram: %{customdata[2]:.2f}"]) + "<extra></extra>"
        if len(hover_data_n0) > 0:
            fig.add_trace(
                go.Scatter(x=n0_lines_x, y=n0_lines_y, name='N-0 Constraints',
                        line = dict(width = 1.5, color="dimgray"),
                        mode="lines",
                        customdata=np.vstack(hover_data_n0),
                        hovertemplate=hovertemplate
                        )
                )

        if len(hover_data_iva) > 0:
            fig.add_trace(
                go.Scatter(x=iva_x, y=iva_y, name='IVA',
                        line = dict(dash='dash', width = 1.5, color="royalblue"),
                        customdata=np.vstack(hover_data_iva),
                        hovertemplate=hovertemplate
                        )
                )
            
        fig.add_trace(
            go.Scatter(x=n1_lines_x, y=n1_lines_y, name='N-1 Constraints',
                    line = dict(width = 1.5, color="lightgray"),
                    opacity=0.8,
                    customdata=np.vstack(hover_data_n1),
                    hovertemplate=hovertemplate

                        )
            )
        fig.add_trace(
                go.Scatter(x=fb_domain.feasible_region_vertices[:, 0], 
                            y=fb_domain.feasible_region_vertices[:, 1],
                            line = dict(width = 1, color="red"),
                            opacity=1, name=f"FB Domain",
                            mode='lines', hoverinfo="none"
                        )
                )
        
        # exchange.set_index(["from", "to"], inplace=True)
        nex_x = exchange.loc[tuple(fb_domain.domain_x), "exchange"] - exchange.loc[tuple(fb_domain.domain_x[::-1]), "exchange"]
        nex_y = exchange.loc[tuple(fb_domain.domain_y), "exchange"] - exchange.loc[tuple(fb_domain.domain_y[::-1]), "exchange"]
        fig.add_trace(go.Scatter(x=[nex_x], y=[nex_y], mode="markers", line=dict(width = 1, color="red"), name="Market Outcome"))
        
        if isinstance(lta, pd.DataFrame):
            x,y = lta_bounds(lta, zones, fb_domain.domain_x, fb_domain.domain_y)
            fig.add_trace(
                go.Scatter(x=x, y=y, name='LTA Domain', mode="lines", opacity=0.8,
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
        )

        if filepath:
            fig.write_html(str(filepath))
        if show_plot:
            plot(fig)
        else:
            return fig