import numpy as np


def point_to_triangle_distance_and_closest_point(p, a, b, c):
    """
    Compute the shortest distance from point p to triangle abc
    and return the exact closest point on the triangle.
    """
    # Edge vectors
    ab = b - a
    ac = c - a
    ap = p - a

    # Compute dot products
    d1 = np.dot(ab, ap)
    d2 = np.dot(ac, ap)

    # Check if P is in vertex region outside A
    if d1 <= 0 and d2 <= 0:
        return np.linalg.norm(ap), a

    # Check if P is in vertex region outside B
    bp = p - b
    d3 = np.dot(ab, bp)
    d4 = np.dot(ac, bp)
    if d3 >= 0 and d4 <= d3:
        return np.linalg.norm(bp), b

    # Check if P is in vertex region outside C
    cp = p - c
    d5 = np.dot(ab, cp)
    d6 = np.dot(ac, cp)
    if d6 >= 0 and d5 <= d6:
        return np.linalg.norm(cp), c

    # Check if P is in edge region of AB
    vc = d1 * d4 - d3 * d2
    if vc <= 0 and d1 >= 0 and d3 <= 0:
        v = d1 / (d1 - d3)
        closest = a + v * ab
        return np.linalg.norm(p - closest), closest

    # Check if P is in edge region of AC
    vb = d5 * d2 - d1 * d6
    if vb <= 0 and d2 >= 0 and d6 <= 0:
        w = d2 / (d2 - d6)
        closest = a + w * ac
        return np.linalg.norm(p - closest), closest

    # Check if P is in edge region of BC
    va = d3 * d6 - d5 * d4
    if va <= 0 and (d4 - d3) >= 0 and (d5 - d6) >= 0:
        w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        closest = b + w * (c - b)
        return np.linalg.norm(p - closest), closest

    # P is inside face region
    denom = 1.0 / (va + vb + vc)
    v = vb * denom
    w = vc * denom
    closest = a + ab * v + ac * w
    return np.linalg.norm(p - closest), closest




from scipy.spatial import cKDTree

def find_closest_point_on_shape(p, triangles, centroids, radius=20.0):
    """
    For a given point `p`, search for closest point on shape using triangles.
    Returns min distance, closest point, and triangle.
    """
    kdtree = cKDTree(centroids)
    idxs = kdtree.query_ball_point(p, radius)

    min_dist = float('inf')
    closest_pt = None
    closest_tri = None

    for i in idxs:
        a, b, c = triangles[i]
        dist, pt = point_to_triangle_distance_and_closest_point(np.array(p), a, b, c)
        if dist < min_dist:
            min_dist = dist
            closest_pt = pt
            closest_tri = (a, b, c)

    return min_dist, closest_pt, closest_tri
