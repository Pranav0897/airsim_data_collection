# ready to run example: PythonClient/multirotor/hello_drone.py
import airsim
import os
import json
import time

def recursive_convert_state_to_dict(state):
    if hasattr(state,'__dict__'):
        d = {}
        for k in state.__dict__.keys():
            d[k] = recursive_convert_state_to_dict(state.__dict__[k])
        return d
    else:
        return state

json_path = './airsim_testrun/states.json'
with open(json_path, 'r') as f1:
    data = json.load(f1)
datastore_path = './airsim_rerun/'
    
if not os.path.exists(datastore_path):
    os.mkdir(datastore_path)


# connect to the AirSim simulator
client = airsim.VehicleClient()
client.confirmConnection()

# Play around with the weather and lighting conditions
client.simEnableWeather(True)
client.simSetVehiclePose(airsim.Pose(airsim.Vector3r(0, 0, 0), airsim.to_quaternion(0, 0, 0)), True, vehicle_name='Copter1')
client.simSetWeatherParameter(airsim.WeatherParameter.Snow, 0.9)
client.simSetTimeOfDay(True,is_start_datetime_dst=True,celestial_clock_speed=7200, update_interval_secs=1)

json_list = {}
for k,v in data.items():
    try:
        print("Timestep ",k)

        loc = v['position']
        pose = v['orientation']

        client.simSetVehiclePose(airsim.Pose(airsim.Vector3r(x_val = loc['x_val'], y_val = loc['y_val'], z_val = loc['z_val']), 
                                airsim.Quaternionr(x_val = pose['x_val'], y_val = pose['y_val'], z_val = pose['z_val'], w_val = pose['w_val'])), True,'Copter1')

        responses = client.simGetImages([
            airsim.ImageRequest("front_center", airsim.ImageType.Scene),
            airsim.ImageRequest("front_center", airsim.ImageType.DepthPlanner, True),
            airsim.ImageRequest("front_center", airsim.ImageType.DepthPerspective, True),
            airsim.ImageRequest("front_center", airsim.ImageType.DepthVis),
            airsim.ImageRequest("front_center", airsim.ImageType.DisparityNormalized),
            airsim.ImageRequest("front_center", airsim.ImageType.Segmentation),
            airsim.ImageRequest("front_center", airsim.ImageType.SurfaceNormals),
            airsim.ImageRequest("front_center", airsim.ImageType.Infrared)])
        print('Retrieved images: %d', len(responses))

        for response in responses:
            if response.pixels_as_float:
                print("Type %d, size %d" % (response.image_type, len(response.image_data_float)))
                airsim.write_pfm(
                    os.path.join(datastore_path,
                        ('airsim_snapshot_%d_timestep_%d.png')%(response.image_type, int(k))), 
                    airsim.get_pfm_array(response))
            else:
                print("Type %d, size %d" % (response.image_type, len(response.image_data_uint8)))
                airsim.write_file(os.path.join(datastore_path,
                    ('airsim_snapshot_%d_timestep_%d.png')%(response.image_type, int(k))
                    ), response.image_data_uint8)

        json_list[k] = recursive_convert_state_to_dict(client.simGetVehiclePose())
        time.sleep(1)

    except:
        print("Something went wrong")
        break

print("List of states stored: ",len(json_list.keys()))
with open(os.path.join(datastore_path,"states.json"), 'w') as f1:
    json.dump(json_list, f1)

client.simSetVehiclePose(airsim.Pose(airsim.Vector3r(0, 0, 0), airsim.to_quaternion(0, 0, 0)), True, vehicle_name='Copter1')