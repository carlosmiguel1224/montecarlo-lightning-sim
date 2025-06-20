from PIL import Image
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
def latlon_to_pixel(lat, lon, lat_min, lat_max, lon_min, lon_max, bbox):
    min_x, min_y, max_x, max_y = bbox
    bbox_width = max_x - min_x
    bbox_height = max_y - min_y

    x_frac = (lon - lon_min) / (lon_max - lon_min)
    y_frac = (lat_max - lat) / (lat_max - lat_min)

    x = int(min_x + x_frac * bbox_width)
    y = int(min_y + y_frac * bbox_height)

    return x, y


def latlon_to_pixel_simple(lat, lon, lat_min, lat_max, lon_min, lon_max, width, height):
    x_frac = (lon - lon_min) / (lon_max - lon_min)
    y_frac = (lat_max - lat) / (lat_max - lat_min)

    x = int(x_frac * width)
    y = int(y_frac * height)
    return x, y


def get_content_bbox(image_path, threshold=200):
    img = Image.open(image_path).convert("RGB")
    np_img = np.array(img)

    # Create mask of non-white pixels (tolerant threshold)
    mask = (np_img < threshold).any(axis=2)
    
    coords = np.argwhere(mask)
    if coords.size == 0:
        return None  # Entire image is white
    min_y, min_x = coords.min(axis=0)
    max_y, max_x = coords.max(axis=0)
    return (min_x, min_y, max_x, max_y)


def plot_heatmap_pixels(image_path, lat_min, lat_max, lon_min, lon_max):
    img = Image.open(image_path).convert("RGB")
    np_img = np.array(img)
    bbox = get_content_bbox(image_path)
    if bbox is None:
        print("Image is fully white — no map content detected.")
        return

    min_x, min_y, max_x, max_y = bbox
    xs = []
    ys = []
    colors = []

    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            r, g, b = np_img[y, x]
            if (r, g, b) != (255, 255, 255):  # Avoid white space
                lon = lon_min + (x - min_x) / (max_x - min_x) * (lon_max - lon_min)
                lat = lat_max - (y - min_y) / (max_y - min_y) * (lat_max - lat_min)
                xs.append(lon)
                ys.append(lat)
                colors.append((r / 255, g / 255, b / 255))  # Normalize to [0,1] for matplotlib

    plt.figure(figsize=(12, 8))
    plt.scatter(xs, ys, c=colors, s=1)
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.title("Mapped Pixels from Image")
    plt.grid(True)
    plt.show()


def plot_mapped_point_on_image(image_path, x, y, bbox=None, label="Mapped Point"):
    img = Image.open(image_path)
    np_img = np.array(img)

    fig, ax = plt.subplots()
    ax.imshow(np_img)

    # Draw the bounding box if provided
    if bbox:
        min_x, min_y, max_x, max_y = bbox
        rect = plt.Rectangle((min_x, min_y), max_x - min_x, max_y - min_y,
                             linewidth=1.5, edgecolor='red', facecolor='none', linestyle='--')
        ax.add_patch(rect)

    # Mark the point
    ax.plot(x, y, marker='o', color='black', markersize=6, label=label)
    ax.set_title(f"Mapped Coordinates on Image ({label})")
    ax.legend()
    plt.show()



def main():

    lat = 28.5383
    lon = -81.3792
    image_path = "ussampleheatmap.jpeg"
    lon_min, lon_max = -125.0, -66.5
    lat_min, lat_max = 24.0, 49.5
    img = Image.open(image_path)
    width, height = img.size
    bbox = get_content_bbox(image_path)
    x2, y2 = latlon_to_pixel(lat, lon, lat_min, lat_max, lon_min, lon_max, bbox)
    x, y = latlon_to_pixel_simple(lat, lon, lat_min, lat_max, lon_min, lon_max, width, height)
    print(f"Mapped pixel: ({x2}, {y2})")
    print(f"Simple method:({x},{y})")

    plot_mapped_point_on_image(image_path, x, y, bbox, label="Orlando")
if __name__ == "__main__":
    main()