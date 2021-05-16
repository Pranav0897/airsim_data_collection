import airsim

import drone_orbit
import os
import time
import math
from PIL import Image
import re
import argparse

def get_ue_coordinates(filename):
    d = {}
    try:
        cx, cy, cz = 0,0,0
        px, py, pz = 0,0,0
        
        data = open(filename, 'r').read().strip().split('\n')
        if len(data) < 1:
            print("Empty file!")
            return None
        elif len(data)>2:
            print("File should only have 2 lines: start location, and mean of locations of barrels")
            return None
        elif len(data) < 2:
            if not ('start' in data.lower() or 'barrel' in data.lower()):
                print("Invalid stuff in file!")
                return None
            else:
                if 'start' in data.lower():
                    # no barrels in the scene?
                    print("No barrels in the list of actors in the scene, it seems")
                    return None 
                else:
                    # there are barrels, but a player start location was not specified.
                    # therefore, assume that we start from 0,0,0
                    coords = [float(p) for p in re.findall(r'[\d.-]+', data[0])]
                    assert len(coords)==3, print("Found this as the coordinates: {}".format(data))
                    px,py,pz = coords[:3]
        else:
            assert all([(('start' in d.lower()) or ('barrel' in d.lower())) for d in data]), print("Invalid data: {}".format(data))
            coords = [[float(p) for p in re.findall(r'[\d.-]+', d)] for d in data]
            if 'start' in data[0].lower():
                cx, cy, cz = coords[0]
                px, py, pz = coords[1]
            else:
                cx, cy, cz = coords[1]
                px, py, pz = coords[0]
        
        # x,y,z = [float(f) for f in f1.read().strip().split(',')]
        # f1.close()
        print([px,py,pz])
        print([cx,cy,cz])
        d['x'] = (px-cx)/100
        d['y'] = (py-cy)/100
        d['z'] = -(pz-cz)/100
        return d
    except Exception as e:
        print(e)
        return None

def OrbitAnimal(cx, cy, radius, speed, altitude, camera_angle, animal, image_dir="./drone_images_testing_ue4_scripts/"):
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
    client.simSetCameraOrientation(0, airsim.to_quaternion(
        camera_angle * math.pi / 180, 0, 0))  # radians

    # move the drone to the requested location
    print("moving to position...")
    
    client.moveToPositionAsync(
        x, y, z, 1, 60, drivetrain=airsim.DrivetrainType.MaxDegreeOfFreedom, yaw_mode=airsim.YawMode(False, 0)).join()
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
                                     cx - pos.x_val, cy - pos.y_val], snapshots=120, image_dir=image_dir)
    nav.start()


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
    actor_location = get_ue_coordinates(args.input_filename)
    z = actor_location['z'] - 8

    # Start the navigation task

    client.simEnableWeather(True)
    weather_patterns = [None, [airsim.WeatherParameter.Fog],[airsim.WeatherParameter.MapleLeaf, airsim.WeatherParameter.RoadLeaf],[airsim.WeatherParameter.Rain, airsim.WeatherParameter.Roadwetness], [airsim.WeatherParameter.Snow, airsim.WeatherParameter.RoadSnow]]
    client.simSetTimeOfDay(True,is_start_datetime_dst=True,celestial_clock_speed=450, update_interval_secs=1)
    client.moveToPositionAsync(
        0, 0, z, 1, 60, drivetrain=airsim.DrivetrainType.MaxDegreeOfFreedom, yaw_mode=airsim.YawMode(False, 0)).join()
        
    for idx in range(len(weather_patterns)):
        if idx > 1:
            for ptrn in weather_patterns[idx-1]:
                client.simSetWeatherParameter(ptrn, 0)
        if idx>0:
            for ptrn in weather_patterns[idx]:
                client.simSetWeatherParameter(ptrn, 0.9)
        OrbitAnimal(actor_location['x'], actor_location['y'], 20, 0.8, 1, -30, "Barrel_weather_{}".format(idx), args.output_dir) 
        
    # OrbitAnimal(19.6, 9.6, 2, 0.4, 1, -30, "BlackSheep")

    #OrbitAnimal(-12.18, -13.56, 2, 0.4, 1, -30, "AlpacaRainbow")

    #OrbitAnimal(-12.18, -13.56, 3, 0.4, 1, -20, "AlpacaRainbow")

    # animals = [(19.8, -11, "AlpacaPink"),
    #    (5.42, -3.7, "AlpacaTeal"),
    #    (-12.18, -13.56, "AlpacaRainbow"),
    #    (19.6, 9.6, "BlackSheep"),
    #    (-1.9, -0.9, "Bunny"),
    #    (3.5, 9.4, "Chick"),
    #    (-13.2, -0.25, "Chipmunk"),
    #    (-6.55, 12.25, "Hippo")]

    #configurations = [(2, 0.4, 1, -30), (3, 0.4, 1, -20)]
    #
    # let's find the animals and take some photos
    # for config in configurations:
    #    for animal in animals:
    #        print("Target animal:" + str(animal[2]))
    #        radius = config[0]
    #        speed = config[1]
    #        camera_angle = config[2]

    #        OrbitAnimal(animal[0], animal[1], radius, speed, 1, camera_angle, animal[2])

    #OrbitAnimal(15, 1.0, 2, 0.4, 1, -30, "Unicorn")

    # that's enough fun for now. let's quit cleanly
    land()

    print("Image capture complete...")