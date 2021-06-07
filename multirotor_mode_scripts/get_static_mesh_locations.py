import unreal
import time 

def vec2str(vec):
    return '['+ ', '.join([str(w) for w in [vec.x, vec.y, vec.z]])+']'
def plane2str(plane):
    return '['+', '.join([str(w) for w in [plane.x, plane.y, plane.z, plane.w]])+']'
def mat2str(mat):
    return '['+', '.join([plane2str(w) for w in [mat.x_plane, mat.y_plane, mat.z_plane, mat.w_plane]])+']'

actors_of_interest = []
actor_list = unreal.EditorLevelLibrary.get_all_level_actors()
unreal.log("{} actors present in the current level".format(len(actor_list)))
object_types_to_consider = ['barrel', 'tableround', 'chair', 'crate', 'tire', 'box']
object_types_to_ignore_for_median = ['closed2', 'crate', 'box', 'tableround', 'chair', 'crate', 'tire', 'box']
    
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
        aname = str(actor.get_path_name()).lower()

        if any([objs in aname for objs in object_types_to_consider]):
            actor_name = actor.get_path_name().strip().split('.')[-1]
            actors_of_interest.append(actor_name)
            if not any([objs in aname for objs in object_types_to_ignore_for_median]):
                loc = actor.get_actor_location()
                for i, w in enumerate([loc.x, loc.y, loc.z]):
                    locs[i] += w
                cnt += 1
        
        if 'playerstart' in aname:
            if start_loc is None:
                start_loc = vec2str(actor.get_actor_location())
                start_loc_actor = aname
    if start_loc is not None:
        f1.write('playerstart')
        f1.write(', ')
        f1.write(start_loc)
        f1.write('\n')
    if cnt > 0:
        locstring = 'barrel, ' + ', '.join([str(w/cnt) for w in locs]) + '\n'
        f1.write(locstring)
    for actors in actors_of_interest:
        f1.write(actors.strip() + '\n')

    f1.close()
    # time.sleep(10)

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