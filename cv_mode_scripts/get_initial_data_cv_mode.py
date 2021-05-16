import airsim
import os
import json
import time

# Settings for initial data capture
NUM_TIMESTEPS = 100
SECS_BETWEEN_CAPTURE = 0.1 

# connect to the AirSim simulator
client = airsim.VehicleClient()
client.confirmConnection()

# take images
def recursive_convert_state_to_dict(state):
    if hasattr(state,'__dict__'):
        d = {}
        for k,v in state.__dict__.items():
            d[k] = recursive_convert_state_to_dict(state.__dict__[k])
        return d
    else:
        return state

datastore_path = './airsim_testrun_town_barrels_blah'
if not os.path.exists(datastore_path):
    os.mkdir(datastore_path)

client.simEnableWeather(True)
# client.simSetVehiclePose(airsim.Pose(airsim.Vector3r(0, 0, 0), airsim.to_quaternion(0, 0, 0)), True, vehicle_name='Copter1')


weather_patterns = [[airsim.WeatherParameter.Fog],[airsim.WeatherParameter.MapleLeaf, airsim.WeatherParameter.RoadLeaf],[airsim.WeatherParameter.Rain, airsim.WeatherParameter.Roadwetness], [airsim.WeatherParameter.Snow, airsim.WeatherParameter.RoadSnow]]
client.simSetTimeOfDay(True,is_start_datetime_dst=True,celestial_clock_speed=7200, update_interval_secs=1)

weather_update_freq = 10

json_list = {}
prev_idx = 0
client.simSetWeatherParameter(weather_patterns[0][0], 0.9)
for t in range(NUM_TIMESTEPS):
    idx_cnt = (t//weather_update_freq)%(len(weather_patterns))
    if idx_cnt != prev_idx:
        for ptrn in weather_patterns[prev_idx]:
            client.simSetWeatherParameter(ptrn, 0)
        for ptrn in weather_patterns[idx_cnt]:
            client.simSetWeatherParameter(ptrn, 0.9)
        prev_idx = idx_cnt

    print("Timestep %d",t)
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
                ('airsim_snapshot_%d_timestep_%d.png')%(response.image_type, t)
                ), airsim.get_pfm_array(response))
        else:
            print("Type %d, size %d" % (response.image_type, len(response.image_data_uint8)))
            airsim.write_file(
                os.path.join(datastore_path,
                ('airsim_snapshot_%d_timestep_%d.png')%(response.image_type, t)
                ), response.image_data_uint8)

    json_list[t] = recursive_convert_state_to_dict(client.simGetVehiclePose('Copter1'))
    time.sleep(SECS_BETWEEN_CAPTURE)

print("List of states stored: ",len(json_list.keys()))
with open(os.path.join(datastore_path,"states.json"), 'w') as f1:
    json.dump(json_list, f1)

client.simSetVehiclePose(airsim.Pose(airsim.Vector3r(0, 0, 0), airsim.to_quaternion(0, 0, 0)), True)