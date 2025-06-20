from OCC.Core.gp import gp_Pnt, gp_Vec, gp_Ax2, gp_Dir, gp_Trsf, gp_Ax3, gp_Pln
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCC.Core.BRepExtrema import BRepExtrema_DistShapeShape
from OCC.Core.Geom import Geom_Plane
from OCC.Core.TopoDS import topods, TopoDS_Shape, topods_Face
from OCC.Core.GProp import GProp_GProps
from OCC.Core.BRepGProp import BRepGProp_Face
from OCC.Core.BRep import BRep_Tool
from OCC.Display.SimpleGui import init_display
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform, BRepBuilderAPI_MakeVertex
from OCC.Core.Quantity import (
    Quantity_NOC_RED,
    Quantity_NOC_GREEN,
    Quantity_NOC_BLUE1,
    Quantity_NOC_YELLOW,
    Quantity_NOC_BLACK,
    Quantity_NOC_WHITE
)
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.AIS import AIS_TextLabel
from OCC.Core.TCollection import TCollection_ExtendedString
from OCC.Core.BRepBndLib import _BRepBndLib
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCC.Core.AIS import AIS_ColoredShape, AIS_Shape
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_FACE
from OCC.Core.Geom import Geom_SphericalSurface
from findingmaxz_readingfile import *
import math
import random
from OCC.Core.Extrema import Extrema_ExtFlag, Extrema_ExtAlgo
from scipy.spatial import KDTree
import joblib
import time
import os
from OCC.Core.BRepGProp import brepgprop_VolumeProperties
from OCC.Core.GProp import GProp_GProps
from multiprocessing import Process, Queue
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import queue
from OCC.Core.gp import gp_Ax1
from OCC.Core.BRep import BRep_Builder
from OCC.Core.TopoDS import TopoDS_Compound
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Common
def find_minimum_distance(shape1, shape2):
    # Create a distance object
    dist = BRepExtrema_DistShapeShape(shape1, shape2)
    dist.Perform()  # Perform the distance calculation

    if dist.IsDone():
        # Get the minimum distance between the shapes
        minimum_distance = dist.Value()
        #print(f"Minimum Distance: {minimum_distance}")

        # Get the closest points on each shape
        #point1 = dist.PointOnShape1(1)
        point2 = dist.PointOnShape2(1)

        # Display the coordinates of the closest points
        #print(f"Closest Point on Shape 1: ({point1.X()}, {point1.Y()}, {point1.Z()})")
        #print(f"Closest Point on Shape 2: ({point2.X()}, {point2.Y()}, {point2.Z()})")
        #print(minimum_distance)
        #used to be return minumum_distance, point1, point2
        return minimum_distance, point2
    else:
        print("Distance calculation failed.")
        return None


def create_centered_floor(x_bounds, y_bounds):
    
    length = -x_bounds[0] + x_bounds[1]
    width = -y_bounds[0] + y_bounds[1]
    plane_face = Geom_Plane(gp_Ax3(gp_Pnt(0, 0, 0),gp_Dir(0, 0, 1)))
    floor = BRepPrimAPI_MakeBox(gp_Pnt(-(length/2),-(width/2),0),length, width, -.01).Shape()
    return floor


def abs_min_dist(vertex, all_shapes):
    return min([find_minimum_distance(vertex, shape) for shape in all_shapes], key=lambda x: x[0])

def translate_shape(shape, dx, dy, dz):
    # Create a translation vector
    vec = gp_Vec(dx, dy, dz)

    # Create a transformation object
    trsf = gp_Trsf()
    trsf.SetTranslation(vec)

    # Apply the transformation to the shape
    transformer = BRepBuilderAPI_Transform(shape, trsf, True)  # True = copy
    return transformer.Shape()



def calculate_valid_range(x_max, y_max, x_min, y_min, largest_radius_possible): #delta user chooses this
    neg_x_bound = ((math.floor(x_min - largest_radius_possible)))
    pos_x_bound = ((math.ceil( x_max + largest_radius_possible)))

    neg_y_bound = ((math.floor(y_min - largest_radius_possible)))
    pos_y_bound = ((math.ceil(y_max + largest_radius_possible)))
    
    return (neg_x_bound, pos_x_bound),(neg_y_bound, pos_y_bound)



def get_bbox(shape):
    bbox = Bnd_Box()
    brepbndlib_Add(shape, bbox)
    return bbox

def get_sphere_bbox(center, radius):
    bbox = Bnd_Box()
    bbox.Update(
        center.X() - radius, center.Y() - radius, 0,
        center.X() + radius, center.Y() + radius, center.Z() + radius
    )
    return bbox


def modified_abs_min_dist(vertex, all_shapes):
    distances = [
        (i, *find_minimum_distance(vertex, shape))
        for i, shape in enumerate(all_shapes)
    ]
    # distances is a list of tuples like (index, distance, contact_point)
    return min(distances, key=lambda x: x[1])


