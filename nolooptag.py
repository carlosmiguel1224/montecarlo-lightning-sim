from montecarlohelper import *
from util import *
from findingmaxz_readingfile import *
from runsimfunc import *
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
all_shapes = []
shape_info = {}
display, start_display, add_menu, add_function_to_menu = init_display()


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
                    "coords": old_data.get("coords")
                }
                break
    shape_info = new_info


def remove_shape_from_list(target_shape, all_shapes):
    # Make a new list with everything except the shape that IsSame() as target_shape
    return [shape for shape in all_shapes if not shape.IsSame(target_shape)]

def on_shape_clicked(clicked_shape, *args):
    global tagging_mode, view_mode, shape_info, cutting_mode, all_shapes, grouping_mode

    if not (tagging_mode or view_mode or cutting_mode or grouping_mode):
        return

    if not clicked_shape:
        print("⚠️ No shape selected — click directly on a visible shape.")
        return

    clicked_shape = clicked_shape[0]
    for key, data in shape_info.items():
        if data["shape"].IsSame(clicked_shape):
            if tagging_mode:
                name = input(f"Enter name for shape {key}: ")
                data["name"] = name
                print(f"Tagged shape {key} as '{name}'")
                tagging_mode = False
                return
            elif view_mode:
                name = data.get("name", f"Shape {key}")
                print(f"Shape {key} name: {name}")
                #x, y , z = data.get("coords")
                #display.DisplayMessage(gp_Pnt(x,y,z), f"id for shape {name}")
                #display.EraseAll()
                view_mode = False
                return
            elif cutting_mode:
                selected_shape_id_for_cut = key
                print(f"✅ Selected shape {key} for cutting.")

                # Get shape and center for plane
                shape = data["shape"]
                plane_for_cut= input("On what plane would you like to make the cut? x , y , z ")
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
                    
                    shape_info[f"{key}"] = {"shape":split_shapes[0],"name": None, "shapehandle": shape1_handle, "count": 0}
                    shape_info[f"{len(all_shapes)-1}"] = {"shape":split_shapes[1],"name": None, "shapehandle": shape2_handle, "count": 0}
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
                    for key_in_group, _, handle in display.current_group:
                        display.Context.Remove(handle, True)
                        all_shapes = remove_shape_from_list(shape_info[f"{key_in_group}"]["shape"], all_shapes)
                        shape_info.pop(f"{key_in_group}", None)
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
                        "count": 0
                    }
                    sync_shape_info_to_all_shapes()
                    del display.current_group
                    grouping_mode = False
                    print("✅ Grouping completed.")
                    print(all_shapes)
                    print(shape_info)
                    print(get_max_z_from_shape_modified(compound))
                    #TOdo FIX THIS CODE
                return





    print("Shape not found in shape_info.")

# --- Menu functions ---
def enable_tagging():
    global tagging_mode, view_mode, cutting_mode, grouping_mode
    tagging_mode = True
    view_mode = False
    cutting_mode = False
    grouping_mode = False
    print("🟢 Tagging mode enabled — click a shape to name it.")

def enable_view_mode():
    global tagging_mode, view_mode, cutting_mode, grouping_mode
    tagging_mode = False
    view_mode = True
    grouping_mode = False
    cutting_mode = False
    print("🔵 View mode enabled — click a shape to see its name.")

def enable_cutting_mode():
    global cutting_mode, tagging_mode, view_mode, grouping_mode
    cutting_mode = True
    tagging_mode = view_mode = False
    grouping_mode = False

    print("🔵 Cutting mode enabled — click a shape to see its name.")

def enable_grouping_mode():
    global cutting_mode, tagging_mode, view_mode, grouping_mode
    cutting_mode = False
    tagging_mode = False
    view_mode = False
    grouping_mode = True
    print("🔵 Grouping mode enabled — click a shape to see its name.")


def make_simulation_callback(XBOUNDS, YBOUNDS, z_max, samples):
    def run_sim_callback():
        global shape_info, all_shapes  # only the essentials are global
        start = time.time()
        shape_info, total_info, count, vertcompound = run_sim(
            samples, z_max, shape_info, all_shapes,
            XBOUNDS, YBOUNDS
        )

        display.DisplayShape(vertcompound, update = False, color= Quantity_NOC_YELLOW)
        print(shape_info)
        print("Done in", time.time() - start, "seconds")
        # Optional: you can refresh display or update labels here
        print("Simulation complete.")
    return run_sim_callback





def display_step_file(step_file):
    # Initialize the display
    display, start_display, add_menu, add_function_to_menu = init_display()

    # Create the reader and load the STEP file
    reader = STEPControl_Reader()
    status = reader.ReadFile(step_file)
    
    if status != IFSelect_RetDone:
        raise RuntimeError("Failed to read STEP file.")
    
    # Transfer the root shapes
    reader.TransferRoots()
    
    # Get the first shape (usually the whole assembly or part)
    shape = reader.OneShape()

    # Display the shape
    display.DisplayShape(shape)
    
    # Start the GUI and display the shape interactively
    start_display()



def main():
    global all_shapes, shape_info

    samples = 1000
    file = 'box_with_hole.stp'
    transformed_file =read_step_and_transform(file)

    z_max, x_max, y_max, x_min, y_min = get_max_z_from_shape(transformed_file)

    XBOUNDS, YBOUNDS = calculate_valid_range(x_max,y_max,x_min,y_min,10*(200**(.67)))

    floor = create_centered_floor(XBOUNDS,YBOUNDS)
    #display.DisplayShape(floor,update = False,color= Quantity_NOC_GREEN)

    all_shapes = extract_shapes(transformed_file,shell=False, compound=False)

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
        shape_info[f"{i}"] = {"coords":(x,y,z), "shape":shape, "name":None, "shapehandle":shape_handle, "count":0}

    total_collision_info = []
    #print(shape_info)
    display.register_select_callback(on_shape_clicked)
    add_menu("Tools")
    add_menu("Run Sim")
    add_function_to_menu("Tools", enable_tagging)
    add_function_to_menu("Tools", enable_view_mode)
    add_function_to_menu("Tools", enable_cutting_mode)
    add_function_to_menu("Tools", enable_grouping_mode)
    simulation_callback = make_simulation_callback(XBOUNDS, YBOUNDS, z_max, samples)
    add_function_to_menu("Run Sim", simulation_callback)

    print(shape_info)
    start_display()


if __name__=="__main__":
    start = time.time()
    main()
    print("Done in", time.time() - start, "seconds")