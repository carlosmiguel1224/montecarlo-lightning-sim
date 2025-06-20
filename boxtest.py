from kdtri import *
from OCC.Core.gp import gp_Pnt
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
from trianglemath import find_closest_point_on_shape
from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Ax2
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from subdivide import *

def extract_more_triangles(shape):
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
                #triangles.append((a, b, c))
                points.append((a))
                points.append((b))
                points.append((c))
                centoid = (a + b + c) / 3.0
                points.append((a + b + c) / 3.0)
                points.append((a + b) / 2)
                points.append((b + c) / 2)
                points.append((c + a) / 2)
                points.append((centoid + a) / 2)
                points.append((centoid + b) / 2)
                points.append((centoid + c) / 2)
                points.append((2*a + b) / 3)
                points.append((2*b + c) / 3)
                points.append((2*c + a) / 3)
                points.append((a + 2*b) / 3)
                points.append((b + 2*c) / 3)
                points.append((c + 2*a) / 3)
                points_on_face = barycentric_grid_points(a, b, c, resolution=200)
                points.extend(points_on_face)


        exp.Next()

    return points  #triangles, points


def barycentric_grid_points(a, b, c, resolution=3):
    """
    Deterministically generate interior points on triangle (a, b, c).
    resolution = number of divisions along edges.
    """
    points = []
    for i in range(resolution + 1):
        for j in range(resolution + 1 - i):
            u = i / resolution
            v = j / resolution
            w = 1 - u - v
            point = u * a + v * b + w * c
            points.append(point)
    return points







def main():
    samples = 10000
    corner = gp_Pnt(0, 0, 0)  # origin
    dx = 250  # length along X
    dy = 300   # width along Y
    dz = 30   # height along Z


        # Define bounds
    x_min, x_max = 0, 250
    y_min, y_max = 0, 300
    z_min, z_max = 200, 600

    # Generate 1000 random points within the bounds
    sphere_points = np.random.uniform(
        low=(x_min, y_min, z_min),
        high=(x_max, y_max, z_max),
        size=(samples, 3)
    )


    # Define the cylinder parameters
    radius = 250     # radius of the cylinder
    height = 200    # height of the cylinder

    # Base point of the cylinder (origin)
    base_point = gp_Pnt(0, 0, 0)

    # Direction of the cylinder (along Z-axis here)
    direction = gp_Dir(0, 0, 1)

    # Axis system defining orientation and base
    axis = gp_Ax2(base_point, direction)

    # Create the cylinder
    cylinder_shape = BRepPrimAPI_MakeCylinder(axis, radius, height).Shape()

    all_fake = []

    # Create the box
    total_time = 0
    false_distance = 0
    shape = BRepPrimAPI_MakeBox(corner, dx, dy, dz).Shape()

    target_area = 500000  # Any face above this will be subdivided

    #shape = subdivide_large_faces(shape, target_area)
    
    mesh_shape(cylinder_shape)
    points = extract_more_triangles(cylinder_shape)
    kdtree = build_kdtree(points)
    for i in range(samples):
        x,y,z=sphere_points[i]
        vertex = BRepBuilderAPI_MakeVertex(gp_Pnt(x,y,z)).Vertex()
        start = time.time()
        real_dist, closest = min_dist_tolerance_adjusted(vertex,cylinder_shape)
        print(f"Real min dist: {real_dist}, {closest.X(), closest.Y(), closest.Z()}")
        # Step 1: Mesh the shape (optional if mesh data is available)
        t1 = time.time() - start
        print("Done in", t1, "seconds")
        # Replace with your actual point
        start = time.time()
        distance, closest = find_closest_point_kdtree(kdtree, sphere_points[i])
        #min_dist, closest_point, closest_triangle = find_closest_point_on_shape(
        #sphere_center, triangles, points, radius
        #)
        #print(f"From triangle: {min_dist, closest_point}")
        # Output the result
        #print(f"Closest point: {closest}")
        print(f"Distance: {distance}")
        t2 = time.time() - start
        print("Done in", t2, "seconds")
        total_time += t1 - t2
        fake = distance - real_dist
        #false_distance += distance - real_dist
        if fake >= .25:
            all_fake.append(fake)

    print(f"time_saved: {total_time}")
    print(f"false_distance: {false_distance}")
    #print(all_fake[:20])
    print(sorted(all_fake, reverse=True)[:20])
    print(len(all_fake))
main()