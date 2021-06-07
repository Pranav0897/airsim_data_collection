import airsim

import drone_orbit
import os
import time
import math
from PIL import Image
import re
import argparse
import random
import csv

def get_ue_coordinates_and_mesh_ids(filename):
    d = {}
    try:
        cx, cy, cz = 0,0,0
        px, py, pz = 0,0,0
        
        data = open(filename, 'r').read().strip().split('\n')
        if len(data) < 1:
            print("Empty file!")
            return None
        # elif len(data) < 2:
        #     if not ('start' in data.lower() or 'barrel' in data.lower()):
        #         print("Invalid stuff in file!")
        #         return None
        #     else:
        #         if 'start' in data.lower():
        #             # no barrels in the scene?
        #             print("No barrels in the list of actors in the scene, it seems")
        #             return None 
        #         else:
        #             # there are barrels, but a player start location was not specified.
        #             # therefore, assume that we start from 0,0,0
        #             coords = [float(p) for p in re.findall(r'[\d.-]+', data[0])]
        #             assert len(coords)==3, print("Found this as the coordinates: {}".format(data))
        #             px,py,pz = coords[:3]
        # else:
        # assert all([(('start' in d.lower()) or ('barrel' in d.lower())) for d in data]), print("Invalid data: {}".format(data))
        coords = [[float(p) for p in re.findall(r'[\d.-]+', d)] for d in data[:2]]
        if 'start' in data[0].lower():
            cx, cy, cz = coords[0]
            px, py, pz = coords[1]
        else:
            cx, cy, cz = coords[1]
            px, py, pz = coords[0]
        
        mesh_ids = [d.strip() for d in data[2:]]
        # x,y,z = [float(f) for f in f1.read().strip().split(',')]
        # f1.close()
        print([px,py,pz])
        print([cx,cy,cz])
        d['x'] = (px-cx)/100
        d['y'] = (py-cy)/100
        d['z'] = -(pz-cz)/100
        return d, mesh_ids
    except Exception as e:
        print(e)
        return None

def OrbitAnimal(cx, cy, radius, speed, altitude, camera_angle, animal, image_dir="./drone_images_testing_ue4_scripts/", image_stamp_offset = 0, mesh_colors = {}):
    """
    @param cx: The x position of our orbit starting location
    @param cy: The x position of our orbit starting location
    @param radius: The radius of the orbit circle
    @param speed: The speed the drone should more, it's hard to take photos when flying fast
    @param altitude: The altidude we want to fly at, dont fly too high!
    @param camera_angle: The angle of the camera
    @param animal: The name of the animal, used to prefix the photos
    """

    x = cx - radius
    y = cy

    # set camera angle
    client.simSetCameraPose(0, airsim.to_quaternion(
        camera_angle * math.pi / 180, 0, 0))  # radians

    # move the drone to the requested location
    print("moving to position...")
    
    client.moveToPositionAsync(
        x, y, z, 5, 60, drivetrain=airsim.DrivetrainType.MaxDegreeOfFreedom, yaw_mode=airsim.YawMode(False, 0)).join()
    pos = client.getMultirotorState().kinematics_estimated.position

    dx = x - pos.x_val
    dy = y - pos.y_val
    yaw = airsim.to_eularian_angles(
        client.getMultirotorState().kinematics_estimated.orientation)[2]

    # keep the drone on target, it's windy out there!
    print("correcting position and yaw...")
    while abs(dx) > 1 or abs(dy) > 1 or abs(yaw) > 0.1:
        client.moveToPositionAsync(
            x, y, z, 0.25, 60, drivetrain=airsim.DrivetrainType.MaxDegreeOfFreedom, yaw_mode=airsim.YawMode(False, 0)).join()
        pos = client.getMultirotorState().kinematics_estimated.position
        dx = x - pos.x_val
        dy = y - pos.y_val
        yaw = airsim.to_eularian_angles(
            client.getMultirotorState().kinematics_estimated.orientation)[2]
        print("yaw is {}".format(yaw))

    print("location is off by {},{}".format(dx, dy))

    o = airsim.to_eularian_angles(
        client.getMultirotorState().kinematics_estimated.orientation)
    print("yaw is {}".format(o[2]))

    # let's orbit around the animal and take some photos
    nav = drone_orbit.OrbitNavigator(photo_prefix=animal, radius=radius, altitude=altitude, speed=speed, iterations=1, center=[
                                     cx - pos.x_val, cy - pos.y_val], snapshots=60, image_dir=image_dir, filename_offset = image_stamp_offset, mesh_colors = mesh_colors)
    offset = nav.start()
    return offset

