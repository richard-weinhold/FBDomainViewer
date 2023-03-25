
import cdd
import numpy as np
import pandas as pd
# from pypoman import compute_polytope_vertices
from scipy import spatial
from scipy.spatial.qhull import QhullError


def compute_polytope_vertices(A, b):
    """
    This is a copy of https://github.com/stephane-caron/pypoman/blob/master/pypoman/duality.py
    which unfortunately does not like to install with github actions. 
    
    Compute the vertices of a polytope given in halfspace representation by
    :math:`A x \\leq b`.
    Parameters
    ----------
    A : array, shape=(m, k)
        Matrix of halfspace representation.
    b : array, shape=(m,)
        Vector of halfspace representation.
    Returns
    -------
    vertices : list of arrays
        List of polytope vertices.

    """
    b = b.reshape((b.shape[0], 1))
    mat = cdd.Matrix(np.hstack([b, -A]), number_type='float')
    mat.rep_type = cdd.RepType.INEQUALITY
    P = cdd.Polyhedron(mat)
    g = P.get_generators()
    V = np.array(g)
    vertices = []
    for i in range(V.shape[0]):
        if V[i, 0] != 1:  # 1 = vertex, 0 = ray
            raise Exception("Polyhedron is not a polytope")
        elif i not in g.lin_set:
            vertices.append(V[i, 1:])
    return vertices


def domain_feasible_region_indices(A, b):
    """Determining the feasible region of the FB domain, utilizing a convexhull algorithm.

    Based on the 2D input argument A and vector b, the convex hull is used to find the indices
    of the linear inequations that define the inner feasible region of the domain. This
    implementation generall follows the matlab implementation on, without recovering the
    vertices explicitly (See
    https://www.mathworks.com/matlabcentral/fileexchange/30892-analyze-n-dimensional-polyhedra-in-terms-of-vertices-or-in-equalities).

    Returns
    -------
        indices : array of indices of A,b that define the domain's feasible region. 
    """
    A = np.array(A, dtype=float)
    b = np.array(b, dtype=float).reshape(len(b), 1)
    D = A/b
    k = spatial.ConvexHull(D) #pylint: disable=no-member
    return k.vertices

class FBDomain():
    """Individual FB Domain plot. 

    This class bundles all data of an individual domain plot
    and the plotting functionality. It gets instantiated 
    into the *fbmc_plots* of the :class:`~FBDomainPlots`
    
    Parameters
    ----------
    domain_information : dict 
        Dictionary with general domain information. 
    domain_equations : array
        Equations to be plottet in the domain.
    feasible_region_vertices : array
        Array of the domain's feasible region vertices.
    domain_data : pandas.DataFrame
        The raw data from which the plot is derived.
    """ 
    def __init__(self, domain_information, domain_equations, feasible_region_vertices, 
                domain_data, volume):

        self.timestep = domain_information["timestep"]
        self.domain_x = domain_information["domain_x"]
        self.domain_y = domain_information["domain_y"]
        if domain_information["filename_suffix"]:
            self.title = self.timestep + "_" + domain_information["filename_suffix"]
        else:
            self.title = self.timestep

        self.domain_equations = domain_equations
        self.feasible_region_vertices = feasible_region_vertices
        self.x_max, self.x_min = domain_information["plot_limits"][0]
        self.y_max, self.y_min = domain_information["plot_limits"][1]
        self.domain_data = domain_data
        self.volume = volume
    
