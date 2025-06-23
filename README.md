Domain-Viewer
=============

The domain-viewer aims to visualize the day-ahead flow-based domain published on the [JAO Publication Tool](https://publicationtool.jao.eu/core/). 


Installation
------------
After cloning this repository create a virtual environment and install dependencies from *requirements.txt*: 

    python -m venv venv 
    venv/Scrips/activate.bat
    python -m pip install -r requirements.txt
    
This will install the dependencies into a new virtual environment named *venv*. 

Overview
--------

The domain-viewer is a simple script that runs top to bottom. The resulting plot is defined via the first lines in *main.py*. 

    date = "2025-06-11" # Businessday
    hour = "13" # in CET
    domain_x = ["DE", "FR"]
    domain_y = ["DE", "AT"]
    shift_mcp = True

In case you need a proxy to access the JAO PublicationTool, create a *proxy.json* in the root folder: 

    {
        "http": "http://<user>:<pw>@<proxy-address>",
        "https": "https://<user>:<pw>@<proxy-address>"
    }

Description:
------------

The domain-viewer will plot the DayAhead flow-based domain along exchanges along the x and y axis, thus any point within the domain is balanced. 

The domain viewer considers extended LTA inclusion. To do this the share of exchange included in the LTA Domain and the FBDomain is recalculated using the formulation in [Extended formulation for LTA inclusion](https://www.jao.eu/sites/default/files/2022-03/LTA_Inclusion_Description_202202.pdf). Here Variables for Flow and Net-Position are fixed to the values from the JAO Publication Tool, so that flow components FlowFB and FlowLTA as well as NetPosFB and NetPosLTA are obtained. The alpha values is calculated by the viewer and not taken from the publication tool. 

When setting *shift_mcp=True* the domain viewer will shift the Domain to the market clearing point. This is done via the FLowFB components from RAM except for the plottet dimensions. 

Because of the Extended LTA consideration and the MCP shift, the viewer can only depict domains for biddingzone configurations where a border exists, e.g. not DE>HU.  

{% include_relative data/readme-plot.html %} 

