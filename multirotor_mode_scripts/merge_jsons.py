import glob
import json

files = glob.glob("../forest1_multiobject_multiview/airsim_snapshots_*.json")
d = {}
for file in files:
    d1 = json.load(open(file, 'r'))
    for k,v in d1.items():
        d[k] = v

json.dump(d, open("../forest1_multiobject_multiview/poses.json",'w'), indent=4, sort_keys=True)

files = glob.glob("../forest1_multiobject_multiview/airsim_annotations_*.json")
d = {}
for file in files:
    d1 = json.load(open(file, 'r'))
    for k,v in d1.items():
        d[k] = v

json.dump(d, open("../forest1_multiobject_multiview/annotations.json",'w'), indent=4, sort_keys=True)