def modified_tied_abs_min_dist(vertex, all_shapes):
    distances = [(i, *find_minimum_distance(vertex, shape)) for i, shape in enumerate(all_shapes)]

    min_dist = min(distances, key=lambda x: x[1])[1]
    tied = [entry for entry in distances if entry[1] == min_dist]

    if len(tied) == 1:
        return tied[0]
    else:
        return random.choice(tied)
    

def min_dist_tolerance_adjusted(shape1, shape2):
    # Use the gradient algorithm for more efficient distance calculation  
    flag_min = Extrema_ExtFlag.Extrema_ExtFlag_MIN
    # Perform the distance calculation
    dist_calc = BRepExtrema_DistShapeShape(shape1, shape2, 1e-4,flag_min)
    
    dist_calc.Perform()
    if dist_calc.IsDone():
        point2 = dist_calc.PointOnShape2(1)
        return dist_calc.Value(), point2
    return None



def modified_tolerance_abs_min_dist(vertex, all_shapes):
    distances = [(i, *min_dist_tolerance_adjusted(vertex, shape)) for i, shape in enumerate(all_shapes)]

    min_dist = min(distances, key=lambda x: x[1])[1]
    tied = [entry for entry in distances if entry[1] == min_dist]

    if len(tied) == 1:
        return tied[0]
    else:
        return random.choice(tied)
    



def modified_tolerance_abs_min_dist_visible(vertex, visible_shapes):
    distances = [(i, *min_dist_tolerance_adjusted(vertex, shape)) for i, shape in visible_shapes]

    min_dist = min(distances, key=lambda x: x[1])[1]
    tied = [entry for entry in distances if entry[1] == min_dist]

    if len(tied) == 1:
        return tied[0]
    else:
        return random.choice(tied)
    

def modified_minimum_distance_tolerance_and_index(index,vertex, shape):
    # Use the gradient algorithm for more efficient distance calculation  
    flag_min = Extrema_ExtFlag.Extrema_ExtFlag_MIN
    # Perform the distance calculation
    dist_calc = BRepExtrema_DistShapeShape(vertex, shape, 1e-2,flag_min)
    dist_calc.Perform()
    if dist_calc.IsDone():
        point2 = dist_calc.PointOnShape2(1)
        return index ,dist_calc.Value(), (point2.X(), point2.Y(), point2.Z())
    return None


def kdot_distshape_abs_min_distance(point, candidate_shapes, shape_info, loaded_trees):
    # Build vertex from 3D point
    vertex = BRepBuilderAPI_MakeVertex(gp_Pnt(*point)).Vertex()

    # Step 2: Compute distances
    distances = []
    for i, shape in candidate_shapes:
        if i in loaded_trees:
            tree_data = loaded_trees[i]
            points = tree_data["points"]
            tree = tree_data["tree"]
            
            
            dist, idx = tree.query(point)
            
            closest = points[idx]
            distances.append((i, dist, closest))
        elif shape_info.get(f"{i}", {}).get("kdtreepath"):
            # Late load on demand
            path = shape_info[f"{i}"]["kdtreepath"]
            if os.path.exists(path):
                tree_data = joblib.load(path)
                loaded_trees[i] = tree_data
                points = tree_data["points"]
                tree = tree_data["tree"]
                dist, idx = tree.query(point)
                closest = points[idx]
                distances.append((i, dist, closest))
        else:
            distances.append(modified_minimum_distance_tolerance_and_index(i, vertex, shape))

    # Step 3: Find min
    min_dist = min(distances, key=lambda x: x[1])[1]
    tied = [entry for entry in distances if entry[1] == min_dist]

    # Optional: Clean up to free RAM
    #loaded_trees.clear()

    return tied[0] if len(tied) == 1 else random.choice(tied)



def compute_volume(shape):
    props = GProp_GProps()
    brepgprop_VolumeProperties(shape, props)
    return props.Mass()


def extract_shell_from_solid(solid):
    explorer = TopExp_Explorer(solid, TopAbs_SHELL)
    if explorer.More():
        return explorer.Current()  # returns a TopoDS_Shell
    return None


# At the top level of your module
def distshape_worker(index, shape, vertex, queue):

    try:
        flag_min = Extrema_ExtFlag.Extrema_ExtFlag_MIN
        dist_calc = BRepExtrema_DistShapeShape(vertex, shape, 1e-2, flag_min)
        dist_calc.Perform()
        if dist_calc.IsDone():
            point2 = dist_calc.PointOnShape2(1)
            queue.put((index, dist_calc.Value(), (point2.X(), point2.Y(), point2.Z())))
        else:
            queue.put(None)
    except Exception:
        queue.put(None)



def distshape_with_timeout(index, shape, vertex, timeout=3):
    queue = Queue()
    p = Process(target=distshape_worker, args=(index, shape, vertex, queue))
    p.start()
    p.join(timeout)

    if p.is_alive() and (compute_volume(shape) <=1e7):
        p.terminate()
        p.join()
        return None
    if not queue.empty():
        return queue.get()
    return None


