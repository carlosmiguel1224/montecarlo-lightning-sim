from montecarlohelper import *
from util import *
from findingmaxz_readingfile import *
import time
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Common
from OCC.Core.AIS import AIS_Shape

tagging_mode = False
view_mode = False
cutting_mode = False
shape_info = {}
display, start_display, add_menu, add_function_to_menu = init_display()




def on_shape_clicked(clicked_shape, *args):
    global tagging_mode, view_mode, shape_info, cutting_mode

    if not (tagging_mode or view_mode or cutting_mode):
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
                x, y , z = data.get("coords")
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
                if plane_for_cut == "x":
                    x = 1
                elif plane_for_cut == "y":
                    y = 1
                elif plane_for_cut == "z":
                    z = 1
                x_height = -((xmin + xmax)/2)
                y_height = -((ymin + ymax)/2)
                z_height = -((zmin + zmax)/2)
                plane = gp_Pln(gp_Pnt(x_height, y_height, z_height), gp_Dir(x, y, z))  # Z-direction plane
                face = BRepBuilderAPI_MakeFace(plane, -1000, 1000, -1000, 1000).Shape()
                face_handle = display.DisplayShape(face, update=True)[0]
                print(face_handle)
                result = ''
                while result != "cut":
                    result = input("type 'cut' to confirm ")
                    while True:
                        if x == 1:
                            change  = float(input("enter how much youd like to increase or decrease x coordinate for cut (enter negative number if decreasing)"))
                            x_height += change
                            break
                        elif y == 1:
                            change = float(input("put y coordinate for cut"))
                            y_height += change
                            break 
                        elif z == 1:
                            change = float(input("put z coordinate for cut"))
                            z_height += change
                            break
                    display.Context.Remove(face_handle, True)
                    plane = gp_Pln(gp_Pnt(x_height, y_height, z_height), gp_Dir(x, y, z)) 
                    face = BRepBuilderAPI_MakeFace(plane, -1000, 1000, -1000, 1000).Shape()
                    face_handle = display.DisplayShape(face ,update=True)[0]

                cutting_mode = False
                return

    print("Shape not found in shape_info.")

# --- Menu functions ---
def enable_tagging():
    global tagging_mode, view_mode, cutting_mode
    tagging_mode = True
    view_mode = False
    print("🟢 Tagging mode enabled — click a shape to name it.")

def enable_view_mode():
    global tagging_mode, view_mode, cutting_mode
    tagging_mode = False
    view_mode = True
    print("🔵 View mode enabled — click a shape to see its name.")

def enable_cutting_mode():
    global cutting_mode, tagging_mode, view_mode
    cutting_mode = True
    tagging_mode = view_mode = False


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
    file = 'box_with_hole.stp'
    transformed_file =read_step_and_transform(file)

    z_max, x_max, y_max, x_min, y_min = get_max_z_from_shape(transformed_file)

    XBOUNDS, YBOUNDS = calculate_valid_range(x_max,y_max,x_min,y_min,10*(200**(.67)))
    samples = 1

    floor = create_centered_floor(XBOUNDS,YBOUNDS)
    display.DisplayShape(floor,update = False,color= Quantity_NOC_GREEN)

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
        shape_info[f"{i}"] = {"coords":(x,y,z), "shape":shape, "name":None}
        display.DisplayShape(shape, update = False, transparency=.9)

    total_collision_info = []
    #print(shape_info)
    display.register_select_callback(on_shape_clicked)
    add_menu("Tools")
    add_function_to_menu("Tools", enable_tagging)
    add_function_to_menu("Tools", enable_view_mode)
    add_function_to_menu("Tools", enable_cutting_mode)

    start_display()


if __name__=="__main__":
    start = time.time()
    main()
    print("Done in", time.time() - start, "seconds")