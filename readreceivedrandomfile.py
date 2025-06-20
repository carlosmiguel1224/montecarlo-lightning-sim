from montecarlohelper import *
from util import *
from findingmaxz_readingfile import *
import time




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
    file = 'Jib crane ASSY.stp'
    transformed_file =read_step_and_transform(file)
    display, start_display, add_menu, add_function_to_menu = init_display()

    z_max, x_max, y_max, x_min, y_min = get_max_z_from_shape(transformed_file)

    XBOUNDS, YBOUNDS = calculate_valid_range(x_max,y_max,x_min,y_min,10*(200**(.67)))
    samples = 1
    shape_info = {}

    floor = create_centered_floor(XBOUNDS,YBOUNDS)
    display.DisplayShape(floor,update = False,color= Quantity_NOC_GREEN)

    all_shapes = extract_shapes(transformed_file,shell=False, compound=False)

    print(len(all_shapes))
    for i in range(len(all_shapes)):
        shape = all_shapes[i]
        z_max,x_max,y_max,x_min,y_min = get_max_z_from_shape(shape)
        x = -(-x_min+x_max)/2
        y = -(-y_min+y_max)/2
        z = z_max + 10
        message_point = gp_Pnt(x,y,z)
        display.DisplayMessage(message_point, f"id for shape {i}")
        shape_info[f"{i}"] = {"coords":(x,y,z), "shape":shape}
        display.DisplayShape(shape, update = False, transparency=.9)

    total_collision_info = []
    #print(shape_info)
    start_display()


if __name__=="__main__":
    start = time.time()
    main()
    print("Done in", time.time() - start, "seconds")