def land():
    print("landing...")
    client.landAsync().join()

    print("disarming.")
    client.armDisarm(False)

    client.reset()
    client.enableApiControl(False)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Collect data using airsim')
    parser.add_argument('--input_filename', type=str, required=True, help='Path to filename generated by the Unreal script')
    parser.add_argument('--output_dir', type=str, default = 'beach_barrel',help='Directory to store images in')
    args = parser.parse_args()
    tic = time.time()
    # Conect with the airsim server
    client = airsim.MultirotorClient()
    client.confirmConnection()
    client.enableApiControl(True)
    client.armDisarm(True)
    cur_location = client.getMultirotorState()
    print(cur_location)
    # Check State and takeoff if required
    landed = client.getMultirotorState().landed_state
    client.takeoffAsync().join()

    if landed == airsim.LandedState.Landed:
        print("taking off...")
        # pos = client.getMultirotorState().kinematics_estimated.position
        # z = pos.z_val - 1
        client.takeoffAsync().join()
    else:
        print("already flying...")
        # client.hover()
        # pos = client.getMultirotorState().kinematics_estimated.position
        # z = pos.z_val

    # actor_loc  = unreal.EditorLevelLibrary.get_all_level_actors()[-1].get_actor_transform()
    # actor_location = actor_loc.translation
    # actor_location = {'x':-23.70000000, 'y': -55.80000000, 'z': -30.10000000}
    actor_location, mesh_ids = get_ue_coordinates_and_mesh_ids(args.input_filename)
    z = actor_location['z'] - 8

    # Start the navigation task

    client.simEnableWeather(True)
    weather_patterns = [None, [airsim.WeatherParameter.Fog],[airsim.WeatherParameter.MapleLeaf, airsim.WeatherParameter.RoadLeaf],
            [airsim.WeatherParameter.Rain, airsim.WeatherParameter.Roadwetness], [airsim.WeatherParameter.Snow, airsim.WeatherParameter.RoadSnow]]
    
    scene_objects = client.simListSceneObjects()
    print("number of objects in scene: {}".format(len(scene_objects)))

    # mesh_colors = list(random.sample(range(1,255), len(mesh_ids)))
    set_count = 0
    success = client.simSetSegmentationObjectID(".*", 255, True)
    extra_meshes = ["[\w]*[sS]ky[\w]*","[\w]*[rR]oad[\w]*", "[\w]*[bB]uilding[\w]*", "[\w]*[rR]oof[\w]*", "[\w]*[mM]ountain[\w]*", "[\w]*[tT]ree[\w]*"]
    all_mesh_colors = list(random.sample(range(1,255), len(mesh_ids+extra_meshes)))
    mesh_colors = all_mesh_colors[:len(mesh_ids)]
    bg_colors = all_mesh_colors[len(mesh_ids):]
    regex_flag = [False]*len(mesh_ids) + [True]*len(extra_meshes)
    presaved_values = {'SM_Barrel_01_Closed_2': 177, 'SM_Barrel_02_Opened_5': 150, 'SM_Barrel_04_Opened_8': 60, 'SM_Barrel_05_Opened_11': 107,
                         '[\w]*[sS]ky[\w]*': 35, '[\w]*[rR]oad[\w]*': 77, '[\w]*[bB]uilding[\w]*': 125, '[\w]*[rR]oof[\w]*': 47}
    # {'SM_Barrel_01_Closed_2': 118, 'SM_Barrel_02_Opened_5': 234, 'SM_Barrel_04_Opened_8': 85, 
                        # 'SM_Barrel_05_Opened_11': 114, '[\w]*[sS]ky[\w]*': 224, '[\w]*[rR]oad[\w]*': 137, '[\w]*[bB]uilding[\w]*': 21, '[\w]*[rR]oof[\w]*': 10}
    # mesh_colors = [presaved_values.get(n, None) if presaved_values.get(n, None) is not None else all_mesh_colors[idx] for idx, n in enumerate(mesh_ids)]
    all_new_mesh_colors = []
    for idx, n in enumerate(mesh_ids+extra_meshes):
        if presaved_values.get(n, None) is not None:
            all_new_mesh_colors.append(presaved_values[n])
        else:
            newcolor = all_mesh_colors[idx]
            while newcolor in set(all_new_mesh_colors):
                newcolor += 1
                newcolor = newcolor % 256
            all_new_mesh_colors.append(newcolor)
    
    all_mesh_colors = all_new_mesh_colors
    mesh_colors = all_new_mesh_colors[:len(mesh_ids)]

    # all_mesh_colors = [presaved_values[n] if presaved_values.get(n, None) is not None else all_mesh_colors[idx] for idx, n in enumerate(mesh_ids+extra_meshes)]

    print("Meshes of interest, and their colors: ", list(zip(mesh_ids+extra_meshes, all_mesh_colors)))
    for meshname, color, rf in zip(mesh_ids+extra_meshes, all_mesh_colors, regex_flag):
        success = client.simSetSegmentationObjectID(meshname, color, rf)
        if success:
            set_count += 1
    print("Was able to set custom colors for {} out of {} objects".format(set_count, len(mesh_ids)))
    mesh_color_dict = dict(zip(mesh_ids, mesh_colors))
    id_color_dict = {}
    with open('color_id_scheme_new.csv', 'r') as f1:
        data = f1.read().strip().split('\n')
        for line in data:
            if line.strip() == '':
                continue
            id, r, g, b = [int(v) for v in re.findall(r'[\d]+', line)[:4]]
            id_color_dict[id] = [r,g,b]
    id_set = set(id_color_dict.keys())
    assert all([v in id_set for _, v in mesh_color_dict.items()]), print(id_set, mesh_color_dict.items())
    mesh_id_color_dict = {k:(v, id_color_dict[v]) for k, v in mesh_color_dict.items()}

    offset = 0
    delta_z = [-1,-0.5,0, 0.5,1]
    delta_r = [15,10,5,0,-5]

    client.moveToPositionAsync(0, 0, z, 5, 60, drivetrain=airsim.DrivetrainType.MaxDegreeOfFreedom, yaw_mode=airsim.YawMode(False, 0)).join()

    for idx in range(len(weather_patterns)):
        if idx > 1:
            for ptrn in weather_patterns[idx-1]:
                client.simSetWeatherParameter(ptrn, 0)
        if idx>0:
            for ptrn in weather_patterns[idx]:
                client.simSetWeatherParameter(ptrn, 0.9)

        if idx != 1:
            for hours in range(8,21,10):
                random.shuffle(delta_z)
                random.shuffle(delta_r)
                for dz, dr in zip(delta_z, delta_r):
                    client.simSetTimeOfDay(True, start_datetime ="2018-02-12 {0:02d}:00:00".format(hours), is_start_datetime_dst=True,celestial_clock_speed=1, update_interval_secs=1)
                    offset = OrbitAnimal(actor_location['x'], actor_location['y'], 60+dr, 1.6,5+dz, -30, "", args.output_dir, offset, mesh_id_color_dict) # "tod_{}_weather_{}".format(hours, idx)
        else:
            random.shuffle(delta_z)
            random.shuffle(delta_r)
            for dz, dr in zip(delta_r, delta_r):
                client.simSetTimeOfDay(True, start_datetime ="2018-02-12 08:00:00", is_start_datetime_dst=True,celestial_clock_speed=1, update_interval_secs=1)
                offset = OrbitAnimal(actor_location['x'], actor_location['y'], 60+dr, 1.6,5+dz, -30, "", args.output_dir, offset, mesh_id_color_dict) # "tod_{}_weather_{}".format(hours, idx)
        
    land()

    print("Image capture complete...")
    toc = time.time()
    print("Time taken to generate this dataset: {}".format(toc-tic))
