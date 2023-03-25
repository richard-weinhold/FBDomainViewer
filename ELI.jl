
using Pkg
Pkg.activate("FBViewer/")

using JuMP
using CSV, DataFrames
using Ipopt

ptdf = CSV.File("ptdf.csv")|> DataFrame

zones = names(ptdf)
ptdf = Array(ptdf)
ram = CSV.File("ram.csv")|> DataFrame |> Array

lta_data = CSV.File("lta.csv") |> DataFrame
lta = Dict(tuple(t[1], t[2]) => t[3] for t in zip(eachcol(lta_data[:, [:from, :to, :lta]])...) |> collect)
exchange_data = CSV.File("exchange.csv") |> DataFrame
exchange = Dict(tuple(t[1], t[2]) => t[3] for t in zip(eachcol(exchange_data[:, [:from, :to, :exchange]])...) |> collect)

mcp_data = CSV.File("mcp.csv", skipto=3) |> DataFrame
mcp = Dict(d[1] => d[2] for d in zip(eachcol(mcp_data)...) |> collect)
m = Model(Ipopt.Optimizer)

@variables m begin
    Flow[z=zones, zz=zones] >= 0
    FlowFB[z=zones, zz=zones] >= 0
    FlowFB_dash[z=zones, zz=zones] >= 0
    FlowLTA[z=zones, zz=zones] >= 0
    FlowLTA_dash[z=zones, zz=zones] >= 0
    SlackFB[cb=1:length(ram)] >= 0
    NetPos[z=zones]
    NetPosFB[z=zones]
    NetPosFB_dash[z=zones]
    NetPosLTA[z=zones]
    NetPosLTA_dash[z=zones]
    Alpha1 >= 0
    Alpha2 >= 0
end

if true
    @constraint(m, [z=zones, zz=zones], FlowFB_dash[z,zz] == Alpha1 * FlowFB[z,zz]);
    @constraint(m, [z=zones, zz=zones], FlowLTA_dash[z,zz] == Alpha1 * FlowLTA[z,zz]);
    @constraint(m, [z=zones], NetPosLTA_dash[z] == Alpha2 * NetPosLTA[z]);
    @constraint(m, [z=zones], NetPosFB_dash[z] == Alpha2 * NetPosFB[z]);
else
    @constraint(m, [z=zones, zz=zones], FlowFB_dash[z,zz] == FlowFB[z,zz]);
    @constraint(m, [z=zones, zz=zones], FlowLTA_dash[z,zz] == FlowLTA[z,zz]);
    @constraint(m, [z=zones], NetPosLTA_dash[z] == NetPosLTA[z]);
    @constraint(m, [z=zones], NetPosFB_dash[z] == NetPosFB[z]);
end

@constraint(m, [z=zones, zz=zones], 
    Flow[z,zz] == FlowFB_dash[z,zz] + FlowLTA_dash[z,zz]);
@constraint(m, [z=zones], 
    NetPos[z] == NetPosFB_dash[z] + NetPosLTA_dash[z]);
@constraint(m, Alpha1 + Alpha2 == 1);
# @constraint(m, sum(NetPos) == 0);

@constraint(m, ptdf * NetPosFB_dash.data .<= Alpha1 * ram .+ SlackFB); 
# @constraint(m, ptdf * NetPosFB_dash.data .<= Alpha1 * ram ); 

@constraint(m, [z=zones], 
    NetPosFB_dash[z] == sum(FlowFB_dash[z,zz] - FlowFB_dash[zz,z] for zz in zones)
)

@constraint(m, [z=zones], 
    NetPosLTA_dash[z] == sum(FlowLTA_dash[z,zz] - FlowLTA_dash[zz,z] for zz in zones)
)

@constraint(m, [z=zones, zz=zones],
    FlowLTA_dash[z,zz] <= Alpha2 * ((z,zz) in keys(lta) ? lta[(z,zz)] : 0)
)

domain_x=["DE", "FR"]
domain_y=["DE", "NL"]

@constraint(m, [z=zones], 
    NetPos[z] == mcp[z]
)

# @constraint(m, NetPosFB["BE"] >= -6597)
# @constraint(m, 0 >= NetPosFB["PL"] >= -621)

# @constraint(m, 
#     sum(FlowFB[z, "BE"] for z in zones) <= 6597 
# )

# @constraint(m, 
#     sum(FlowFB[z, "PL"] for z in zones) <= 621 
# )
# @constraint(m, 
#     sum(FlowFB["PL", z] for z in zones) <= 0 
# )

# sum(value(Flow["PL", z]) for z in zones)

@constraint(m, [z=zones, zz=zones], 
    Flow[z,zz] == ((z,zz) in keys(exchange) ? exchange[(z,zz)] : 0 )    
)

@objective(m, Max, 
    -sum(SlackFB)*1e4 + Alpha1*100
    # + NetPos[domain_x].data'*[1; -1]
    # + NetPos[domain_y].data'*[1; -1]
)
optimize!(m)

println("Obj: ", objective_value(m))
println("Status: ", termination_status(m))
println("Alpha1/Alpha2: ", value(Alpha1), value(Alpha2))
println("Slack: ", sum(value.(SlackFB)))
all(ptdf * value.(NetPosFB).data .<= ram .+ value.(SlackFB))


lta_results = DataFrame(from=[], to=[], LTA=[], Flow=[], FlowFB=[], FlowLTA=[])
for row in eachrow(lta_data) 
    z, zz = row[:from], row[:to]
    push!(lta_results, [z, zz, lta[(z,zz)], value(Flow[z,zz]), value(FlowFB[z,zz]), value(FlowLTA[z,zz])])
end
CSV.write("lta_results.csv", lta_results)
lta_results

mcp_results = DataFrame(zone=[], MCP=[], NetPos=[], NetPosFB=[], NetPosLTA=[])
for row in eachrow(mcp_data) 
    z = row[:Column1]
    push!(mcp_results, [z, mcp[z], value(NetPos[z]), value(NetPosFB[z]), value(NetPosLTA[z])])
end
mcp_results

CSV.write("mcp_results.csv", mcp_results)