from disttest import *
from trianglemath import *
import numpy as np
from scipy.spatial import cKDTree
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.BRep import BRep_Tool
from OCC.Core.TopAbs import TopAbs_FACE
from OCC.Core.gp import gp_Pnt
from OCC.Core.BRep import BRep_Builder
from OCC.Core.TopoDS import TopoDS_Shape, TopoDS_Face

# Function to mesh the shape
def mesh_shape(shape, linear_deflection=1e-1, angular_deflection=1e-1):
    mesh = BRepMesh_IncrementalMesh(shape, linear_deflection, False, angular_deflection, True)
    mesh.Perform()
    return mesh


def filter_externally_visible_shapes(shapes):
    visible_shapes = []

    # Precompute bounding boxes with original indices
    bboxes = []
    for idx, shape in enumerate(shapes):
        bbox = Bnd_Box()
        brepbndlib_Add(shape, bbox)
        bboxes.append((idx, shape, bbox))

    # Check which shapes are not completely inside another
    for i, (idx_i, shape_i, bbox_i) in enumerate(bboxes):
        ixmin, iymin, izmin, ixmax, iymax, izmax = bbox_i.Get()

        is_inside_another = False
        for j, (idx_j, shape_j, bbox_j) in enumerate(bboxes):
            if i == j:
                continue

            jxmin, jymin, jzmin, jxmax, jymax, jzmax = bbox_j.Get()

            if (
                ixmin >= jxmin and ixmax <= jxmax and
                iymin >= jymin and iymax <= jymax and
                izmin >= jzmin and izmax <= jzmax
            ):
                is_inside_another = True
                break

        if not is_inside_another:
            visible_shapes.append((shape_i, idx_i))

    return visible_shapes



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



def extract_triangles(shape):
    triangles = []
    centroids = []

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
                centroids.append((a + b + c) / 3.0)

        exp.Next()

    return triangles, np.array(centroids)


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
    file = 'Jib crane ASSY.stp'
    shape_info = {}
    all_shapes = []
    transformed_file = read_step_no_transform_find_center(file)
    Z_max,Z_min, X_max, Y_max, X_min, Y_min = get_max_z_from_shape_modified(transformed_file)
    center_x = (X_min + X_max) / 2
    center_y = (Y_min + Y_max) / 2
    print(center_x, center_y)
    all_shapes = extract_shapes(transformed_file, solid = True,shell=True, compound=True)
    visible_shapes = filter_externally_visible_shapes(all_shapes)
    vertex = BRepBuilderAPI_MakeVertex(gp_Pnt(center_x,center_y,50)).Vertex()

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
        start = time.time()
        print(f"This is index {i}")
        print(shape_info[f"{i}"]["shape"])
        real_dist, closest = min_dist_tolerance_adjusted(vertex,shape)
        print(f"Real min dist: {real_dist}, {closest.X(), closest.Y(), closest.Z()}")
        # Step 1: Mesh the shape with desired deflection
        mesh_shape(shape, linear_deflection=1e-2, angular_deflection=1e-2)

        # Step 2: Extract mesh points
        #mesh_points = get_mesh_points(shape)
        triangles, centroids = extract_triangles(shape)
        print(centroids)
        #print(get_max_z_from_shape_modified(shape))
        # Step 3: Build K-d tree with mesh points
        kdtree = cKDTree(centroids)

        # Example target point (center of sphere)
        sphere_center = np.array([center_x, center_y, 50])  # Replace with your actual point

        # Step 4: Find the closest point to the sphere center
        radius = 50.0  # You can tune this
        min_dist, closest_point, closest_triangle = find_closest_point_on_shape(
        sphere_center, triangles, centroids, radius
        )

        # Output the result
        print("Closest point on shape:", closest_point)
        print("Distance from point to shape:", min_dist)
        print("Closest triangle:", closest_triangle)

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
