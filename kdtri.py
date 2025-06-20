import numpy as np
from scipy.spatial import cKDTree
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.BRep import BRep_Tool
from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.gp import gp_Pnt
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
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
import time
from util import *

# Function to mesh the shape
def mesh_shape(shape, linear_deflection=1e-1, angular_deflection=1e-1):
    mesh = BRepMesh_IncrementalMesh(shape, linear_deflection, False, angular_deflection, True)
    mesh.Perform()
    return mesh



def extract_triangles(shape):
    triangles = []
    points = []

    # Explore all faces in the shape
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    while exp.More():
        face = topods.Face(exp.Current())
        loc = face.Location()  # Get the location (transformation) of the face
        trsf = loc.Transformation()  # Extract the transformation

        # Get the triangulation of the face
        triangulation = BRep_Tool.Triangulation(face, loc)
        if triangulation:
            tris = triangulation.Triangles()  # Get the triangles
            for i in range(1, triangulation.NbTriangles() + 1):
                tri = tris.Value(i)  # Get the ith triangle
                idx1, idx2, idx3 = tri.Get()  # Get the node indices of the triangle

                # Transform each node using the transformation of the face
                p1 = triangulation.Node(idx1).Transformed(trsf)
                p2 = triangulation.Node(idx2).Transformed(trsf)
                p3 = triangulation.Node(idx3).Transformed(trsf)

                # Convert the points to numpy arrays for easier processing
                a = np.array([p1.X(), p1.Y(), p1.Z()])
                b = np.array([p2.X(), p2.Y(), p2.Z()])
                c = np.array([p3.X(), p3.Y(), p3.Z()])

                # Append the triangle and its centroid
                triangles.append((a, b, c))
                points.append((a))
                points.append((b))
                points.append((c))
                points.append((a + b + c) / 3.0)
                points.append((a + b) / 2)
                points.append((b + c) / 2)
                points.append((c + a) / 2)

        exp.Next()

    return triangles, points

# Function to compute the point-to-triangle distance
def point_to_triangle_distance(point, triangle):
    # Triangle vertices
    p1, p2, p3 = triangle
    
    # Compute vectors
    v0 = p2 - p1
    v1 = p3 - p1
    v2 = point - p1
    
    # Compute dot products
    dot00 = np.dot(v0, v0)
    dot01 = np.dot(v0, v1)
    dot02 = np.dot(v0, v2)
    dot11 = np.dot(v1, v1)
    dot12 = np.dot(v1, v2)
    
    # Compute barycentric coordinates
    invDenom = 1 / (dot00 * dot11 - dot01 * dot01)
    u = (dot11 * dot02 - dot01 * dot12) * invDenom
    v = (dot00 * dot12 - dot01 * dot02) * invDenom
    
    # Compute closest point on the triangle
    if u < 0.0 or v < 0.0 or u + v > 1.0:
        # Closest point is outside the triangle, clamp to the nearest vertex
        distances = [np.linalg.norm(point - p1), np.linalg.norm(point - p2), np.linalg.norm(point - p3)]
        min_dist = min(distances)
        closest_point = [p1, p2, p3][distances.index(min_dist)]
    else:
        # Closest point is inside the triangle
        closest_point = p1 + u * v0 + v * v1
        min_dist = np.linalg.norm(point - closest_point)
    
    return min_dist, closest_point

# Function to build the K-D tree from the points
def build_kdtree(points):
    points_array = np.array(points)
    kdtree = cKDTree(points_array)
    return kdtree



def find_closest_point_kdtree(kdtree, query_point):
    dist, idx = kdtree.query(query_point)
    closest_point = kdtree.data[idx]
    return dist, closest_point

# Function to find the closest triangle using the K-D tree
def find_closest_triangle(kdtree, triangles, target_point, radius):
    # Query the K-D tree for the nearby points within the radius
    indices = kdtree.query_ball_point(target_point, radius)
    
    # Now for each point index, calculate which triangle it belongs to
    min_dist = float('inf')
    closest_point = None
    for idx in indices:
        # Each triangle has 3 points
        triangle_idx = idx // 3  # Each triangle has 3 vertices
        triangle = triangles[triangle_idx]
        
        # Compute the point-to-triangle distance
        dist, point = point_to_triangle_distance(target_point, triangle)
        if dist < min_dist:
            min_dist = dist
            closest_point = point
    
    return min_dist, closest_point

# Main function to put everything together
def main():
    display, start_display, add_menu, add_function_to_menu = init_display()
    file = 'Jib crane ASSY.stp'
    shape_info = {}
    all_shapes = []
    transformed_file = read_step_no_transform_find_center(file)
    Z_max,Z_min, X_max, Y_max, X_min, Y_min = get_max_z_from_shape_modified(transformed_file)
    center_x = (X_min + X_max) / 2
    center_y = (Y_min + Y_max) / 2
    print(center_x, center_y)
    all_shapes = extract_shapes(transformed_file, solid = False,shell=True, compound=False)
    visible_shapes = filter_externally_visible_shapes(all_shapes)
    vertex = BRepBuilderAPI_MakeVertex(gp_Pnt(center_x,center_y,1000)).Vertex()

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

    print(visible_shapes)
    for i ,shape  in enumerate(all_shapes):
        print(f"This is index {i}")
        print(shape_info[f"{i}"]["shape"])
        #start = time.time()

        real_dist, closest = min_dist_tolerance_adjusted(vertex,shape)
        print(f"Real min dist: {real_dist}, {closest.X(), closest.Y(), closest.Z()}")
        # Step 1: Mesh the shape (optional if mesh data is available)
        #print("Done in", time.time() - start, "seconds")
        start = time.time()
        mesh_shape(shape)
        # Step 2: Extract the triangles from the shape
        triangles, points = extract_triangles(shape)
        
        # Step 3: Build the K-D tree with the points from the triangles
        kdtree = build_kdtree(points)
        print("Done meshing and extracting and kd", time.time() - start, "seconds")
        sphere_center = np.array([center_x, center_y, 1000])
        # Replace with your actual point
        #start = time.time()
        distance, closest = find_closest_point_kdtree(kdtree, sphere_center)
        
        # Output the result
        print(f"Closest point: {closest}")
        print(f"Distance: {distance}")
        print("Done in", time.time() - start, "seconds")

# Call main function
if __name__ == "__main__":
    main()