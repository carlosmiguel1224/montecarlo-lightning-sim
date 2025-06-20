from trimeshtest import *
from montecarlohelper import *
from findingmaxz_readingfile import *
from util import *
from OCC.Core.BRep import BRep_Builder
from OCC.Core.TopoDS import TopoDS_Compound
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeSphere
from savingtree import *
import math
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
import matplotlib.colorbar as colorbar
import matplotlib.colors as mcolors
from matplotlib.ticker import FuncFormatter
from matplotlib.colors import LinearSegmentedColormap, LogNorm
from matplotlib.colors import ListedColormap
from OCC.Core.AIS import AIS_Point
from OCC.Core.Aspect import Aspect_TOM_PLUS, Aspect_TOM_O  # Corrected!
from OCC.Core.Prs3d import Prs3d_PointAspect
from OCC.Core.Geom import Geom_Point
from OCC.Core.Geom import Geom_CartesianPoint
import sqlite3
matplotlib.use("Qt5Agg")
import psutil



def memory_usage_fraction():
    mem = psutil.virtual_memory()
    return mem.used / mem.total


def clear_collision_db(db_path="collisions.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM collisions")
    conn.commit()
    conn.close()


def insert_shape_metadata(shape_info, simulation_id, db_path="collisions.db"):

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    shape_data_batch = []
    for shape_id, info in shape_info.items():
        shape_data_batch.append((
            shape_id,
            simulation_id,
            info.get("name"),
            str(info.get("coords")),
            info.get("count"),
            info.get("collectarea"),
            info.get("percentofstrikes"),
            info.get("kdtreepath")
        ))

    cursor.executemany("""
        INSERT INTO shape_metadata (
            shape_id,
            simulation_id,
            name,
            coords,
            count,
            collectarea,
            percentofstrikes,
            kdtreepath
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, shape_data_batch)

    conn.commit()
    conn.close()



def insert_total_collisions_into_db(simulation_id,data_batch, db_path="collisions.db"):
    if not data_batch:
        return  # Nothing to insert
    if not simulation_id:
        print("Sim id is None")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.executemany("""
        INSERT INTO collisions (
            center_on_contact,
            surface_on_contact,
            peakcurrent,
            strike,
            structurestruck,
            count,
            simulation_id
        ) VALUES (?, ?, ?, ?, ?, ?,?)
    """, [
        (
            entry["center_on_contact"],
            entry["surface_on_contact"],
            entry["peakcurrent"],
            entry["strike"],
            entry["structurestruck"],
            entry["count"],
            simulation_id
        )
        for entry in data_batch
    ])

    conn.commit()
    conn.close()



def display_strike_vertex(display,color, point, current, polarity: str):

    gp_point = gp_Pnt(*point)
    geom_point = Geom_CartesianPoint(gp_point)
    ais_point = AIS_Point(geom_point)

    marker_type = Aspect_TOM_PLUS if polarity == "positive" else Aspect_TOM_O

    # Construct Prs3d_PointAspect with required args
    aspect = Prs3d_PointAspect(marker_type, color, 2.0)

    ais_point.Attributes().SetPointAspect(aspect)
    display.Context.Display(ais_point, False)

# Define the custom blue-to-red colormap skipping green
_custom_cmap = ListedColormap([
    "#0000FF",  # Blue
    "#00BFFF",  # DeepSkyBlue
    "#FFFF00",  # Yellow
    "#FFA500",  # Orange
    "#FF0000"   # Red
], name="custom_b2r")

def peak_current_to_rgb_custom(current, min_current=4, max_current=400, cmap=_custom_cmap):
    """
    Maps peak current to a Quantity_Color using a custom colormap.

    Args:
        current (float): Peak current (kA).
        min_current (float): Minimum current value.
        max_current (float): Maximum current value.
        cmap: Matplotlib colormap (defaults to custom blue-to-red).

    Returns:
        Quantity_Color: OpenCascade-compatible RGB color.
    """
    norm = mcolors.LogNorm(vmin=min_current, vmax=max_current)
    rgba = cmap(norm(current))
    r, g, b = rgba[:3]
    return Quantity_Color(r, g, b, Quantity_TOC_RGB)


def show_colormap_legend_custom(min_current=4, max_current=400):
    # Custom colormap: Blue → Yellow → Orange → Red
    custom_cmap = LinearSegmentedColormap.from_list(
        'blue_yellow_red',
        ['#0000FF', '#FFFF00', '#FFA500', '#FF0000'],  # blue → yellow → orange → red
        N=256
    )

    fig, ax = plt.subplots(figsize=(8, 1.2))
    fig.subplots_adjust(bottom=0.5)

    norm = LogNorm(vmin=min_current, vmax=max_current)
    cb1 = colorbar.ColorbarBase(ax, cmap=custom_cmap, norm=norm, orientation='horizontal')

    # Show tick labels with actual values instead of scientific notation
    tick_values = [4, 10, 20, 50, 100, 200, 400]
    cb1.set_ticks(tick_values)
    cb1.set_ticklabels([str(v) for v in tick_values])

    cb1.set_label('Peak Current (kA)')
    plt.show()

    return custom_cmap

def peak_current_to_rgb(current, min_current=4, max_current=400, cmap=cm.turbo):
    log_min = math.log10(min_current)
    log_max = math.log10(max_current)
    log_val = math.log10(current)
    norm_val = (log_val - log_min) / (log_max - log_min)
    r, g, b, _ = cmap(1.0 - norm_val)  # returns RGBA
    return Quantity_Color(r, g, b, Quantity_TOC_RGB)


def show_colormap_legend_no_label(min_current=4, max_current=400, cmap=cm.inferno):
    fig, ax = plt.subplots(figsize=(6, 1))
    fig.subplots_adjust(bottom=0.5)

    norm = mcolors.LogNorm(vmin=min_current, vmax=max_current)
    cb1 = colorbar.ColorbarBase(ax, cmap=cmap, norm=norm, orientation='horizontal')
    cb1.set_label('Peak Current (kA)')
    plt.show()




def show_colormap_legend(min_current=4, max_current=400, cmap=cm.turbo):
    fig, ax = plt.subplots(figsize=(8, 1))
    fig.subplots_adjust(bottom=0.5)

    norm = mcolors.LogNorm(vmin=min_current, vmax=max_current)
    tick_values = [4, 10, 20, 50, 100, 200, 400]

    cb1 = colorbar.ColorbarBase(
        ax, cmap=cmap, norm=norm, orientation='horizontal',
        ticks=tick_values
    )

    # Use FuncFormatter to preserve interactivity
    formatter = FuncFormatter(lambda x, _: f'{int(x)}')
    cb1.ax.xaxis.set_major_formatter(formatter)

    cb1.set_label('Peak Current (kA)')

    plt.show()


def run_sim_trimesh(display,samples,z_max,shape_info, all_shapes, XBOUNDS, YBOUNDS,SIM_ID, meters=True, area_for_floor=None, pos_min=4,neg_min=4,pos_max=400,neg_max=200,curtoradpos=None,curtoradneg=None):
    global_tree_cache = {}
    
    for ind ,shape in enumerate(all_shapes):
        test_point = gp_Pnt(0, 0, z_max)
        test_vertex = BRepBuilderAPI_MakeVertex(test_point).Vertex()
        result = new_distshape_with_timeout(ind, shape, test_vertex,0.1)
        #print(f"Test result for shapeid {ind} is: {result}")
        floor_index = find_floor_index(all_shapes)
        if result is not None or compute_volume(shape) >= 1e8 or (ind == floor_index):
        #if (compute_volume(shape) >= 1e6 or ind == len(all_shapes) - 1) and (result is not None and compute_volume(shape) >= 1e7):
            print(f"Shape id {ind} is not getting meshed")
            continue
        #shape = extract_shell_from_solid(shape)
        points, tree = process_shell(shape)
        shape_info[f"{ind}"]["kdtreepath"] = save_points_and_tree(ind, points, tree)

        path = shape_info[f"{ind}"].get("kdtreepath")
        if ind not in global_tree_cache:
            global_tree_cache[ind] = joblib.load(path)
    start = time.time()
    samples = samples
    delta = 50

    total_collision_info = []


    #This is for the heatmap on the groundpoints
    builder = BRep_Builder()
    vertcompound = TopoDS_Compound()
    builder.MakeCompound(vertcompound)


    builder = BRep_Builder()
    befvertcompound = TopoDS_Compound()
    builder.MakeCompound(befvertcompound)
    

    peak_currents = bulk_log_distribution(bulk_positive_negative_strikes(samples),pos_max=pos_max, neg_max=neg_max, pos_min=pos_min, neg_min=neg_min)
    radii = bulk_sphere_radii(peak_currents)
    sphere_points = points_with_radii(XBOUNDS,YBOUNDS, radii ,samples, z_max + delta)
    object_bboxes = [(i, shape, get_bbox(shape)) for i ,shape in enumerate(all_shapes)]
    #print("done with points")

    counter = 0

    for i in range(samples):

        counter += 1
        print(counter)

        point = sphere_points[i]
        x = point.X()
        y = point.Y()
        z = point.Z()

        radius = radii[i]
        current = peak_currents[0][i]
        strike = peak_currents[1][i]

        vertex = BRepBuilderAPI_MakeVertex(point).Vertex()
        

        spherepoint = BRep_Tool.Pnt(vertex)
        sphere = BRepPrimAPI_MakeSphere(spherepoint,radius).Shape()
        #builder.Add(befvertcompound, sphere)
        #display.DisplayShape(sphere, update= False, color = Quantity_NOC_YELLOW,transparency=.9)

        total_traveled = 0

        sphere_bbox = get_sphere_bbox(point, radius)
        candidate_shapes = [(i, shape) for i, shape, bbox in object_bboxes if not sphere_bbox.IsOut(bbox)]


        #initializing the tree before we get into loop for abs_min_distance
        #for shape_i, _ in candidate_shapes:
            #path = shape_info[f"{shape_i}"].get("kdtreepath")
            #if path and shape_i not in global_tree_cache:
                #global_tree_cache[shape_i] = joblib.load(path)
        
        while True:
            
            index ,distance, groundpoint = kdot_distshape_abs_min_distance((x,y,z), candidate_shapes, shape_info, global_tree_cache)
            
            if  -.25 <= (distance-radius) <= .25: #distance <= radius + .1
                print("We are out of loop")
                break

            moving = smart_move(distance,radius, factor=.99, min_step=.001)

            z -= moving
            #print(z)

            total_traveled += moving
            vertex = BRepBuilderAPI_MakeVertex(gp_Pnt(point.X(),point.Y(), z)).Vertex()

        print(f"This is current RAM usage: {memory_usage_fraction()}")
        if memory_usage_fraction() >= .90:
            del global_tree_cache[next(iter(global_tree_cache))]
            gc.collect()
            
        #ground_vert = BRepBuilderAPI_MakeVertex(gp_Pnt(groundpoint[0],groundpoint[1], groundpoint[2])).Vertex()
        #ground_sphere = BRepPrimAPI_MakeSphere(gp_Pnt(groundpoint.X(),groundpoint.Y(), groundpoint.Z()), radius).Shape()
        if  i <= 10000:
            vert_color = peak_current_to_rgb_custom(current)
            #display.DisplayShape(ground_vert, color =vert_color, update = False)
            display_strike_vertex(display, vert_color, (groundpoint[0],groundpoint[1], groundpoint[2]), current, strike)
        
        #builder.Add(vertcompound, ground_vert)
        #spherepoint = gp_Pnt(point.X(),point.Y(), z)

        #for sphere demonstration
        #sphere = BRepPrimAPI_MakeSphere(spherepoint,radius).Shape()
        #display.DisplayShape(sphere, update= False, color = Quantity_NOC_RED,transparency=.9)
        shape_info[f"{index}"]["count"] += 1
        total_collision_info.append({"center_on_contact": f"{point.X()},{point.Y()},{z}", 
        "surface_on_contact":f"{groundpoint[0]},{groundpoint[1]},{groundpoint[2]}", "peakcurrent":current,
        "strike":strike,"structurestruck": shape_info[f"{index}"].get("name") or f"shapeid:{index}", "count":shape_info[f"{index}"]["count"]})

        #print(total_collision_info[:20])
        if len(total_collision_info) >= 10000:
            insert_total_collisions_into_db(SIM_ID,total_collision_info)
            total_collision_info.clear()

    print("Done in", time.time() - start, "seconds")
    if total_collision_info:
        insert_total_collisions_into_db(SIM_ID,total_collision_info)
        total_collision_info.clear()

    global_tree_cache.clear()
    gc.collect()
    for i in range(len(all_shapes)):
        #print(shape_info[f"{i}"]["count"])
        shape_info[f"{i}"]["collectarea"] = collection_area(samples,XBOUNDS,YBOUNDS, shape_info[f"{i}"]["count"])
        shape_info[f"{i}"]["percentofstrikes"] = (shape_info[f"{i}"]["count"]/samples)
    
    #print(shape_info)
    if shape_info:
        insert_shape_metadata(shape_info,SIM_ID)
    #all_shapes.append(vertcompound)
    #export_simulation_to_csv(SIM_ID)

    return (shape_info, total_collision_info, samples, vertcompound, befvertcompound)

def main():
    samples = 100000
    display, start_display, add_menu, add_function_to_menu = init_display()
    file = 'box_with_hole.stp'
    shape_info = {}
    all_shapes = []
    transformed_file = read_step_and_transform(file)
    Z_max,Z_min, X_max, Y_max, X_min, Y_min = get_max_z_from_shape_modified(transformed_file)
    center_x = (X_min + X_max) / 2
    center_y = (Y_min + Y_max) / 2
    print(center_x, center_y)
    all_shapes = extract_shapes(transformed_file, solid = False,shell=True, compound=False)

    XBOUNDS, YBOUNDS = calculate_valid_range(X_max,Y_max,X_min,Y_min,10*(200**(.67)))

    floor = create_centered_floor(XBOUNDS,YBOUNDS)
    #display.DisplayShape(floor,update = False,color= Quantity_NOC_GREEN)

    all_shapes.append(floor)
    
    for i in range(len(all_shapes)):
        shape = all_shapes[i]
        
        #display.DisplayMessage(message_point, f"id for shape {i}")
        shape_handle = display.DisplayShape(shape, update = False, transparency=.9)[0]
        shape_info[f"{i}"] = {"shape":shape, "name":None, "shapehandle":shape_handle, "count":0, "kdtreepath": None}


    for i ,shape in enumerate(all_shapes):
        if i not in (238, 239) and (compute_volume(shape) >= 1e6 or i == len(all_shapes) - 1):
            continue

        points, tree = process_shell(shape)
        shape_info[f"{i}"]["kdtreepath"] = save_points_and_tree(i, points, tree)

    start = time.time()
    shape_info, _, _, vertcompound, _ = run_sim_trimesh(display,samples,Z_max,shape_info, all_shapes, XBOUNDS, YBOUNDS)
    print(f"Simulation done in {time.time() - start}")
    #display.DisplayShape(vertcompound, update = False, color= Quantity_NOC_YELLOW)
    print(shape_info)
    show_colormap_legend_custom()
    start_display()

if __name__ == "__main__":
    main()
    clear_collision_db()