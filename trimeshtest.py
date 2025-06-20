import math
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_SHELL
from OCC.Core.TopoDS import topods
from trimesh.sample import sample_surface_even
from scipy.spatial import cKDTree
import gc
import joblib
from util import *

def mesh_shell(shell, max_triangle_area=0.01):
    # Approximate maximum edge length from area
    max_edge_length = math.sqrt(4 * max_triangle_area / math.sqrt(3))

    # Perform meshing
    mesh = BRepMesh_IncrementalMesh(shell,1e-1, False, 1e-1, True)
    mesh.Perform()
    return mesh



from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_FACE
from OCC.Core.BRep import BRep_Tool_Triangulation
from OCC.Core.Poly import Poly_Triangulation
from OCC.Core.TopLoc import TopLoc_Location
import numpy as np

def extract_mesh_from_shell(shell):
    vertices = []
    faces = []
    index_offset = 0

    exp = TopExp_Explorer(shell, TopAbs_FACE)
    while exp.More():
        face = exp.Current()
        loc = TopLoc_Location()
        triangulation = BRep_Tool_Triangulation(face, loc)
        if triangulation is None:
            exp.Next()
            continue

        n_pts = triangulation.NbNodes()
        occ_vertices = np.array([
            [triangulation.Node(i + 1).X(), triangulation.Node(i + 1).Y(), triangulation.Node(i + 1).Z()]
            for i in range(n_pts)
        ])

        # Extract triangle connectivity
        tris = triangulation.Triangles()
        n_tris = tris.Length()
        occ_faces = np.array([
            [tris.Value(i + 1).Value(1) - 1 + index_offset,
             tris.Value(i + 1).Value(2) - 1 + index_offset,
             tris.Value(i + 1).Value(3) - 1 + index_offset]
            for i in range(n_tris)
        ])

        vertices.append(occ_vertices)
        faces.append(occ_faces)
        index_offset += n_pts
        exp.Next()

    if not vertices:
        return None  # empty mesh

    return np.vstack(vertices), np.vstack(faces)


import trimesh

def convert_shell_to_trimesh(shell, max_triangle_area=0.01):
    mesh_shell(shell, max_triangle_area)
    verts, faces = extract_mesh_from_shell(shell)
    return trimesh.Trimesh(vertices=verts, faces=faces, process=False)


def build_collision_checker(mesh: trimesh.Trimesh, spacing=0.2):
    from trimesh.sample import sample_surface_even
    import math

    area_per_point = math.pi * spacing ** 2
    n_points = int((mesh.area)/ area_per_point)

    sampled_points, _ = sample_surface_even(mesh, count=n_points)
    tree = cKDTree(sampled_points)

    return sampled_points, tree

def query_closest_point(tree: cKDTree, sampled_points, point, max_distance=0.2):
    distance, index = tree.query(point)
    closest = sampled_points[index]
    return distance, closest, (distance <= max_distance)



def face_max_edge_lengths(mesh):
    # Get vertex positions for each face
    v = mesh.vertices
    f = mesh.faces
    a = np.linalg.norm(v[f[:, 0]] - v[f[:, 1]], axis=1)
    b = np.linalg.norm(v[f[:, 1]] - v[f[:, 2]], axis=1)
    c = np.linalg.norm(v[f[:, 2]] - v[f[:, 0]], axis=1)
    return np.maximum(np.maximum(a, b), c)

def subdivide_largest_faces(mesh, max_edge=0.2, max_iter=10, batch_size=1000):
    current = mesh
    for i in range(max_iter):
        # Compute max edge per face
        max_edge_lengths = face_max_edge_lengths(current)
        face_areas = current.area_faces

        # Find faces with at least one long edge
        candidate_faces = np.where(max_edge_lengths > max_edge)[0]
        if len(candidate_faces) == 0:
            print(f"[INFO] All triangles are within the max_edge after {i} iterations.")
            break

        # Sort candidates by face area (descending) and pick the top N
        sorted_faces = candidate_faces[np.argsort(-face_areas[candidate_faces])]
        selected = sorted_faces[:batch_size]

        if len(selected) == 0:
            print("[INFO] No eligible faces to subdivide.")
            break

        # Subdivide selected faces only
        refined = current.submesh([selected], append=True).subdivide()
        mask = np.ones(len(current.faces), dtype=bool)
        mask[selected] = False
        unrefined = current.submesh([mask], append=True)

        # Merge
        current = trimesh.util.concatenate([refined, unrefined])
        print(f"[INFO] Iteration {i+1}: Subdivided {len(selected)} largest faces")

    return current

