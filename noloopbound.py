from montecarlohelper import *
from util import *
from findingmaxz_readingfile import *
from runsimtrimesh import *
from window import *
import time
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Common
from OCC.Core.AIS import AIS_Shape
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QInputDialog
from PyQt5.QtWidgets import QApplication, QSlider, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Splitter
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_SOLID
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Splitter
from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.TopTools import TopTools_ListOfShape
from OCC.Core.BRep import BRep_Builder
from OCC.Core.TopoDS import TopoDS_Compound
from OCC.Core.TopAbs import TopAbs_SHAPE
from OCC.Core.SelectMgr import SelectMgr_Selection
tagging_mode = False
view_mode = False
cutting_mode = False
grouping_mode = False
mesh_mode = False
remove_mode = False
SIM_ID = None
all_shapes = []
shape_info = {}

app = QApplication(sys.argv)
dialog = StepFileSelector()
if dialog.exec_() == QDialog.Accepted:
    file = dialog.selected_file_path
else:
    sys.exit()
display, start_display, add_menu, add_function_to_menu = init_display()
#file = 'E01-18-06-000B.STEP'
transformed_file =read_step_and_transform(file)

Z_max, X_max, Y_max, X_min, Y_min = get_max_z_from_shape(transformed_file)


XBOUNDS, YBOUNDS = calculate_valid_range(X_max,Y_max,X_min,Y_min,10*(200**(.67)))

def create_new_project(project_name, db_path="collisions.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO projects (name) VALUES (?)", (project_name,))
    conn.commit()
    sim_id = cursor.lastrowid
    conn.close()
    return sim_id

def create_placeholder_project(db_path="collisions.db"):
    return create_new_project("Untitled Project", db_path)


def update_project_name(simulation_id, new_name, db_path="collisions.db"):
    if simulation_id is None:
        print("Simulation has not been ran yet")
        return
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE projects SET name = ? WHERE simulation_id = ?", (new_name, simulation_id))
    conn.commit()
    conn.close()


def list_all_projects(db_path="collisions.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT simulation_id, name, timestamp FROM projects")
    results = cursor.fetchall()
    conn.close()
    return results

def get_plane_selection():
    items = ["x", "y", "z"]
    plane, ok = QInputDialog.getItem(None, "Select Plane", "On what plane would you like to make the cut?", items, 0, False)
    
    if ok and plane:
        return plane
    else:
        return None  # User canceled or didn't select



def sync_shape_info_to_all_shapes():
    global shape_info, all_shapes
    new_info = {}
    for idx, shape in enumerate(all_shapes):
        for old_data in shape_info.values():
            if old_data["shape"].IsSame(shape):
                new_info[str(idx)] = {
                    "shape": shape,
                    "name": old_data.get("name"),
                    "shapehandle": old_data.get("shapehandle"),
                    "coords": old_data.get("coords"),
                    "count": 0,
                    "kdtreepath": None
                }
                break
    shape_info = new_info


def remove_shape_from_list(target_shape, all_shapes):
    # Make a new list with everything except the shape that IsSame() as target_shape
    return [shape for shape in all_shapes if not shape.IsSame(target_shape)]

def find_index_of_shape(target_shape, all_shapes):
    return [i for i, shape in all_shapes if shape.IsSame(target_shape)]

