import unreal
import time 
import re

def vec2str(vec):
    return '['+ ', '.join([str(w) for w in [vec.x, vec.y, vec.z]])+']'
def plane2str(plane):
    return '['+', '.join([str(w) for w in [plane.x, plane.y, plane.z, plane.w]])+']'
def mat2str(mat):
    return '['+', '.join([plane2str(w) for w in [mat.x_plane, mat.y_plane, mat.z_plane, mat.w_plane]])+']'

actors_of_interest = []
actor_list = unreal.EditorLevelLibrary.get_all_level_actors()
unreal.log("{} actors present in the current level".format(len(actor_list)))
object_types_to_consider = ['barrel', 'tableround', 'chair', 'crate', 'tire', 'cardboardbox', 'rock','couch','pallet']
# customise this list based on your environment
# use for modular forest env
# object_types_to_consider_or_ignore_for_median = [
#     (['barrel[\w]+_hill1'], False),
#     (['barrel[\w]+_hill2'], False),
#     (['barrel[\w]+_hill3'], False)
# ]
# use for modular buildings env
object_types_to_consider_or_ignore_for_median = [
    (['building1'], False),
    (['groundfloor'], False),
    (['building2'], False),
    (['building3'], False),
    (['building4'], False),
    (['building5'], False),
    (['building6'], False),
    (['ground2'], False),
] #true means we ignore any actors which have these in their name, false means we only consider actors which have these in their name
centers = [[0,0,0] for _ in range(len(object_types_to_consider_or_ignore_for_median))]
counts = [0] * len(object_types_to_consider_or_ignore_for_median)
actors_considered = [[] for _ in range(len(object_types_to_consider_or_ignore_for_median))]

with open('C:/Users/Dronelab/Downloads/llnl/airsim_data_collection/py_ue4_script_output2.txt','w') as f1:
    # f1.write("{} actors present in the current level".format(len(actor_list)))
    locs = [0,0,0]
    cnt = 0
    start_loc = None
    start_loc_actor = None
    for actor in actor_list:
        # f1.write(actor.get_path_name())
        # f1.write(', ')
        # f1.write(mat2str(actor.get_actor_transform().to_matrix()))
        # f1.write(', ')
        # f1.write(vec2str(actor.get_actor_location()))
        # f1.write('\n')
        # f1.write(', '.join([t for t in actor.tags]))
        aname = str(actor.get_path_name()).lower().split('.')[-1]

        if any([objs in aname for objs in object_types_to_consider]):
            actor_name = actor.get_path_name().strip().split('.')[-1]
            actors_of_interest.append(actor_name)
            for median_idx, (taglist, ignore_flag) in enumerate(object_types_to_consider_or_ignore_for_median):
                unreal.log("{}: {}, {}\n".format(median_idx, taglist, ignore_flag))
                if ignore_flag:
                    if not any([len(re.findall(objs, aname))>0 for objs in taglist]):
                        loc = actor.get_actor_location()
                        for i, w in enumerate([loc.x, loc.y, loc.z]):
                            centers[median_idx][i] += w
                        counts[median_idx] += 1
                        actors_considered[median_idx].append(aname)
                else:
                    if any([len(re.findall(objs, aname))>0 for objs in taglist]):
                        loc = actor.get_actor_location()
                        for i, w in enumerate([loc.x, loc.y, loc.z]):
                            centers[median_idx][i] += w
                        counts[median_idx] += 1
                        actors_considered[median_idx].append(aname)

        if 'playerstart' in aname:
            if start_loc is None:
                start_loc = vec2str(actor.get_actor_location())
                start_loc_actor = aname
    if start_loc is not None:
        f1.write('playerstart')
        f1.write(', ')
        f1.write(start_loc)
        f1.write('\n')
    for center, count in zip(centers, counts):
        if count > 0:
            locstring = 'median_location, ' + ', '.join([str(w/count) for w in center]) + '\n'
            f1.write(locstring)
    for actors in actors_of_interest:
        f1.write(actors.strip() + '\n')

    f1.close()
    # time.sleep(10)
    for median_idx, actor_list_considered in enumerate(actors_considered):
        unreal.log("Orbit {}, actors considered: {}\n".format(median_idx, actor_list_considered))
# unreal.log("Starting new function")
# def new_func():
#     import subprocess
#     py_exe = "C:/Users/prana/AppData/Local/Microsoft/WindowsApps/PythonSoftwareFoundation.Python.3.8_qbz5n2kfra8p0/python.exe"
#     subprocess.call([py_exe, "C:/Users/prana/Downloads/UCSD/dronelab/LLNL/search_sample.py"], shell=True)

# import threading
# t = threading.Thread(target=new_func,name='New func',args=())
# t.daemon = True
# t.start()
# unreal.log("Started new function")