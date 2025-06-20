from OCC.Core.BRep import BRep_Tool
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCC.Core.BRepTools import breptools_UVBounds
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Section
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Sewing
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeShell
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_FACE
from OCC.Core.TopoDS import topods_Face, TopoDS_Compound, TopoDS_Solid, topods_Shell
from OCC.Core.GProp import GProp_GProps
from OCC.Core.BRepGProp import brepgprop_SurfaceProperties
from OCC.Core.TopTools import TopTools_ListOfShape
from OCC.Core.ShapeExtend import ShapeExtend_WireData
from OCC.Extend.TopologyUtils import TopologyExplorer
import math

def get_face_area(face):
    props = GProp_GProps()
    brepgprop_SurfaceProperties(face, props)
    return props.Mass()

def subdivide_face(face, target_area):
    u_min, u_max, v_min, v_max = breptools_UVBounds(face)
    area = get_face_area(face)

    if area <= target_area:
        return [face]

    # Estimate number of subdivisions
    divisions = int(math.ceil(math.sqrt(area / target_area)))
    subdivided_faces = []

    u_step = (u_max - u_min) / divisions
    v_step = (v_max - v_min) / divisions

    # Get surface
    surf = BRep_Tool.Surface(face)
    tol = 1e-6  # small tolerance value

    for i in range(divisions):
        for j in range(divisions):
            u1 = u_min + i * u_step
            u2 = u1 + u_step
            v1 = v_min + j * v_step
            v2 = v1 + v_step

            # Pass the surface and 6 parameters
            make_face = BRepBuilderAPI_MakeFace(surf, u1, u2, v1, v2, tol)
            if make_face.IsDone():
                small_face = make_face.Face()
                subdivided_faces.append(small_face)

    return subdivided_faces

def subdivide_large_faces(shape, target_area):
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    new_faces = []

    while explorer.More():
        face = topods_Face(explorer.Current())
        subdivided = subdivide_face(face, target_area)
        new_faces.extend(subdivided)
        explorer.Next()

    # Sewing them into a shell
    sewing = BRepBuilderAPI_Sewing()
    for f in new_faces:
        sewing.Add(f)
    sewing.Perform()
    sewed_shape = sewing.SewedShape()

    return sewed_shape
