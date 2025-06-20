





def mesh_shell(shell, max_triangle_area=0.01):
    # Approximate maximum edge length from area
    max_edge_length = math.sqrt(4 * max_triangle_area / math.sqrt(3))

    # Perform meshing
    mesh = BRepMesh_IncrementalMesh(shell,1e-1, False, 1e-1, True)
    mesh.Perform()
    return mesh



def query_kdtree_once(index, query_point, all_shapes):
    path = all_shapes[f"{index}"]["ckdottree"]
    if not path: return None

    data = joblib.load(path)
    points, tree = data["points"], data["tree"]

    distance, idx = tree.query(query_point)
    closest = points[idx]

    del points, tree, data
    gc.collect()

    return index, distance, closest