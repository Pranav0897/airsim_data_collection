import airsim

import os
import sys
import math
import time
import argparse
from PIL import Image
import json
import numpy as np

def recursive_convert_state_to_dict(state):
    if hasattr(state,'__dict__'):
        d = {}
        for k in state.__dict__.keys():
            d[k] = recursive_convert_state_to_dict(state.__dict__[k])
        return d
    else:
        return state


class Position:
    def __init__(self, pos):
        self.x = pos.x_val
        self.y = pos.y_val
        self.z = pos.z_val

class NumpyEncoder(json.JSONEncoder):
    """ Custom encoder for numpy data types """
    def default(self, obj):
        if isinstance(obj, (np.int_, np.intc, np.intp, np.int8,
                            np.int16, np.int32, np.int64, np.uint8,
                            np.uint16, np.uint32, np.uint64)):

            return int(obj)

        elif isinstance(obj, (np.float_, np.float16, np.float32, np.float64)):
            return float(obj)

        elif isinstance(obj, (np.complex_, np.complex64, np.complex128)):
            return {'real': obj.real, 'imag': obj.imag}

        elif isinstance(obj, (np.ndarray,)):
            return obj.tolist()

        elif isinstance(obj, (np.bool_)):
            return bool(obj)

        elif isinstance(obj, (np.void)): 
            return None

        return json.JSONEncoder.default(self, obj)

# Make the drone fly in a circle.


