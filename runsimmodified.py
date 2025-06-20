from montecarlohelper import *
from findingmaxz_readingfile import *
from util import *
from OCC.Core.BRep import BRep_Builder
from OCC.Core.TopoDS import TopoDS_Compound
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeSphere

def run_sim_modified(samples,z_max,shape_info, all_shapes, XBOUNDS, YBOUNDS, meters=True, area_for_floor=None, pos_min=4,neg_min=4,pos_max=400,neg_max=200,curtoradpos=None,curtoradneg=None):
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
    object_bboxes = [(shape, get_bbox(shape)) for shape in all_shapes]
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
        builder.Add(befvertcompound, sphere)
        #display.DisplayShape(sphere, update= False, color = Quantity_NOC_YELLOW,transparency=.9)

        total_traveled = 0

        sphere_bbox = get_sphere_bbox(point, radius)
        candidate_shapes = [shape for shape, bbox in object_bboxes if not sphere_bbox.IsOut(bbox)]
        
        while True:
            
            index ,distance, groundpoint = modified_tolerance_abs_min_dist(vertex, candidate_shapes)
            if  -.25 <= (distance-radius) <= .25: #distance <= radius + .1
                break

            moving = smart_move(distance,radius, factor=.99, min_step=.001)

            z -= moving
            #print(z)

            total_traveled += moving
            vertex = BRepBuilderAPI_MakeVertex(gp_Pnt(point.X(),point.Y(), z)).Vertex()
            
        ground_vert = BRepBuilderAPI_MakeVertex(gp_Pnt(groundpoint.X(),groundpoint.Y(), groundpoint.Z())).Vertex()
        #ground_sphere = BRepPrimAPI_MakeSphere(gp_Pnt(groundpoint.X(),groundpoint.Y(), groundpoint.Z()), radius).Shape()
        builder.Add(vertcompound, ground_vert)
        #spherepoint = gp_Pnt(point.X(),point.Y(), z)

        #for sphere demonstration
        #sphere = BRepPrimAPI_MakeSphere(spherepoint,radius).Shape()
        #display.DisplayShape(sphere, update= False, color = Quantity_NOC_RED,transparency=.9)
        shape_info[f"{index}"]["count"] += 1
        total_collision_info.append({"center_on_contact": f"{point.X()},{point.Y()},{z}", 
        "surface_on_contact":f"{groundpoint.X()},{groundpoint.Y()},{groundpoint.Z()}", "peakcurrent":current,
        "strike":strike,"structurestruck": shape_info[f"{index}"].get("name", f"shapeid:{index}"), "count":shape_info[f"{index}"]["count"]})

    #print(total_collision_info[:20])


    for i in range(len(all_shapes)):
        #print(shape_info[f"{i}"]["count"])
        shape_info[f"{i}"]["collectarea"] = collection_area(samples,XBOUNDS,YBOUNDS, shape_info[f"{i}"]["count"])
        shape_info[f"{i}"]["percentofstrikes"] = (shape_info[f"{i}"]["count"]/samples)
    
    #print(shape_info)

    all_shapes.append(vertcompound)

    return (shape_info, total_collision_info, samples, vertcompound, befvertcompound)