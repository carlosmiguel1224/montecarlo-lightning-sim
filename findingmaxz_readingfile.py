from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.BRepBndLib import brepbndlib_Add
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_SOLID, TopAbs_SHELL, TopAbs_COMPOUND
from OCC.Core.gp import gp_Trsf, gp_Vec
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCC.Core.TopoDS import TopoDS_Shape

def get_max_z_from_shape(shape):
    bbox = Bnd_Box()
    brepbndlib_Add(shape, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
    return zmax, xmax, ymax, xmin, ymin



def get_max_z_from_shape_modified(shape):
    bbox = Bnd_Box()
    brepbndlib_Add(shape, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
    return zmax, zmin, xmax, ymax, xmin, ymin



def get_max_z_from_step(filepath):
    reader = STEPControl_Reader()
    status = reader.ReadFile(filepath)
    if status != 1:
        raise RuntimeError("Failed to read STEP file.")
    
    reader.TransferRoots()
    max_z = float("-inf")
    max_x = float("-inf")
    max_y = float("-inf")
    min_x = float("inf")
    min_y = float("inf")

    n_shapes = reader.NbShapes()
    for i in range(1, n_shapes + 1):
        shape = reader.Shape(i)
        zmax, xmin, xmax, ymin, ymax = get_max_z_from_shape(shape)
        if zmax > max_z:
            max_z = zmax
        if xmax > max_x:
            max_x = xmax
        if ymax > max_y:
            max_y = ymax
        if xmin < min_x:
            min_x = xmin
        if ymin < min_y:
            min_y = ymin

        
    
    return max_z, max_x , max_y, min_x, min_y


def extract_physical_shapes(step_file):
    reader = STEPControl_Reader()
    status = reader.ReadFile(step_file)
    if status != 1:
        raise RuntimeError("Failed to read STEP file.")

    reader.TransferRoots()
    shape = reader.OneShape()

    physical_shapes = []

    # Extract solids
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    while explorer.More():
        physical_shapes.append(explorer.Current())
        explorer.Next()

    # Extract shells
    explorer = TopExp_Explorer(shape, TopAbs_SHELL)
    while explorer.More():
        physical_shapes.append(explorer.Current())
        explorer.Next()

    # Optionally extract compounds (assemblies or groups)
    explorer = TopExp_Explorer(shape, TopAbs_COMPOUND)
    while explorer.More():
        physical_shapes.append(explorer.Current())
        explorer.Next()

    return physical_shapes



def read_step_and_transform(filepath):
    # Read STEP file
    reader = STEPControl_Reader()
    status = reader.ReadFile(filepath)
    if status != 1:
        raise RuntimeError("Failed to read STEP file.")

    reader.TransferRoots()
    shape = reader.OneShape()

    # Compute bounding box
    bbox = Bnd_Box()
    brepbndlib_Add(shape, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()

    # Calculate center in XY and shift in Z
    center_x = (xmin + xmax) / 2
    center_y = (ymin + ymax) / 2
    z_shift = -zmin if zmin < 0 else 0  # ensure Z is non-negative

    # Define transformation
    transform = gp_Trsf()
    transform.SetTranslation(gp_Vec(-center_x, -center_y, z_shift))
    transformer = BRepBuilderAPI_Transform(shape, transform, True)
    transformed_shape = transformer.Shape()

    return transformed_shape



def extract_shapes(shape, solid=True, shell=True, compound=True):
    physical_shapes = []

    # Extract solids
    if solid:
        explorer = TopExp_Explorer(shape, TopAbs_SOLID)
        while explorer.More():
            physical_shapes.append(explorer.Current())
            explorer.Next()

    # Extract shells
    if shell:
        explorer = TopExp_Explorer(shape, TopAbs_SHELL)
        while explorer.More():
            physical_shapes.append(explorer.Current())
            explorer.Next()

    # Optionally extract compounds (assemblies or groups)
    if compound:
        explorer = TopExp_Explorer(shape, TopAbs_COMPOUND)
        while explorer.More():
            physical_shapes.append(explorer.Current())
            explorer.Next()

    return physical_shapes



def read_step_and_transform_centered(step_file):
    reader = STEPControl_Reader()
    status = reader.ReadFile(step_file)
    if status != IFSelect_RetDone:
        raise RuntimeError("Failed to read STEP file.")

    reader.TransferRoots()
    shape = reader.OneShape()

    # Get bounding box
    bbox = Bnd_Box()
    brepbndlib_Add(shape, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()

    # Compute center in XY
    x_center = (xmin + xmax) / 2
    y_center = (ymin + ymax) / 2

    # Translate to center XY and lift Z so zmin = 0
    translation = gp_Trsf()
    translation.SetTranslation(gp_Vec(-x_center, -y_center, -zmin))
    transformer = BRepBuilderAPI_Transform(shape, translation, True)
    transformed_shape = transformer.Shape()

    return transformed_shape


def get_bounding_volume(zmax, zmin, xmax, ymax,xmin,ymin):
    height = zmax - zmin
    length = xmax - xmin
    width = ymax - ymin
    return (length*width*height)




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




def read_step_no_transform_find_center(filepath):
    # Read STEP file
    reader = STEPControl_Reader()
    status = reader.ReadFile(filepath)
    if status != 1:
        raise RuntimeError("Failed to read STEP file.")

    reader.TransferRoots()
    shape = reader.OneShape()

    # Compute bounding box
    bbox = Bnd_Box()
    brepbndlib_Add(shape, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()

    # Calculate center in XY and shift in Z
    center_x = (xmin + xmax) / 2
    center_y = (ymin + ymax) / 2
    z_shift = -zmin if zmin < 0 else 0  # ensure Z is non-negative

    return shape








def main():
    #print(get_max_z_from_step('box_with_hole.stp'))
    file = 'box_with_hole.stp'
    print(get_max_z_from_shape(read_step_and_transform(file)))
    all_shapes = extract_shapes(read_step_and_transform(file))
    print(all_shapes)


if __name__ == "__main__":
    main()