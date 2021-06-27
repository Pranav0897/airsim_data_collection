import json
import numpy as np
import re
import argparse

key_name_update_dict = {'object':'annotations', 'bounding_box': 'bbox',
                        'class': 'category_name',
                        }
cname_cid_dict = {}

set_of_objects = set()
object_types = ['barrel', 'tableround', 'chair', 'crate', 
                'tire', 'cardboardbox', 'rock','couch','pallet']
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


def recursive_parse(data, class_to_instance_flag = False):
    new_dict = {}
    for k,v in data.items():
        if type(v)== dict:
            newv = recursive_parse(v)
        else:
            newv = v
        # update key names to match COCO
        if k in key_name_update_dict.keys():
            newkey = key_name_update_dict[k]
        else:
            newkey = k
        

        if newkey == 'category_name':
            assert type(newv) == str, print("category_name not of type str: found {} of type: {}".format(newv, type(newv)))
            set_of_objects.add(newv)
        # if class_to_instance_flag:
            # use class_to_instance_map to set instance ids:
            
        # update bbox from ymin, xmin, ymax, xmax to xmin, ymin, xmax, ymax
        if newkey == 'bbox':
            assert type(newv) == list and len(newv)==4, print("Bbox coordinates : {} of type: {} with length {}, expect list of length 4".format(newv, type(newv), len(newv)))
            newv = newv[[1,0,3,2]]

        # add category_names to set, will add object id and instance id later
        new_dict[newkey] = newv
    return new_dict

def get_instance_ids_from_set(object_set):
    class_to_instance_map = {}
    class_instance_count = {}
    used_classes = set()
    for instances in object_set:
        instance = instances.lower()
        for classes in object_types:
            if classes in instance:
                instance_count = class_instance_count.get(classes, -1) + 1
                class_to_instance_map[instances] = (classes, instance_count)
                class_instance_count[classes] = instance_count
                used_classes.add(classes)
    used_classes = class_to_instance_map.values()
    return class_to_instance_map

# def add_instance_ids_to_json(data):
#     for 

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input_json_file', type=str)
    parser.add_argument('output_json_file', type=str)
    args = parser.parse_args()

    data = json.load(open(args.i,'r'))
    new_data = recursive_parse(data)
    json.dump(new_data, open(args.o,'w'), indent=4, sort_keys=True,
              separators=(', ', ': '), cls=NumpyEncoder)