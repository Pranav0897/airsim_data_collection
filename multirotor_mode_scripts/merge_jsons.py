import glob
import json

files = glob.glob("../modular_buildings_multiobjects_multiviewpoints/airsim_snapshots_*.json")
d = {}
for file in files:
    d1 = json.load(open(file, 'r'))
    for k,v in d1.items():
        d[k] = v

json.dump(d, open("../modular_buildings_multiobjects_multiviewpoints/poses.json",'w'), indent=4, sort_keys=True)

files = glob.glob("../modular_buildings_multiobjects_multiviewpoints/airsim_annotations_*.json")
d = {}
for file in files:
    d1 = json.load(open(file, 'r'))
    for k,v in d1.items():
        d[k] = v

json.dump(d, open("../modular_buildings_multiobjects_multiviewpoints/annotations.json",'w'), indent=4, sort_keys=True)