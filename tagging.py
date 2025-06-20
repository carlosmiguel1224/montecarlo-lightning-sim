from readreceivedrandomfile import *

tagged_shapes = {}
tagging_mode = False

def on_shape_clicked(shape, *args):
    global tagging_mode
    if tagging_mode:
        name = input("Enter name for selected shape: ")
        tagged_shapes[f"{shape}"] = name
        print(f"Tagged shape as '{name}'")
        tagging_mode = False  # Optional: disable after one tag

def enable_tagging():
    global tagging_mode
    tagging_mode = True
    print("Tagging mode enabled — click on a shape")

def auto_assign_ids(all_shapes):
    id_counter = 1
    for shape in all_shapes:
        if shape not in tagged_shapes:
            print(f"Auto-tagging shape: Shape_{id_counter}")
            tagged_shapes[shape] = f"Shape_{id_counter}"
            id_counter += 1

def read_shapes_from_step(step_file):
    reader = STEPControl_Reader()
    if reader.ReadFile(step_file) != IFSelect_RetDone:
        raise Exception("Error reading STEP")
    reader.TransferRoots()
    shape = reader.OneShape()
    return shape

def main():
    step_path = "box_with_hole.stp"
    shape = read_shapes_from_step(step_path)

    display, start_display, add_menu, add_function_to_menu = init_display()

    display.DisplayShape(shape, update=True)
    display.register_select_callback(on_shape_clicked)

    add_menu("Tools")
    add_function_to_menu("Tools", enable_tagging)

    start_display()

    # After GUI closes
    auto_assign_ids(display.DisplayedShapes())
    print("Final shape tagging:")
    for s, name in tagged_shapes.items():
        print(name)



if __name__ == "__main__":

    main()