class OrbitNavigator:
    def __init__(self, photo_prefix="photo_", radius=2, altitude=10, speed=2, iterations=1, center=[1, 0], 
                        snapshots=None, image_dir="./images_blah/", filename_offset = 0, mesh_colors = {}):
        
        self.radius = radius
        self.altitude = altitude
        self.speed = speed
        self.iterations = iterations
        self.snapshots = snapshots
        self.snapshot_delta = None
        self.next_snapshot = None
        self.image_dir = image_dir
        self.z = None
        self.snapshot_index = 0
        self.photo_prefix = photo_prefix
        self.takeoff = True  # whether we did a take off
        self.json_data_list = {}
        self.offset = filename_offset
        self.mesh_colors = mesh_colors

        if self.snapshots is not None and self.snapshots > 0:
            self.snapshot_delta = 360 / self.snapshots

        if self.iterations <= 0:
            self.iterations = 1

        if len(center) != 2:
            raise Exception(
                "Expecting '[x,y]' for the center direction vector")

        # center is just a direction vector, so normalize it to compute the actual cx,cy locations.
        cx = float(center[0])
        cy = float(center[1])
        length = math.sqrt((cx*cx)+(cy*cy))
        cx /= length
        cy /= length
        cx *= self.radius
        cy *= self.radius

        self.client = airsim.MultirotorClient()
        self.client.confirmConnection()
        self.client.enableApiControl(True)
        # for name, id_color in self.mesh_colors.items():
        #     self.client.simSetSegmentationObjectID(name, id_color[0])
        
        self.home = self.client.getMultirotorState().kinematics_estimated.position
        # check that our home position is stable
        start = time.time()
        count = 0
        while count < 100:
            pos = self.home
            if abs(pos.z_val - self.home.z_val) > 1:
                count = 0
                self.home = pos
                if time.time() - start > 10:
                    print(
                        "Drone position is drifting, we are waiting for it to settle down...")
                    start = time
            else:
                count += 1

        self.center = self.client.getMultirotorState().kinematics_estimated.position
        self.center.x_val += cx
        self.center.y_val += cy

        # setting up directories to store images in
        self.subdirs = {
            airsim.ImageType.Scene: 'Scene' ,
            airsim.ImageType.DepthPlanar: 'DepthPlanar' ,
            airsim.ImageType.DepthPerspective: 'DepthPerspective' ,
            airsim.ImageType.Segmentation: 'Segmentation' ,
            airsim.ImageType.SurfaceNormals: 'SurfaceNormals' ,
            airsim.ImageType.Infrared: 'Infrared' }

        if not os.path.exists(self.image_dir):
            os.makedirs(self.image_dir)
        for subdir in self.subdirs.values():
            sdpath = os.path.join(self.image_dir, subdir)
            if not os.path.exists(sdpath):
                os.makedirs(sdpath)
        # list of dicts for storing semantic segmentation bounding boxes
        self.semseg_list = {}

    def start(self):
        print("arming the drone...")
        self.client.armDisarm(True)

        # AirSim uses NED coordinates so negative axis is up.
        start = self.client.getMultirotorState().kinematics_estimated.position
        landed = self.client.getMultirotorState().landed_state
        if not self.takeoff and landed == airsim.LandedState.Landed:
            self.takeoff = True
            print("taking off...")
            self.client.takeoffAsync().join()
            start = self.client.getMultirotorState().kinematics_estimated.position
            z = -self.altitude + self.home.z_val
        else:
            print("already flying so we will orbit at current altitude {}".format(
                start.z_val))
            z = start.z_val  # use current altitude then

        print("climbing to position: {},{},{}".format(
            start.x_val, start.y_val, z))
        self.client.moveToPositionAsync(
            start.x_val, start.y_val, z, self.speed).join()
        self.z = z

        print("ramping up to speed...")
        count = 0
        self.start_angle = None
        self.next_snapshot = None

        # ramp up time
        ramptime = self.radius / 10
        self.start_time = time.time()

        while count < self.iterations and self.snapshot_index < self.snapshots:
            # ramp up to full speed in smooth increments so we don't start too aggressively.
            now = time.time()
            speed = self.speed
            diff = now - self.start_time
            if diff < ramptime:
                speed = self.speed * diff / ramptime
            elif ramptime > 0:
                print("reached full speed...")
                ramptime = 0

            lookahead_angle = speed / self.radius

            # compute current angle
            pos = self.client.getMultirotorState().kinematics_estimated.position
            dx = pos.x_val - self.center.x_val
            dy = pos.y_val - self.center.y_val
            actual_radius = math.sqrt((dx*dx) + (dy*dy))
            angle_to_center = math.atan2(dy, dx)

            camera_heading = (angle_to_center - math.pi) * 180 / math.pi

            # compute lookahead
            lookahead_x = self.center.x_val + self.radius * \
                math.cos(angle_to_center + lookahead_angle)
            lookahead_y = self.center.y_val + self.radius * \
                math.sin(angle_to_center + lookahead_angle)

            vx = lookahead_x - pos.x_val
            vy = lookahead_y - pos.y_val

            if self.track_orbits(angle_to_center * 180 / math.pi):
                count += 1
                print("completed {} orbits".format(count))

            self.camera_heading = camera_heading
            self.client.moveByVelocityZAsync(
                vx, vy, z, 1, airsim.DrivetrainType.MaxDegreeOfFreedom, airsim.YawMode(False, camera_heading))

        self.client.moveToPositionAsync(start.x_val, start.y_val, z, 2).join()
        # orbiting done. store all positions
        k = list(self.json_data_list.keys())
        with open(os.path.join(self.image_dir, self.photo_prefix+"airsim_snapshots_timesteps_{}_to_{}.json".format(min(k), max(k))), 'w') as f1:
            json.dump(self.json_data_list, f1)
        
        k = list(self.semseg_list.keys())
        with open(os.path.join(self.image_dir, self.photo_prefix+"airsim_annotations_timesteps_{}_to_{}.json".format(min(k), max(k))), 'w') as f1:
            json.dump(self.semseg_list, f1, indent=4, sort_keys=True,
              separators=(', ', ': '), cls=NumpyEncoder)
              
        return self.snapshot_index + self.offset

    def track_orbits(self, angle):
        # tracking # of completed orbits is surprisingly tricky to get right in order to handle random wobbles
        # about the starting point.  So we watch for complete 1/2 orbits to avoid that problem.
        if angle < 0:
            angle += 360

        if self.start_angle is None:
            self.start_angle = angle
            if self.snapshot_delta:
                self.next_snapshot = angle + self.snapshot_delta
            self.previous_angle = angle
            self.shifted = False
            self.previous_sign = None
            self.previous_diff = None
            self.quarter = False
            return False

        # now we just have to watch for a smooth crossing from negative diff to positive diff
        if self.previous_angle is None:
            self.previous_angle = angle
            return False

        # ignore the click over from 360 back to 0
        if self.previous_angle > 350 and angle < 20:
            if self.snapshot_delta and self.next_snapshot >= 360:
                self.next_snapshot -= 360
            return False

        diff = self.previous_angle - angle
        crossing = False
        self.previous_angle = angle

        if self.snapshot_delta and angle > self.next_snapshot:
            print("Taking snapshot at angle {}".format(angle))
            self.take_snapshot()
            self.next_snapshot += self.snapshot_delta

        diff = abs(angle - self.start_angle)
        if diff > 45:
            self.quarter = True

        if self.quarter and self.previous_diff is not None and diff != self.previous_diff:
            # watch direction this diff is moving if it switches from shrinking to growing
            # then we passed the starting point.
            direction = self.sign(self.previous_diff - diff)
            if self.previous_sign is None:
                self.previous_sign = direction
            elif self.previous_sign > 0 and direction < 0:
                if diff < 45:
                    self.quarter = False
                    if self.snapshots <= self.snapshot_index + 1:
                        crossing = True
            self.previous_sign = direction
        self.previous_diff = diff

        return crossing

    def take_snapshot(self):

        # first hold our current position so drone doesn't try and keep flying while we take the picture.
        pos = self.client.getMultirotorState().kinematics_estimated.position
        self.client.moveToPositionAsync(pos.x_val, pos.y_val, self.z, 0.25, 3, airsim.DrivetrainType.MaxDegreeOfFreedom,
                                        airsim.YawMode(False, self.camera_heading))
        responses = self.client.simGetImages([
            airsim.ImageRequest("front_center", airsim.ImageType.Scene),
            airsim.ImageRequest("front_center", airsim.ImageType.DepthPlanar, True),
            airsim.ImageRequest("front_center", airsim.ImageType.DepthPerspective, True),
            # airsim.ImageRequest("front_center", airsim.ImageType.DepthVis),
            # airsim.ImageRequest("front_center", airsim.ImageType.DisparityNormalized),
            airsim.ImageRequest("front_center", airsim.ImageType.Segmentation, False, False),
            airsim.ImageRequest("front_center", airsim.ImageType.SurfaceNormals),
            airsim.ImageRequest("front_center", airsim.ImageType.Infrared)])

        # print('Retrieved images: %d', len(responses))
        bbox_list = {}
        for response in responses:
            if response.pixels_as_float:
                # print("Type %d, size %d" % (response.image_type, len(response.image_data_float)))
                airsim.write_pfm(
                    os.path.join(os.path.join(self.image_dir, self.subdirs[response.image_type]),
                    self.photo_prefix + ('%d.png')%(self.snapshot_index+self.offset)
                    ), airsim.get_pfm_array(response))
            else:
                # print("Type %d, size %d" % (response.image_type, len(response.image_data_uint8)))
                if response.image_type == airsim.ImageType.Segmentation:
                # semantic segmentaion usually is of type uint8
                
                    img = np.fromstring(response.image_data_uint8, dtype=np.uint8).reshape(response.height, response.width, 3)
                    new_img = img.astype(np.uint32)
                    # img = np.flipud(img)
                    packed = new_img[:,:,0]<<16 | new_img[:,:,1]<<8 | new_img[:,:,2]
                    
                    img_size = img.shape[:2]
                    for name, id_color in self.mesh_colors.items():
                        id = id_color[0]
                        color = np.asarray(id_color[1], dtype=np.uint32)
                        packed_color = color[0] << 16 | color[1]<<8 | color[2]
                        px, py = np.where(packed==packed_color)
                        if len(px) == 0 and len(py) == 0:
                            # object not in view
                            bbox_list[name] = None
                        else:
                            bbox_list[name] = [px.min(), py.min(), px.max(), py.max()]
                    Image.fromarray(img).save(os.path.join(os.path.join(self.image_dir, self.subdirs[response.image_type]),
                    self.photo_prefix + ('%d.png')%(self.snapshot_index+self.offset)
                    ))
                else:
                    airsim.write_file(
                    os.path.join(os.path.join(self.image_dir, self.subdirs[response.image_type]),
                    self.photo_prefix + ('%d.png')%(self.snapshot_index+self.offset)
                    ), response.image_data_uint8)
                
        json_list = recursive_convert_state_to_dict(self.client.getMultirotorState())
        self.json_data_list[self.snapshot_index+self.offset] = json_list
        d = {}
        d['image_id'] = self.snapshot_index + self.offset
        d['file_name'] = self.photo_prefix + ('%d.png')%(self.snapshot_index+self.offset)
        d['size'] = list(img_size) + [3]
        d['object'] = [{'object_id':id_color[0], 'class':name, 'bounding_box':tuple(bbox_list[name])} for name, id_color in self.mesh_colors.items() if bbox_list[name] is not None]
        
        self.semseg_list[self.snapshot_index+self.offset] = d
        # k = list(self.semseg_list.keys())
        # with open(os.path.join(self.image_dir, self.photo_prefix+"airsim_annotations_timesteps_{}_to_{}.json".format(min(k), max(k))), 'w') as f1:
        #     json.dump(self.semseg_list, f1, indent=4, sort_keys=True,
        #       separators=(', ', ': '), cls = NumpyEncoder)

        # time.sleep(SECS_BETWEEN_CAPTURE)
        
        # responses = self.client.simGetImages([airsim.ImageRequest(
        #     0, airsim.ImageType.Scene)])  # scene vision image in png format
        # response = responses[0]
        # filename = self.photo_prefix + \
        #     str(self.snapshot_index) + "_" + str(int(time.time()))
        self.snapshot_index += 1
        # airsim.write_file(os.path.normpath(
        #     self.image_dir + filename + '.png'), response.image_data_uint8)
        # print("Saved snapshot: {}".format(filename))
        # cause smooth ramp up to happen again after photo is taken.
        self.start_time = time.time()

    def sign(self, s):
        if s < 0:
            return -1
        return 1


if __name__ == "__main__":
    args = sys.argv
    args.pop(0)
    arg_parser = argparse.ArgumentParser(
        "Orbit.py makes drone fly in a circle with camera pointed at the given center vector")
    arg_parser.add_argument("--radius", type=float,
                            help="radius of the orbit", default=10)
    arg_parser.add_argument("--altitude", type=float,
                            help="altitude of orbit (in positive meters)", default=20)
    arg_parser.add_argument("--speed", type=float,
                            help="speed of orbit (in meters/second)", default=3)
    arg_parser.add_argument(
        "--center", help="x,y direction vector pointing to center of orbit from current starting position (default 1,0)", default="1,0")
    arg_parser.add_argument("--iterations", type=float,
                            help="number of 360 degree orbits (default 3)", default=3)
    arg_parser.add_argument("--snapshots", type=float,
                            help="number of FPV snapshots to take during orbit (default 0)", default=0)
    args = arg_parser.parse_args(args)
    nav = OrbitNavigator(photo_prefix="photo_", radius=args.radius, altitude=args.altitude, speed=args.speed, iterations=args.iterations, center=args.center.split(','), snapshots=args.snapshots, image_dir="./images_blah/")
    nav.start()