def new_distshape_with_timeout(index, shape, vertex, timeout=3):
    shape_volume = compute_volume(shape)

    def wrapper():
        q = queue.Queue()
        distshape_worker(index, shape, vertex, q)
        return q.get()

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(wrapper)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeoutError:
            print(f"Timeout on shape {index} (volume {shape_volume:.2e}) — skipping.")
            return None
        
def reorient_shapes_to_z0_and_center_xy(shapes, axis="X", angle_deg=90):
    """
    Rotates all shapes around a principal axis, then translates them so:
    - The lowest Z point aligns to Z = 0.
    - The center of the bounding box in X and Y aligns to (0, 0).

    Args:
        shapes (list): List of TopoDS_Shapes.
        axis (str): "X", "Y", or "Z" to rotate around.
        angle_deg (float): Rotation angle in degrees.

    Returns:
        list: Transformed TopoDS_Shapes.
    """
    import math
    from OCC.Core.gp import gp_Trsf, gp_Ax1, gp_Pnt, gp_Dir, gp_Vec
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepBndLib import brepbndlib_Add

    # 1. Define rotation
    angle_rad = math.radians(angle_deg)
    if axis.upper() == "X":
        rotation_axis = gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0))
    elif axis.upper() == "Y":
        rotation_axis = gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0))
    elif axis.upper() == "Z":
        rotation_axis = gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1))
    else:
        raise ValueError("Invalid axis. Use 'X', 'Y', or 'Z'.")

    rot_trsf = gp_Trsf()
    rot_trsf.SetRotation(rotation_axis, angle_rad)

    # 2. Apply rotation
    rotated_shapes = []
    for shape in shapes:
        rotated = BRepBuilderAPI_Transform(shape, rot_trsf, True).Shape()
        rotated_shapes.append(rotated)

    # 3. Calculate bounding box
    bbox = Bnd_Box()
    for shape in rotated_shapes:
        brepbndlib_Add(shape, bbox)

    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()

    # 4. Translate to Z = 0 and center XY around (0,0)
    center_x = (xmax + xmin) / 2.0
    center_y = (ymax + ymin) / 2.0

    move_vec = gp_Vec(-center_x, -center_y, -zmin)
    move_trsf = gp_Trsf()
    move_trsf.SetTranslation(move_vec)

    # 5. Apply translation
    final_shapes = []
    for shape in rotated_shapes:
        moved = BRepBuilderAPI_Transform(shape, move_trsf, True).Shape()
        final_shapes.append(moved)

    return final_shapes

def make_compound_from_shapes(shapes):
    """
    Builds a TopoDS_Compound from a list of TopoDS_Shapes.

    Args:
        shapes (list): List of TopoDS_Shape objects.

    Returns:
        TopoDS_Compound: The compound shape containing all the input shapes.
    """
    builder = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)

    for shape in shapes:
        builder.Add(compound, shape)

    return compound


def get_shape_z_bounds(shape):
    bbox = Bnd_Box()
    brepbndlib_Add(shape, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
    return zmin, zmax

def find_floor_index(all_shapes):
    for i, shape in enumerate(all_shapes):
        zmin, zmax = get_shape_z_bounds(shape)
        if zmin <= .001:
            return i  # Likely the floor
    return None  # No floor found


def translate_shapes_to_z0_and_center_xy(shapes):
    """
    Translates all shapes so that:
    - The lowest Z value becomes 0 (base of the model is on Z=0)
    - The center in X and Y is positioned at (0, 0)

    Args:
        shapes (list): List of TopoDS_Shapes.

    Returns:
        list: Transformed TopoDS_Shapes.
    """
    # 1. Calculate overall bounding box
    bbox = Bnd_Box()
    for shape in shapes:
        brepbndlib_Add(shape, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()

    # 2. Determine center in XY and Z offset
    center_x = (xmax + xmin) / 2.0
    center_y = (ymax + ymin) / 2.0
    z_offset = -zmin  # move base to Z=0

    # 3. Build translation
    move_vec = gp_Vec(-center_x, -center_y, z_offset)
    move_trsf = gp_Trsf()
    move_trsf.SetTranslation(move_vec)

    # 4. Apply translation
    moved_shapes = []
    for shape in shapes:
        moved = BRepBuilderAPI_Transform(shape, move_trsf, True).Shape()
        moved_shapes.append(moved)

    return moved_shapes



def bounding_box_volume(shape):
    """
    Calculates the volume of the axis-aligned bounding box of a shape.

    Args:
        shape (TopoDS_Shape): The input shape.

    Returns:
        float: Volume of the bounding box.
    """
    bbox = Bnd_Box()
    brepbndlib_Add(shape, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
    
    dx = xmax - xmin
    dy = ymax - ymin
    dz = zmax - zmin
    
    return dx * dy * dz