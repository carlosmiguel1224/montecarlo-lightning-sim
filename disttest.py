from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX
from OCC.Extend.DataExchange import read_step_file  # or read_iges_file
from findingmaxz_readingfile import *
from montecarlohelper import *
from util import *
import time
from OCC.Display.SimpleGui import init_display


from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_EDGE
from OCC.Core.BRep import BRep_Tool
from OCC.Core.BRepAdaptor import BRepAdaptor_Curve
from OCC.Core.GCPnts import GCPnts_AbscissaPoint

from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.TopLoc import TopLoc_Location



from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_FACE
from OCC.Core.TopoDS import topods_Face
from OCC.Core.BRep import BRep_Tool_Triangulation
from OCC.Core.TopLoc import TopLoc_Location


def get_mesh_points(shape):
    points = []

    # Explore all faces
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    while exp.More():
        face = exp.Current()
        location = TopLoc_Location()
        triangulation = BRep_Tool.Triangulation(face, location)

        if triangulation is not None:
            n_nodes = triangulation.NbNodes()
            for i in range(1, n_nodes + 1):  # OCC is 1-indexed
                pnt = triangulation.Node(i).Transformed(location.Transformation())
                points.append((pnt.X(), pnt.Y(), pnt.Z()))

        exp.Next()

    return points





#def mesh_shape(shape, linear_deflection=1e-5, angular_deflection=0.1):
    #mesh = BRepMesh_IncrementalMesh(shape, linear_deflection, False, angular_deflection, True)
    #mesh.Perform()

def average_edge_length(shape):
    exp = TopExp_Explorer(shape, TopAbs_EDGE)
    lengths = []
    while exp.More():
        edge = exp.Current()
        adaptor = BRepAdaptor_Curve(edge)
        first = adaptor.FirstParameter()
        last = adaptor.LastParameter()

        try:
            length = GCPnts_AbscissaPoint.Length(adaptor, first, last, 1e-6)
            lengths.append(length)
        except RuntimeError:
            # If length computation fails, skip this edge
            pass

        exp.Next()

    if not lengths:
        return 0
    return sum(lengths) / len(lengths)

def is_coil_by_edge_density(shape, volume_threshold=7000000, ratio_threshold=0.000007, edgeface_threshhold=5.6):
    z_max,zmin,x_max,y_max,x_min,y_min = get_max_z_from_shape_modified(shape)
    volume = get_bounding_volume(z_max,zmin,x_max,y_max,x_min,y_min)  # Fallback if volume is near 0
    if volume < .0001:
        volume = .001
    avg_edge_len = average_edge_length(shape)
    complexity_ratio = avg_edge_len / volume
    face, edge, _ = count_subshapes(shape)
    if volume > volume_threshold and complexity_ratio < ratio_threshold and (edge/face) > edgeface_threshhold:
        return True
    return False


def count_bspline_faces(shape):
    from OCC.Core.TopAbs import TopAbs_FACE
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopoDS import topods_Face
    from OCC.Core.BRep import BRep_Tool

    bspline_count = 0
    face_count = 0

    exp = TopExp_Explorer(shape, TopAbs_FACE)
    while exp.More():
        face = topods_Face(exp.Current())
        surf = BRep_Tool.Surface(face)
        surf_type = surf.DynamicType().Name()
        if "BSpline" in surf_type:
            bspline_count += 1
        face_count += 1
        exp.Next()

    return face_count, bspline_count

def count_subshapes(shape: TopoDS_Shape):
    face_count = 0
    edge_count = 0
    vertex_count = 0

    # Count faces
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    while exp.More():
        face_count += 1
        exp.Next()

    # Count edges
    exp = TopExp_Explorer(shape, TopAbs_EDGE)
    while exp.More():
        edge_count += 1
        exp.Next()

    # Count vertices
    exp = TopExp_Explorer(shape, TopAbs_VERTEX)
    while exp.More():
        vertex_count += 1
        exp.Next()

    return face_count, edge_count, vertex_count