def on_shape_clicked(clicked_shape, *args):
    global tagging_mode, view_mode, shape_info, cutting_mode, all_shapes, grouping_mode, mesh_mode,remove_mode, SIM_ID, XBOUNDS, YBOUNDS, Z_max

    if not (tagging_mode or view_mode or cutting_mode or grouping_mode or mesh_mode or remove_mode):
        return

    if not clicked_shape:
        print("⚠️ No shape selected — click directly on a visible shape.")
        return

    clicked_shape = clicked_shape[0]
    for key, data in shape_info.items():
        if data["shape"].IsSame(clicked_shape):
            if tagging_mode:
                name, ok = QInputDialog.getText(None, "Tag Shape", f"Enter name for shape {key}:")
                if ok and name:
                    data["name"] = name
                    QMessageBox.information(None, "Shape Tagged", f"✅ Tagged shape {key} as '{name}'")
                else:
                    QMessageBox.information(None, "Tagging Cancelled", f"No name entered for shape {key}")
                tagging_mode = False
                return
            elif view_mode:
                name = data.get("name", f"Shape {key}")
                coords = data.get("coords", ("N/A", "N/A", "N/A"))
                count = data.get("count", "N/A")
                zmax_info = get_max_z_from_shape_modified(data["shape"])
                collection_area = data.get("collectarea", "N/A")

                # Replace with real data you want to plot
                #histogram_data = [random.uniform(10, 50) for _ in range(100)]  # Example

                shape_data = {
                    "id": key,
                    "name": name,
                    "coords": coords,
                    "count": count,
                    "zmax_info": zmax_info,
                    "collectarea": collection_area
                }

                dialog = ShapeInfoDialog(shape_data,SIM_ID)
                dialog.exec_()
                
                view_mode = False
                return
            elif cutting_mode:
                selected_shape_id_for_cut = key
                print(f"✅ Selected shape {key} for cutting.")

                # Get shape and center for plane
                shape = data["shape"]
                plane_for_cut = get_plane_selection()
                if not plane_for_cut:
                    cutting_mode = False
                    return
                x = 0
                y = 0
                z = 0
                zmax, zmin , xmax, ymax, xmin, ymin = get_max_z_from_shape_modified(shape)
                print(zmax, zmin , xmax, ymax, xmin, ymin)
                if plane_for_cut == "x":
                    x = 1
                elif plane_for_cut == "y":
                    y = 1
                elif plane_for_cut == "z":
                    z = 1
                x_height = ((xmin + xmax)/2)
                y_height = ((ymin + ymax)/2)
                z_height = ((zmin + zmax)/2)
                plane = gp_Pln(gp_Pnt(x_height, y_height, z_height), gp_Dir(x, y, z))  # Z-direction plane
                face = BRepBuilderAPI_MakeFace(plane, -1000, 1000, -1000, 1000).Shape()
                face_handle = display.DisplayShape(face, update=False, transparency=.9, color=Quantity_NOC_BLUE1)[0]
                ok = False
                result = ''
                while result != QMessageBox.Yes:
                    if x == 1:
                        change, ok = QInputDialog.getDouble(None, "Change Plane Height", "X height:")
                        display.Context.Remove(face_handle, True)
                        x_height += change
                        plane = gp_Pln(gp_Pnt(x_height, y_height, z_height), gp_Dir(x, y, z)) 
                        face = BRepBuilderAPI_MakeFace(plane, -1000, 1000, -1000, 1000).Shape()
                        face_handle = display.DisplayShape(face ,update=False, transparency=.8, color=Quantity_NOC_BLUE1)[0]
                        if ok == False:
                            break
                    elif y == 1:
                        change, ok = QInputDialog.getDouble(None, "Change Plane Height", "Y height:")
                        display.Context.Remove(face_handle, True)
                        y_height += change
                        plane = gp_Pln(gp_Pnt(x_height, y_height, z_height), gp_Dir(x, y, z)) 
                        face = BRepBuilderAPI_MakeFace(plane, -1000, 1000, -1000, 1000).Shape()
                        face_handle = display.DisplayShape(face ,update=False, transparency=.8, color=Quantity_NOC_BLUE1)[0]
                        if ok == False:
                            break
                    elif z == 1:
                        change, ok = QInputDialog.getDouble(None, "Change Plane Height", "Z height:")
                        display.Context.Remove(face_handle, True)
                        z_height += change
                        plane = gp_Pln(gp_Pnt(x_height, y_height, z_height), gp_Dir(x, y, z)) 
                        face = BRepBuilderAPI_MakeFace(plane, -1000, 1000, -1000, 1000).Shape()
                        face_handle = display.DisplayShape(face ,update=False, transparency=.8, color=Quantity_NOC_BLUE1)[0]
                        if ok == False:
                            break
                    result = QMessageBox.question(None, "Confirm Cut", "Do you want to cut here?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if result == QMessageBox.Yes:
                    
                    #print(shape)
                    #print(len(all_shapes))
                    #print(all_shapes)
                    #deleting shape information from global dictionary. Replacing this with 2 entries
                    print(all_shapes)
                    shape_handle =shape_info[f"{key}"]["shapehandle"]
                    display.Context.Remove(shape_handle, True)
                    del shape_info[f"{key}"]
                    #del all_shapes[int(key)]
                    # Create and populate TopTools_ListOfShape for arguments and tools
                    args = TopTools_ListOfShape()
                    args.Append(shape)

                    tools = TopTools_ListOfShape()
                    tools.Append(face)

                    # Set up and execute splitter
                    splitter = BRepAlgoAPI_Splitter()
                    splitter.SetArguments(args)
                    splitter.SetTools(tools)
                    splitter.Build()

                    # Collect resulting solids
                    split_shapes: list[TopoDS_Shape] = []
                    explorer = TopExp_Explorer(splitter.Shape(), TopAbs_SOLID)
                    while explorer.More():
                        split_shapes.append(explorer.Current())
                        explorer.Next()

                    #print(f"shapes: {split_shapes}")
                    #print(f"Split resulted in {len(split_shapes)} solid(s).")
                    


                    #print(split_shapes[0])
                    #print(split_shapes[1])
                    all_shapes = remove_shape_from_list(shape, all_shapes)
                    #need to append at location of index
                    all_shapes.insert(int(key),split_shapes[0])
                    all_shapes.append(split_shapes[1])

                    shape1_handle =display.DisplayShape(split_shapes[0], update = False, transparency=.9)[0]
                    shape2_handle = display.DisplayShape(split_shapes[1], update = False, transparency=.9)[0]
                    
                    shape_info[f"{key}"] = {"shape":split_shapes[0],"name": None, "shapehandle": shape1_handle, "count": 0,"kdtreepath": None}
                    shape_info[f"{len(all_shapes)-1}"] = {"shape":split_shapes[1],"name": None, "shapehandle": shape2_handle, "count": 0,"kdtreepath": None}
                    print(shape_info)
                    print(all_shapes)
                    display.Context.Remove(face_handle, True)
                    cutting_mode = False
                    return
                    #print(shape_info)
                    

                #remove plane
                display.Context.Remove(face_handle, True)
                cutting_mode = False
                return
            elif grouping_mode:
                shape = data["shape"]

                # Store clicked shapes in a persistent list
                if not hasattr(display, "current_group"):
                    display.current_group = []

                # Check if shape already added
                existing_keys = [entry[0] for entry in display.current_group]
                if key in existing_keys:
                    QMessageBox.information(None, "Already Added", f"Shape {key} is already in the group.")
                else:
                    display.current_group.append((key, shape, data["shapehandle"]))
                    print(f"Added shape {key} to group.")

                result = QMessageBox.question(None, "Finish Group?",
                                              "Do you want to finish this group?",
                                              QMessageBox.Yes | QMessageBox.No,
                                              QMessageBox.No)
                if result == QMessageBox.Yes:
                    # Build compound from group
                    compound = TopoDS_Compound()
                    builder = BRep_Builder()
                    builder.MakeCompound(compound)
                    for _, shape_in_group, _ in display.current_group:
                        builder.Add(compound, shape_in_group)

                    # Clean up old shapes
                    print(shape_info)
                    #for key_in_group, _, handle in display.current_group:
                        #display.Context.Remove(handle, True)
                        #all_shapes = remove_shape_from_list(shape_info[f"{key_in_group}"]["shape"], all_shapes)
                        #shape_info.pop(f"{key_in_group}", None)
                        # all_shapes is a list, so we use remove_shape_from_list utility

                        #here we need to add fixing the indexed for the other elements 

                    # Add compound to display and data structures
                    handle = display.DisplayShape(compound, update=False, transparency=0.9)[0]
                    handle.SelectionMode(AIS_Shape.SelectionMode(TopAbs_COMPOUND))
                    display.Context.UpdateCurrentViewer()
                    all_shapes.append(compound)
                    shape_info[str(len(all_shapes)-1)] = {
                        "shape": compound,
                        "name": None,
                        "shapehandle": handle,
                        "count": 0,
                        "kdtreepath": None
                    }

                    for key_in_group, _, handle in display.current_group:
                        display.Context.Remove(handle, True)
                        all_shapes = remove_shape_from_list(shape_info[f"{key_in_group}"]["shape"], all_shapes)
                        shape_info.pop(f"{key_in_group}", None)

                    sync_shape_info_to_all_shapes()
                    del display.current_group
                    grouping_mode = False
                    print("✅ Grouping completed.")
                    print(all_shapes)
                    print(shape_info)
                    print(get_max_z_from_shape_modified(compound))
                    #TOdo FIX THIS CODE
                return
            elif mesh_mode:
                print("We made it to mesh mode")
                name = data.get("name", f"Shape {key}")
                shape = data["shape"]
                result = QMessageBox.question(
                    None,
                    "Mesh Shape?",
                    f"Do you want to mesh {name} for better performance?",QMessageBox.Yes | QMessageBox.No,QMessageBox.No)
                if result == QMessageBox.Yes:
                    points, tree = process_shell(shape)
                    shape_info[f"{key}"]["kdtreepath"] = save_points_and_tree(key, points, tree)
                    QMessageBox.information(
                        None,
                        "Shape Meshed",
                        f"✅ Successfully meshed {name}.\n"
                        "KD-Tree acceleration enabled for faster distance calculations."
                    )
                mesh_mode = False
                return
            elif remove_mode:
                shape_removing = data["shape"]
                handle = data["shapehandle"]
                display.Context.Remove(handle, True)
                all_shapes = remove_shape_from_list(shape_removing, all_shapes)
                shape_info.pop(f"{key}", None)
                sync_shape_info_to_all_shapes()

                floor_index = find_floor_index(all_shapes)
                display.EraseAll()

                all_shapes = remove_shape_from_list(shape_info[f"{floor_index}"]["shape"], all_shapes)
                shape_info.pop(f"{floor_index}", None)
                sync_shape_info_to_all_shapes()
                all_shapes = translate_shapes_to_z0_and_center_xy(all_shapes)
                Z_max, X_max, Y_max, X_min, Y_min = get_max_z_from_shape(make_compound_from_shapes(all_shapes))
                XBOUNDS, YBOUNDS = calculate_valid_range(X_max,Y_max,X_min,Y_min,10*(200**(.67)))
                print(XBOUNDS, YBOUNDS)

                floor = create_centered_floor(XBOUNDS, YBOUNDS)
                all_shapes.append(floor)
                handle = display.DisplayShape(floor, update = False,transparency=.9)[0]
                shape_info[str(len(all_shapes)-1)] = {
                                    "shape": floor,
                                    "name": None,
                                    "shapehandle": handle,
                                    "count": 0,
                                    "kdtreepath": None
                                }
                floor_index = find_floor_index(all_shapes)
                for i ,shape in enumerate(all_shapes):
                    shape_info[f"{i}"]["shape"] = shape
                    if i == floor_index:
                        continue
                    display.DisplayShape(shape, update=False, transparency=.9)[0]
                
                display.Context.UpdateCurrentViewer()
                remove_mode = False
                return








    print("Shape not found in shape_info.")

# --- Menu functions ---
def enable_tagging():
    global tagging_mode, view_mode, cutting_mode, grouping_mode, mesh_mode, remove_mode
    tagging_mode = True
    view_mode = False
    cutting_mode = False
    grouping_mode = False
    mesh_mode = False
    remove_mode = False 
    QMessageBox.information(None, "Tagging","🟢 Tagging mode enabled — click a shape to name it.")

def enable_view_mode():
    global tagging_mode, view_mode, cutting_mode, grouping_mode, mesh_mode, remove_mode
    tagging_mode = False
    view_mode = True
    grouping_mode = False
    cutting_mode = False
    mesh_mode = False
    remove_mode = False 
    QMessageBox.information(None, "View Mode","🔵 View mode enabled — click a shape to see its name.")

def enable_cutting_mode():
    global cutting_mode, tagging_mode, view_mode, grouping_mode, mesh_mode, remove_mode
    cutting_mode = True
    mesh_mode = False
    tagging_mode = view_mode = False
    grouping_mode = False
    remove_mode = False 
    QMessageBox.information(None, "Cutting Mode","🔵 Cutting mode enabled — click a shape to see its name.")

def enable_grouping_mode():
    global cutting_mode, tagging_mode, view_mode, grouping_mode, mesh_mode
    cutting_mode = False
    tagging_mode = False
    mesh_mode = False
    view_mode = False
    grouping_mode = True
    remove_mode = False 
    QMessageBox.information(None, "Grouping","🔵 Grouping mode enabled — click a shape to see its name.")


def mesh_object():
    global cutting_mode, tagging_mode, view_mode, grouping_mode, mesh_mode, remove_mode 
    cutting_mode = False
    tagging_mode = False
    view_mode = False
    grouping_mode = False
    mesh_mode = True
    remove_mode = False 
    QMessageBox.information(None,"Mesh Mode Enabled","⚙️ Mesh Mode is enabled.\nComplex shapes will be meshed to improve performance.\nDistance checks will use KD-Trees based on sampled mesh points.")

def remove_shape_from_screen_and_sim():
    global cutting_mode, tagging_mode, view_mode, grouping_mode, mesh_mode, remove_mode
    cutting_mode = False
    tagging_mode = False
    view_mode = False
    grouping_mode = False
    mesh_mode = False
    remove_mode = True


def clear_previous_sim_results_from_screen():
    global shape_info, all_shapes
    display.EraseAll()
    for shape in all_shapes:
        display.DisplayShape(shape, update = False, transparency=.9)[0]
    display.Context.UpdateCurrentViewer()


def save_simulation_run():
    global SIM_ID
    print(f"This is sim_id: {SIM_ID}")
    parent = None
    if SIM_ID is None:
        QMessageBox.warning(parent, "No Simulation", "Simulation has not been run. No data to save.")
        return

    name, ok = QInputDialog.getText(parent, "Save Project", "What name would you like to save the project as?")
    if ok and name.strip():
        update_project_name(SIM_ID, name.strip())
        QMessageBox.information(parent, "Project Saved", f"Simulation ID {SIM_ID} saved as '{name.strip()}'.")
    elif ok:
        QMessageBox.warning(parent, "Invalid Name", "Project name cannot be empty.")

def open_simulation_selector():
    global SIM_ID
    dialog = SimulationSelectionDialog(SIM_ID)
    if dialog.exec_() == QDialog.Accepted:
        SIM_ID =dialog.selected_sim_id
        print(f"Selected simulation ID: {SIM_ID}")

        

def make_simulation_callback(XBOUNDS, YBOUNDS, z_max, samples):
    def run_simulation():
        global shape_info, all_shapes, SIM_ID, XBOUNDS, YBOUNDS, Z_max  # only the essentials are global
        SIM_ID = create_placeholder_project()
        #display.EraseAll()
        #for shape in all_shapes:
            #display.DisplayShape(shape, update = False, transparency=.9)[0]
        #display.Context.UpdateCurrentViewer()
        

        dialog = SimulationParametersDialog(XBOUNDS, YBOUNDS)
        if dialog.exec_() == QDialog.Accepted:
            params = dialog.get_parameters()
            real_XBOUNDS = params["XBOUNDS"] if params["XBOUNDS"] else XBOUNDS
            real_YBOUNDS = params["YBOUNDS"] if params["YBOUNDS"] else YBOUNDS
            real_samples = params["samples"] if params["samples"] else samples
        else:
            return
        #start = time.time()

        #we are erasing all shapes so we can redo simulations without clogging up the screen
        
        shape_info, total_info, count, vertcompound, befphere = run_sim_trimesh(display,
            real_samples, Z_max, shape_info, all_shapes,
            real_XBOUNDS, real_YBOUNDS, SIM_ID
        )

        #display.DisplayShape(vertcompound, update = False, color= Quantity_NOC_YELLOW)
        #display.DisplayShape(befphere,update = False, color= Quantity_NOC_RED, transparency=.9)
        print(shape_info)
        #print("Done in", time.time() - start, "seconds")
        # Optional: you can refresh display or update labels here
        print("Simulation complete.")
    return run_simulation

def change_orientation():
    global all_shapes, shape_info, XBOUNDS, YBOUNDS, Z_max
    floor_index = find_floor_index(all_shapes)
    print(f"This is floor index {floor_index}")
    #orientation = input("what axis are you changing on X , Y or Z? ")
    """display.EraseAll()
    all_shapes = reorient_shapes_to_z0_and_center_xy(all_shapes,axis=orientation)
    all_shapes = translate_shapes_to_z0_and_center_xy(all_shapes)
    for i ,shape in enumerate(all_shapes):
        shape_info[f"{i}"]["shape"] = shape
        if i == floor_index:
            continue
        display.DisplayShape(shape, update=False, transparency=.9)[0]
    Z_max, X_max, Y_max, X_min, Y_min = get_max_z_from_shape(make_compound_from_shapes(all_shapes))
    XBOUNDS, YBOUNDS = calculate_valid_range(X_max,Y_max,X_min,Y_min,10*(200**(.67)))
    print(XBOUNDS, YBOUNDS)

    floor = create_centered_floor(XBOUNDS, YBOUNDS)
    all_shapes.append(floor)
    handle = display.DisplayShape(floor, update = False,transparency=.9)[0]
    shape_info[str(len(all_shapes)-1)] = {
                        "shape": floor,
                        "name": None,
                        "shapehandle": handle,
                        "count": 0,
                        "kdtreepath": None
                    }
    all_shapes = remove_shape_from_list(shape_info[f"{floor_index}"]["shape"], all_shapes)
    shape_info.pop(f"{floor_index}", None)

    sync_shape_info_to_all_shapes()
    display.Context.UpdateCurrentViewer()"""
    floor_index = find_floor_index(all_shapes)
    display.EraseAll()

    all_shapes = remove_shape_from_list(shape_info[f"{floor_index}"]["shape"], all_shapes)
    shape_info.pop(f"{floor_index}", None)
    sync_shape_info_to_all_shapes()
    all_shapes = reorient_shapes_to_z0_and_center_xy(all_shapes)
    Z_max, X_max, Y_max, X_min, Y_min = get_max_z_from_shape(make_compound_from_shapes(all_shapes))
    XBOUNDS, YBOUNDS = calculate_valid_range(X_max,Y_max,X_min,Y_min,10*(200**(.67)))
    print(XBOUNDS, YBOUNDS)

    floor = create_centered_floor(XBOUNDS, YBOUNDS)
    all_shapes.append(floor)
    handle = display.DisplayShape(floor, update = False,transparency=.9)[0]
    shape_info[str(len(all_shapes)-1)] = {
                        "shape": floor,
                        "name": None,
                        "shapehandle": handle,
                        "count": 0,
                        "kdtreepath": None
                    }
    floor_index = find_floor_index(all_shapes)
    for i ,shape in enumerate(all_shapes):
        shape_info[f"{i}"]["shape"] = shape
        if i == floor_index:
            continue
        display.DisplayShape(shape, update=False, transparency=.9)[0]
    
    display.Context.UpdateCurrentViewer()
    return

def main():
    global all_shapes, shape_info
    #app = QApplication(sys.argv)
    #screen = StartScreen()
    #screen.show()
    samples = 1000
    #file = 'FINAL-BUILDING.STEP'
    #transformed_file =read_step_and_transform(file)

    Z_max, X_max, Y_max, X_min, Y_min = get_max_z_from_shape(transformed_file)


    XBOUNDS, YBOUNDS = calculate_valid_range(X_max,Y_max,X_min,Y_min,10*(200**(.67)))

    floor = create_centered_floor(XBOUNDS,YBOUNDS)
    #display.DisplayShape(floor,update = False,color= Quantity_NOC_GREEN)

    all_shapes = extract_shapes(transformed_file, solid=True,shell=False, compound=False)

    all_shapes.append(floor)
    for i in range(len(all_shapes)):
        shape = all_shapes[i]
        z_max,x_max,y_max,x_min,y_min = get_max_z_from_shape(shape)
        x = -(-x_min+x_max)/2
        y = -(-y_min+y_max)/2
        z = z_max + 10
        message_point = gp_Pnt(x,y,z)
        #display.DisplayMessage(message_point, f"id for shape {i}")
        shape_handle = display.DisplayShape(shape, update = False, transparency=.9)[0]
        shape_info[f"{i}"] = {"coords":(x,y,z), "shape":shape, "name":None, "shapehandle":shape_handle, "count":0,"kdtreepath": None}

    total_collision_info = []
    #print(shape_info)
    display.register_select_callback(on_shape_clicked)
    add_menu("File")
    add_menu("Tools")
    add_menu("Simulation")
    add_function_to_menu("File", save_simulation_run)
    add_function_to_menu("File", open_simulation_selector)
    add_function_to_menu("Tools", enable_tagging)
    add_function_to_menu("Tools", enable_view_mode)
    add_function_to_menu("Tools", enable_cutting_mode)
    add_function_to_menu("Tools", enable_grouping_mode)
    add_function_to_menu("Tools", remove_shape_from_screen_and_sim)
    add_function_to_menu("Tools", mesh_object)
    add_function_to_menu("Tools", change_orientation)
    simulation_callback = make_simulation_callback(XBOUNDS, YBOUNDS, Z_max, samples)
    add_function_to_menu("Simulation", simulation_callback)
    add_function_to_menu("Simulation", clear_previous_sim_results_from_screen)

    print(shape_info)
    show_colormap_legend_custom()
    start_display()


if __name__=="__main__":
    start = time.time()
    main()
    #clear_collision_db()
    delete_all_cached_kdtrees()
    print("Done in", time.time() - start, "seconds")
    