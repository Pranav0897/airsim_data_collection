import airsim
import numpy as np
import csv

def get_id_color_dict():
    client = airsim.VehicleClient(timeout_value = 7200)
    client.confirmConnection()

    requests = airsim.ImageRequest("0", airsim.ImageType.Segmentation, False, False)

    colors = {}
    for cls_id in range(256):
        # map every asset to cls_id and extract the single RGB value produced
        client.simSetSegmentationObjectID(".*", cls_id, is_name_regex=True)
        response = client.simGetImages([requests])[0]
        img1d = np.frombuffer(response.image_data_uint8, dtype=np.uint8)
        img_rgb = img1d.reshape(response.height, response.width, 3)

        color = tuple(np.unique(img_rgb.reshape(-1, img_rgb.shape[-1]), axis=0)[0])
        print(f"{cls_id}\t{color}")
        colors[cls_id] = color

    with open('color_id_scheme_new.csv', 'w') as f:
        writer = csv.writer(f, delimiter=' ')
        for k, v in colors.items():
            writer.writerow([k] + list(v))

if __name__ == '__main__':
    get_id_color_dict()