from nolooptag import *
from OCC.Core.gp import gp_Pln, gp_Pnt, gp_Dir
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Splitter
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_SOLID
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Splitter
from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.TopTools import TopTools_ListOfShape

# Create base shape (box)
box_shape = BRepPrimAPI_MakeBox(10, 10, 10).Shape()
#display.DisplayShape(box_shape)
# Create splitting face (plane at x = 5)
plane = gp_Pln(gp_Pnt(5, 0, 0), gp_Dir(1, 0, 0))
plane_face = BRepBuilderAPI_MakeFace(plane, -10, 10, -10, 10).Shape()
display.DisplayShape(plane_face)
# Create and populate TopTools_ListOfShape for arguments and tools
args = TopTools_ListOfShape()
args.Append(box_shape)

tools = TopTools_ListOfShape()
tools.Append(plane_face)

# Set up and execute splitter
splitter = BRepAlgoAPI_Splitter()
splitter.SetArguments(args)
splitter.SetTools(tools)
splitter.Build()

# Collect resulting solids
split_shapes: list[TopoDS_Shape] = []
explorer = TopExp_Explorer(splitter.Shape(), TopAbs_SOLID)
while explorer.More():
    split_shapes.append(explorer.Current())
    explorer.Next()

display.DisplayShape(split_shapes[0])
display.DisplayShape(split_shapes[1])
print(get_max_z_from_shape_modified(split_shapes[0]))
print(get_max_z_from_shape_modified(split_shapes[1]))
print(f"shapes: {split_shapes}")
#print(f"Split resulted in {len(split_shapes)} solid(s).")
start_display()