def is_shape_likely_slow(shape):
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopAbs import TopAbs_FACE
    from OCC.Core.TopoDS import topods_Face
    from OCC.Core.BRep import BRep_Tool
    from OCC.Core.Geom import Geom_BSplineSurface
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepBndLib import brepbndlib_Add

    # 1. B-spline complexity (few but heavy)
    bspline_control_points = 0
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    while exp.More():
        face = topods_Face(exp.Current())
        surf = BRep_Tool.Surface(face)
        if isinstance(surf, Geom_BSplineSurface):
            bspline_control_points += surf.NbUPoles() * surf.NbVPoles()
        exp.Next()

    # 2. Bounding box aspect ratio
    bbox = Bnd_Box()
    brepbndlib_Add(shape, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
    dx, dy, dz = xmax - xmin, ymax - ymin, zmax - zmin
    aspect_ratio = max(
        dz / max(dx, 1e-6),
        dz / max(dy, 1e-6)
    )
    print(f"Number of control points {bspline_control_points}")
    # Heuristic thresholds (tune as needed)
    return (
        bspline_control_points > 10000 or
        aspect_ratio > 30  # very long/thin in Z direction
    )


def main():
    display, start_display, add_menu, add_function_to_menu = init_display()
    file = 'box_with_hole.stp'
    shape_info = {}
    all_shapes = []
    all_shapes = extract_shapes(read_step_and_transform(file), solid = True,shell=True, compound=True)
    vertex = BRepBuilderAPI_MakeVertex(gp_Pnt(0,0,1100)).Vertex()

    for i in range(len(all_shapes)):
        shape = all_shapes[i]
        z_max,x_max,y_max,x_min,y_min = get_max_z_from_shape(shape)
        x = -(-x_min+x_max)/2
        y = -(-y_min+y_max)/2
        z = z_max + 10
        message_point = gp_Pnt(x,y,z)
        #display.DisplayMessage(message_point, f"id for shape {i}")
        shape_handle = display.DisplayShape(shape, update = False, transparency=.9)[0]
        shape_info[f"{i}"] = {"coords":(x,y,z), "shape":shape, "name":None, "shapehandle":shape_handle, "count":0}


    for i, shape in enumerate(all_shapes):
        start = time.time()
        print(f"This is index {i}")
        print(shape_info[f"{i}"]["shape"])
        #print(f"Averageedgelength: {average_edge_length(shape)}")
        print(min_dist_tolerance_adjusted(vertex, shape))
        print(mesh_shape(shape))
        print(get_mesh_points(shape))
        print("Done in", time.time() - start, "seconds")
        if i == 239:
            #print(is_shape_likely_slow(shape))
            print(f"This is index {i}")
            print(shape_info[f"{i}"]["shape"])
            display.DisplayShape(shape, update = False, transparency=.9, color = Quantity_NOC_GREEN)[0]
            time.sleep(30)
        if i == 521:

            #print(is_shape_likely_slow(shape))
            print(f"This is index {i}")
            print(shape_info[f"{i}"]["shape"])
            #print(average_edge_length(shape))
            #find_minimum_distance(vertex, shape)
            #print(get_max_z_from_shape_modified(shape))
            #print(f"Number of subshapes: {count_subshapes(shape)}")
            print(f"Is complex? {is_coil_by_edge_density(shape)}")
            display.DisplayShape(shape, update = False, transparency=.9, color = Quantity_NOC_GREEN)[0]
            time.sleep(30)
        #if i == 569:
            #print(f"This is index {i}")
            #print(shape_info[f"{i}"]["shape"])
            #print(average_edge_length(shape))
            #find_minimum_distance(vertex, shape)
            #print(get_max_z_from_shape_modified(shape))
            #print(f"Number of subshapes: {count_subshapes(shape)}")
            #time.sleep(30)
            #print(get_max_z_from_shape_modified(shape))

            #display.DisplayShape(shape, update = False, transparency=.9, color = Quantity_NOC_RED)[0]

    #start_display()

    


# Example: Load a STEP file and analyze it
if __name__ == "__main__":
    main()