class FBDomainPlots():
    """Create FB domain plots based on flowbased parameters.
    
    This module creates 2D plots of the flow based domain, derived from the 
    FB parameters created by :meth:`~pomato.fbmc.FBMCModule.create_flowbased_parameters`.

    The FB parameters are zonal PTDF and RAMs for each timestep, the number of zones
    defines the width of the matrix, the length is determined by the number of lines
    defined as cb (critical branch) and co (critical outages). 

    To create a 2D plot, the x and y axis represent commercial exchange between two market areas, 
    thereby the whole system remains balanced for each point in the graph. 
    The methods create the necessary data for each domain plot and stores them as an instance of 
    the :class:`~FBDomain` in the *fbmc_plots* attribute. 
    
    Parameters
    ----------
    wdir : pathlib.Path
        POMATO working directory.  
    data : :class:`~pomato.data.DataManagement`
        Instance of POMATO data management. 
    flowbased_parameters : pd.DataFrame 
        FB parameters, as derived from :class:`~pomato.fbmc.FBMCModule`.
    """  
    def __init__(self, zones, flowbased_parameters):
        self.zones = zones
        self.flowbased_parameters = flowbased_parameters

    def set_xy_limits_forall_plots(self):
        """For each fbmc plot object, set x and y limits"""
        print("Resetting x and y limits for all domain plots")
        x_min = min([plot.x_min for plot in self.fbmc_plots])
        x_max = max([plot.x_max for plot in self.fbmc_plots])
        y_min = min([plot.y_min for plot in self.fbmc_plots])
        y_max = max([plot.y_max for plot in self.fbmc_plots])

        plot_limits = (x_max, x_min, y_max, y_min)

        for plot in self.fbmc_plots:
            plot.x_min = x_min
            plot.x_max = x_max
            plot.y_min = y_min
            plot.y_max = y_max

    def zonal_ptdf_projection(self, domain_x, domain_y, A):
        """The zonal PTDF has to be projected into 2D to be visualized as a domain plot. 

        The input matrix A is projected into 2D. The x,y axis represent commercial exchange 
        between two market areas define in the domain_x and domain_y input arguments, 
        therefore are net zero.  

        """
        domain_idx = [[self.zones.index(zone[0]),
                        self.zones.index(zone[1])] for zone in [domain_x, domain_y]]
        A = np.vstack([np.dot(A[:, domain], np.array([1, -1])) for domain in domain_idx]).T
        return A

    def create_domain_plot(self, A, b, indices, plot_limits=None):
        """Create linear equations of the FB domain. 

        Create 2D equation from the 2D projection of the zonal PTDF, suitable to for a line plot in
        the form axis.plot(plot_equations[i][0], plot_equations[i][1]) for each linear inequation
        that represents a specific line under contingency.

        The indices represent a subset of equations to be plottet if the size of A is too high. 

        Parameters
        ----------
        A : np.array Projected zonal PTDF with width 2. b : np.array Vector of RAMs indices :
            list-like List of indices that compose the domain plot.

        Returns
        -------
        plot_equations : list of [[x1;x2],[y1;y2]] Each plot consists of two x and y coordinates.

        """
        # indices = plot_indices

        A = np.take(np.array(A), indices, axis=0)
        b = np.take(np.array(b), indices, axis=0)
        Ab = np.concatenate((np.array(A), np.array(b).reshape(len(b), 1)), axis=1)
        
        # Calculate two coordinates for a line plot -> Return X = [X1;X2], Y = [Y1,Y2]
        if plot_limits:
            ((x_max, x_min), (y_max, y_min)) = plot_limits
        else: 
            x_max, y_max = max(b)*2, max(b)*2
            x_min, y_min = -max(b)*2, -max(b)*2
        
        steps = 10
        eps = 1.001
        plot_equations = []
        plot_equations_error = []
        plot_indices = []
        plot_indices_error = []
        for index in range(0, len(Ab)):
            if any([a != 0 for a in Ab[index][:-1]]):
                x_coordinates = []
                y_coordinates = []
                if Ab[index][0] == 0:
                    x_coordinates = [x for x in np.linspace(x_min, x_max, steps)]
                    y_coordinates = [Ab[index][2]/ Ab[index][1] for x in x_coordinates]
                elif Ab[index][1] == 0:
                    y_coordinates = [y for y in np.linspace(y_min, y_max, steps)]
                    x_coordinates = [Ab[index][2]/ Ab[index][0] for y in y_coordinates]
                
                elif abs(Ab[index][1]/Ab[index][0]) > 1:
                    x_range_max = (Ab[index][2] - y_max*Ab[index][1])/Ab[index][0]
                    x_range_min = (Ab[index][2] - y_min*Ab[index][1])/Ab[index][0]
                    x_coordinates = [x for x in np.linspace(max(x_min, min(x_range_max, x_range_min)), min(x_max, max(x_range_max, x_range_min)), steps)]
                    y_coordinates = [(Ab[index][2] - x*Ab[index][0]) / Ab[index][1] for x in x_coordinates]
                else:
                    y_range_max = (Ab[index][2] - x_max*Ab[index][0])/Ab[index][1] 
                    y_range_min = (Ab[index][2] - x_min*Ab[index][0])/Ab[index][1] 
                    y_coordinates = [y for y in np.linspace(max(y_min, min(y_range_max, y_range_min)), min(y_max, max(y_range_max, y_range_min)), steps)]
                    x_coordinates = [(Ab[index][2] - y*Ab[index][1]) / Ab[index][0] for y in y_coordinates]
                
                condition_visible = (
                    all([(x <= x_max*eps) and (x >= x_min*eps) for x in x_coordinates]) and 
                    all([(y <= y_max*eps) and (y >= y_min*eps) for y in y_coordinates]) 
                )
                condition_error = ((len(x_coordinates) == steps) and (len(y_coordinates) == steps))

                if condition_visible and condition_error:
                    plot_equations.append([x_coordinates, y_coordinates])
                    plot_indices.append(index)
                elif not condition_error:
                    plot_equations_error.append([x_coordinates, y_coordinates])
                    plot_indices_error.append(index)

        return plot_equations, plot_indices
    
    
    def create_feasible_region_vertices(self, A, b):
        """Calculate vertices of the FB domain feasible region.

        To plot the feasible region of the domain, this method find all vertices linear inequalities
        A x <= b that make up the domain and sorts them clockwise.

        Parameters
        ----------
        A : np.array,
            2-dimensional projection of zonal PTDF.
        b : np.array 
            Vector of RAMs.

        Returns
        -------
        vertices : array 
            Vertices in a CBCO x 2 array.

        """        
        vertices = np.asarray(compute_polytope_vertices(A, b))
        vertices_x = vertices[:, 0]
        vertices_y = vertices[:, 1]

        ### Sort them Counter Clockwise to plot them
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
        return vertices_sorted[:, [0,1]]

    def generate_flowbased_domain(self, domain_x, domain_y, timestep, filename_suffix=None, 
                                  exchange=None, lta_domain=None):
        """Create FB Domain for specified zones and timesteps. 
        
        Parameters
        ----------
        domain_x : 2-element, list-like 
            Two-element list-like of market areas whose commercial exchange is depicted on the 
            x-axis, where positive values indicate a commercial exchange from element one to 
            element two. 
        domain_y : 2-element, list-like 
            Analogue to *domain_x*, just for the y-axis of the 2 dimensional plot.
        timestep : string, 
            Timestep for which the domain is generated. 
        filename_suffix : string, optional
            Optionally append to the resulting filename a suffix that makes it easier to 
            identify when domains for more scenarios are created, by default None.
        """
        domain_info = self.flowbased_parameters.loc[self.flowbased_parameters.timestep == timestep].copy()
        domain_info = domain_info[~(domain_info[self.zones] == 0).all(axis=1)].reset_index()

        if isinstance(exchange, pd.DataFrame):
            print("Correcting Domain for non-depicted commercial exchange")
            # Find Exchange that is not part of the domain plot
            domain_copy = domain_info.copy()
            domain_ex = [tuple(domain_x), tuple(domain_x[::-1]), tuple(domain_y), tuple(domain_y[::-1])]
            
            tmp_exchange = exchange.reset_index()
            tmp_exchange = tmp_exchange[tmp_exchange["from"].isin(self.zones)&tmp_exchange["to"].isin(self.zones)]
            # non_core_zones = [z for z in set(list(exchange["from"]) + list(exchange["to"])) if z not in domain_copy.columns]
            # domain_copy[non_core_zones] = 0
            non_domain_ex = tmp_exchange[~tmp_exchange[["from", "to"]].apply(tuple, axis=1).isin(domain_ex)]
            # correct ram accordingly (i.e. moving the domain into the correct z axis position)
            ram_correction = np.dot(domain_copy[non_domain_ex["from"]].values - domain_copy[non_domain_ex["to"]].values, non_domain_ex["FlowFB"].values)
            # ram_correction = np.dot(domain_copy[exchange["from"]].values - domain_copy[exchange["to"]].values, exchange["exchange"].values)
            domain_info.loc[:, "ram"] = domain_info.loc[:, "ram"] - ram_correction
        
        ram_threshold = 1
        if not domain_info[domain_info.ram < ram_threshold].empty:
            print("Correction caused negative rams!")
            domain_info.loc[domain_info.ram < ram_threshold, "ram"] = ram_threshold
            t = domain_info.loc[domain_info.ram <= ram_threshold]
            print(t)
            print(t.ram)
            # domain_info = domain_info[domain_info.ram > ram_threshold].reset_index()


        # Zonal PTDF with dimensionality number of zones x CBCOs and RAM
        A = domain_info.loc[:, self.zones].values
        b = domain_info.loc[:, "ram"].values

        # Checks 
        if not len(domain_x) == len(domain_y) == 2:
            raise AttributeError("Attributes domain_x, domain_y must have 2 elements")
        if not isinstance(self.flowbased_parameters, pd.DataFrame):
            raise AttributeError("No precalculated flow based parameters available, run create_flowbased_parameters with basecase and GSK")
        elif self.flowbased_parameters[self.flowbased_parameters.timestep == timestep].empty:
            raise AttributeError("No FB parameters available with given parameters!")

        # Project A to the x,y domain axis's
        A_hat = self.zonal_ptdf_projection(domain_x, domain_y, A)
        feasible_region_indices = domain_feasible_region_indices(A_hat, b)
        
        domain_info["in_domain"] = False
        domain_info.loc[domain_info.index.isin(feasible_region_indices), "in_domain"] = True
        
        # Limit the number of constraints plottet to a threshold
        threshold = int(1e4)
        if len(A) > threshold:
            print(f"Plot limited to {threshold} constraints plotted", threshold)
            np.random.seed(2020)
            random_choice = np.random.choice(domain_info.index, size=threshold, replace=False)
            n_0_indices = domain_info.index[domain_info.co == "basecase"].values
            plot_indices = np.sort(np.unique(np.hstack([feasible_region_indices, random_choice, n_0_indices])))
        else:
            plot_indices = domain_info.index

        feasible_region_vertices = self.create_feasible_region_vertices(A_hat, b)
        # feasible_region_volume = domain_volume(self, A, A_hat, b) 
        feasible_region_volume = 0
           
        x_max, y_max = feasible_region_vertices.max(axis=0)*2
        x_min, y_min = feasible_region_vertices.min(axis=0)*2
        if isinstance(lta_domain, pd.DataFrame):
            x_max, y_max = max(x_max, lta_domain.x.max()), max(y_max, lta_domain.y.max()), 
            x_min, y_min = min(x_min, lta_domain.x.min()), min(y_min, lta_domain.y.min()), 

        x_margin, y_margin = 0.2*abs(x_max - x_min), 0.2*abs(y_max - y_min)
        plot_limits = ((x_max + x_margin, x_min - x_margin), (y_max + y_margin, y_min - y_margin))

        # Bring the 2D FB Domain into a format plottable. 
        plot_equations, plot_indices = self.create_domain_plot(A_hat, b, plot_indices, plot_limits)
        domain_info = domain_info.loc[plot_indices, :]

        print(f"Number of CBCOs defining the domain {len(feasible_region_vertices[:, 0]) - 1}")

        plot_information = {
            "timestep": timestep,
            "domain_x": domain_x, 
            "domain_y": domain_y,
            "filename_suffix": filename_suffix, 
            "plot_limits": plot_limits
        }
        
        # FBDomain Class to store all relevant data. 
        fbmc_plot = FBDomain(plot_information, plot_equations, feasible_region_vertices, 
                             domain_info.copy(), feasible_region_volume)

        return fbmc_plot


