from OCC.Core.gp import gp_Pnt, gp_Vec, gp_Ax2, gp_Dir, gp_Trsf, gp_Ax3
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakePrism, BRepPrimAPI_MakeSphere
from OCC.Core.BRepExtrema import BRepExtrema_DistShapeShape
from OCC.Core.Geom import Geom_Plane
from OCC.Core.TopoDS import topods, TopoDS_Shape, topods_Face, TopoDS_Compound
from OCC.Core.GProp import GProp_GProps
from OCC.Core.BRepGProp import BRepGProp_Face
from OCC.Core.BRep import BRep_Tool
from OCC.Display.SimpleGui import init_display
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform, BRepBuilderAPI_MakeVertex
from OCC.Core.Quantity import (
    Quantity_NOC_RED,
    Quantity_NOC_GREEN,
    Quantity_NOC_BLUE1,
    Quantity_NOC_YELLOW,
    Quantity_NOC_BLACK,
    Quantity_NOC_WHITE,
    Quantity_Color
)
from OCC.Core.BRepBuilderAPI import (
    BRepBuilderAPI_MakeEdge,
    BRepBuilderAPI_MakeWire,
    BRepBuilderAPI_MakeFace,
)
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib_Add
from OCC.Core.AIS import AIS_TextLabel
from OCC.Core.TCollection import TCollection_ExtendedString
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCC.Core.BRep import BRep_Tool, BRep_Builder
from OCC.Core.AIS import AIS_Point
from OCC.Core.Geom import Geom_CartesianPoint
import time
from util import *
from montecarlohelper import *
from findingmaxz_readingfile import *
import uuid
import os
from OCC.Core.IFSelect import IFSelect_RetDone


def run_sim(cleaned_step_file, samples, meters=True, area_for_floor=None, solids=True, shells=True, compounds=True, pos_min=4,neg_min=4,pos_max=400,neg_max=200,curtoradpos=None,curtoradneg=None):
    #display, start_display, add_menu, add_function_to_menu = init_display()
    samples = samples
    delta = 50


    shape_info ={}
    all_shapes = []
    total_collision_info = []


    builder = BRep_Builder()
    vertcompound = TopoDS_Compound()
    builder.MakeCompound(vertcompound)


    z_max, x_max, y_max, x_min, y_min = get_max_z_from_shape(read_step_and_transform(cleaned_step_file))

    XBOUNDS, YBOUNDS = calculate_valid_range(x_max,y_max,x_min,y_min,10*(200**(.67)))

    all_shapes = extract_shapes(read_step_and_transform(cleaned_step_file),solids=solids,shells=shells, compounds=compounds)

    #for i in range(len(all_shapes)):
        #shape = all_shapes[i]
        #z_max,x_max,y_max,x_min,y_min = get_max_z_from_shape(shape)
        #x = -(-x_min+x_max)/2
        #y = -(-y_min+y_max)/2
        #z = z_max + 10
        #message_point = gp_Pnt(x,y,z)
        #display.DisplayMessage(message_point, f"id for shape {i}")
        #shape_info[f"{i}"] = {"coords":(x,y,z), "shape":shape, "count":0}
        #display.DisplayShape(shape, update = False, transparency=.9)

    print(shape_info)


    XBOUNDS, YBOUNDS = calculate_valid_range(x_max, y_max, x_min, y_min,10*(200**(.67)) + 10 )


    floor = create_centered_floor(XBOUNDS,YBOUNDS)
    #display.DisplayShape(floor, update = False,color= Quantity_NOC_GREEN)


    all_shapes.append(floor)
    

    peak_currents = bulk_log_distribution(bulk_positive_negative_strikes(samples),pos_max=pos_max, neg_max=neg_max, pos_min=pos_min, neg_min=neg_min)
    radii = bulk_sphere_radii(peak_currents)
    sphere_points = points_with_radii(XBOUNDS,YBOUNDS, radii ,samples, z_max + delta)
    #print("done with points")

    for i in range(len(all_shapes)):
        shape = all_shapes[i]
        z_max,x_max,y_max,x_min,y_min = get_max_z_from_shape(shape)
        x = -(-x_min+x_max)/2
        y = -(-y_min+y_max)/2
        z = z_max + 10
        #message_point = gp_Pnt(x,y,z)
        #display.DisplayMessage(message_point, f"id for shape {i}")
        shape_info[f"{i}"] = {"coords":(x,y,z), "shape":shape, "count": 0}
        #display.DisplayShape(shape, update = False, transparency=.9)

    #counter = 0

    for i in range(samples):
  
        #counter += 1
        #print(counter)

        point = sphere_points[i]
        x = point.X()
        y = point.Y()
        z = point.Z()

        radius = radii[i]
        current = peak_currents[0][i]
        strike = peak_currents[1][i]

        vertex = BRepBuilderAPI_MakeVertex(point).Vertex()


        #spherepoint = BRep_Tool.Pnt(vertex)
        #sphere = BRepPrimAPI_MakeSphere(spherepoint,radius).Shape()
        #display.DisplayShape(sphere, update= False, color = Quantity_NOC_YELLOW,transparency=.9)

        #distance = abs_min_dist(vertex,all_shapes)[0]
        total_traveled = 0
        #while distance>=(radius + .1):
        #print(radius)
        while True:
            
            index ,distance, groundpoint = modified_tied_abs_min_dist(vertex, all_shapes)
            if  -.01 <= (distance-radius) <= .01: #distance <= radius + .1
                break
            #distance,_,groundpoint = abs_min_dist(vertex, all_shapes)
            moving = smart_move(distance,radius, factor=.99, min_step=.001)

            z -= moving

            total_traveled += moving
            vertex = BRepBuilderAPI_MakeVertex(gp_Pnt(point.X(),point.Y(), z)).Vertex()
            #print(f"This is radius{radius}")
            #print(f"This is z{z}")

        builder.Add(vertcompound, vertex)
        #spherepoint = gp_Pnt(point.X(),point.Y(), z)

        #for sphere demonstration
        #sphere = BRepPrimAPI_MakeSphere(spherepoint,radius).Shape()
        #display.DisplayShape(sphere, update= False, color = Quantity_NOC_RED,transparency=.9)
        shape_info[f"{index}"]["count"] += 1

        total_collision_info.append({"center_on_contact": f"{point.X()},{point.Y()},{z}", 
        "surface_on_contact":f"{groundpoint.X()},{groundpoint.Y()},{groundpoint.Z()}", "peakcurrent":current,
        "strike":strike,"structurestruck": shape_info[f"{index}"]["coords"], "count":shape_info[f"{index}"]["count"]})

    #print(total_collision_info[:20])
    #start_display()


    for i in range(len(all_shapes)):
        #print(shape_info[f"{i}"]["count"])
        shape_info[f"{i}"]["collectarea"] = collection_area(samples,XBOUNDS,YBOUNDS, shape_info[f"{i}"]["count"])
        shape_info[f"{i}"]["percentofstrikes"] = (shape_info[f"{i}"]["count"]/samples)
    
    print(shape_info)

    all_shapes.append(vertcompound)
    step_writer = STEPControl_Writer()
    for shape in all_shapes:
        step_writer.Transfer(shape, STEPControl_AsIs)
    filename = f"{uuid.uuid4()}.stp"
    filepath = os.path.join(settings.MEDIA_ROOT, filename)
    status = step_writer.Write(filepath)
    return (shape_info, total_collision_info, samples, filename)



#file = 'box_with_hole.stp'
#run_sim(file, 1000)




