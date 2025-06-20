from disttest import *

import numpy as np
from scipy.spatial import cKDTree
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.BRep import BRep_Tool
from OCC.Core.TopAbs import TopAbs_FACE
from OCC.Core.gp import gp_Pnt
from OCC.Core.BRep import BRep_Builder
from OCC.Core.TopoDS import TopoDS_Shape, TopoDS_Face

# Function to mesh the shape
def mesh_shape(shape, linear_deflection=1e-7, angular_deflection=0.01):
    mesh = BRepMesh_IncrementalMesh(shape, linear_deflection, False, angular_deflection, True)
    mesh.Perform()
    return mesh


def get_mesh_points(shape):
    points = []

    exp = TopExp_Explorer(shape, TopAbs_FACE)
    while exp.More():
        face = topods.Face(exp.Current())

        # Local transformation of face
        face_location = face.Location()
        face_trsf = face_location.Transformation()

        # Global transformation of the whole shape (if it has one)
        shape_location = shape.Location()
        shape_trsf = shape_location.Transformation()

        # Final transformation: local + global
        full_trsf = face_trsf.Multiplied(shape_trsf)

        triangulation = BRep_Tool.Triangulation(face, face_location)
        if triangulation is not None:
            for i in range(1, triangulation.NbNodes() + 1):
                pnt = triangulation.Node(i).Transformed(full_trsf)
                points.append((pnt.X(), pnt.Y(), pnt.Z()))

        exp.Next()

    return points



# Build K-d tree from the mesh points
def build_kdtree(mesh_points):
    # Convert the list of points into a numpy array
    points_array = np.array(mesh_points)
    # Build the K-d tree using scipy's cKDTree
    kdtree = cKDTree(points_array)
    return kdtree

# Find closest point on the mesh to the sphere center (target point)
def find_closest_point(kdtree, target_point):
    # Query the K-d tree for the closest point
    distance, index = kdtree.query(target_point)
    return distance, kdtree.data[index]

# Main function to tie everything together
def main():
    
    display, start_display, add_menu, add_function_to_menu = init_display()
    file = 'box_with_hole.stp'
    shape_info = {}
    all_shapes = []
    all_shapes = extract_shapes(read_step_and_transform(file), solid = False,shell=True, compound=True)
    vertex = BRepBuilderAPI_MakeVertex(gp_Pnt(0,0,50)).Vertex()

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
        real_dist, closest = min_dist_tolerance_adjusted(vertex,shape)
        print(f"Real min dist: {real_dist}, {closest.X(), closest.Y(), closest.Z()}")
        # Step 1: Mesh the shape with desired deflection
        mesh_shape(shape, linear_deflection=1e-2, angular_deflection=1e-2)

        # Step 2: Extract mesh points
        mesh_points = get_mesh_points(shape)
        print(get_max_z_from_shape_modified(shape))
        # Step 3: Build K-d tree with mesh points
        kdtree = build_kdtree(mesh_points)

        # Example target point (center of sphere)
        sphere_center = np.array([25, 15, 50])  # Replace with your actual point

        # Step 4: Find the closest point to the sphere center
        distance, closest_point = find_closest_point(kdtree, sphere_center)
        print(f"Closest point: {closest_point}")
        print(f"Distance: {distance}")

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

    start_display()
# Call main function
if __name__ == "__main__":
    main()