def process_shell(shell, spacing=0.2, max_edge=5, max_iter=5, batch_size=1000):
    # Step 1: Mesh the shell in OCC
    mesh_shell(shell)

    # Step 2: Extract mesh as numpy arrays
    verts, faces = extract_mesh_from_shell_transformed(shell)
    if verts is None:
        print("[WARN] Shell has no triangulated geometry.")
        return None

    # Step 3: Convert to trimesh
    tri_mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)

    # Step 4: Selectively subdivide large faces
    tri_mesh = subdivide_largest_faces(tri_mesh, max_edge=max_edge, max_iter=max_iter, batch_size=batch_size)

    # Step 5: Sample surface with point spacing
    area_per_point = math.pi * spacing ** 2
    n_points = int(tri_mesh.area / area_per_point)
    sampled_points, _ = sample_surface_even(tri_mesh, count=n_points)

    # Step 6: Build KDTree
    tree = cKDTree(sampled_points)

    # Step 7: Clean up large mesh objects to save memory
    del tri_mesh, verts, faces
    gc.collect()

    return sampled_points, tree

from OCC.Core.BRep import BRep_Tool
from OCC.Core.TopLoc import TopLoc_Location

def extract_mesh_from_shell_transformed(shell):
    vertices = []
    faces = []
    index_offset = 0

    exp = TopExp_Explorer(shell, TopAbs_FACE)
    while exp.More():
        face = exp.Current()
        loc = TopLoc_Location()
        triangulation = BRep_Tool.Triangulation(face, loc)
        if triangulation is None:
            exp.Next()
            continue

        trsf = loc.Transformation()  # ✅ This is the transformation for this face
        n_pts = triangulation.NbNodes()

        occ_vertices = np.array([
            np.dot(
                np.array([
                    trsf.Value(1, 1) * triangulation.Node(i + 1).X() +
                    trsf.Value(1, 2) * triangulation.Node(i + 1).Y() +
                    trsf.Value(1, 3) * triangulation.Node(i + 1).Z() +
                    trsf.Value(1, 4),

                    trsf.Value(2, 1) * triangulation.Node(i + 1).X() +
                    trsf.Value(2, 2) * triangulation.Node(i + 1).Y() +
                    trsf.Value(2, 3) * triangulation.Node(i + 1).Z() +
                    trsf.Value(2, 4),

                    trsf.Value(3, 1) * triangulation.Node(i + 1).X() +
                    trsf.Value(3, 2) * triangulation.Node(i + 1).Y() +
                    trsf.Value(3, 3) * triangulation.Node(i + 1).Z() +
                    trsf.Value(3, 4)
                ]),
                np.identity(3)
            )
            for i in range(n_pts)
        ])

        # Extract triangle connectivity
        tris = triangulation.Triangles()
        n_tris = tris.Length()
        occ_faces = np.array([
            [tris.Value(i + 1).Value(1) - 1 + index_offset,
             tris.Value(i + 1).Value(2) - 1 + index_offset,
             tris.Value(i + 1).Value(3) - 1 + index_offset]
            for i in range(n_tris)
        ])

        vertices.append(occ_vertices)
        faces.append(occ_faces)
        index_offset += n_pts
        exp.Next()

    if not vertices:
        return None
    
    return np.vstack(vertices), np.vstack(faces)



def query_kdtree_once(index, query_point, shape_info):
    path = shape_info[f"{index}"]["kdtreepath"]
    if not path: return None

    data = joblib.load(path)
    points, tree = data["points"], data["tree"]

    distance, idx = tree.query(query_point)
    closest = points[idx]

    del points, tree, data
    gc.collect()

    return index, distance, closest




def main():
    # Create a simple box shape
    box_shape = BRepPrimAPI_MakeBox(1, 1, 30).Shape()

    samples = 100

    sphere_points = np.random.uniform(
        low=(0, 0, 30.1),
        high=(1000, 1000,  30.2),
        size=(samples, 3)
    )


    # Extract the shell from the box
    shells = []
    exp = TopExp_Explorer(box_shape, TopAbs_SHELL)
    while exp.More():
        shell = topods.Shell(exp.Current())
        shells.append(shell)
        exp.Next()

    # For now, just test with the first shell
    shell = shells[0]

    tri_mesh = convert_shell_to_trimesh(shell, max_triangle_area=0.01)
    max_triangle_area = 2
    max_edge = math.sqrt(4 * max_triangle_area / math.sqrt(3))

    tri_mesh = subdivide_largest_faces(tri_mesh,max_edge=5)
    
    sampled_points, tree = build_collision_checker(tri_mesh, spacing=0.2)

    for i in range(samples):
        x, y ,z = sphere_points[i]
        vertex = BRepBuilderAPI_MakeVertex(gp_Pnt(x, y, z)).Vertex()
        dist, closest_pt, is_close = query_closest_point(tree, sampled_points, sphere_points[i], max_distance=2)

        distance, point = find_minimum_distance(vertex, box_shape)
        print(f" Real closest point: {point}, Real distance {distance}")
        print(f" Closest point: {closest_pt}, distance: {dist}")

if __name__ == "__main__":
    main()
