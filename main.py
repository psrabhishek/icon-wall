import glob
import json
import math
import os

from PIL import Image


def load_config(config_file):
    with open(config_file, 'r') as f:
        config = json.load(f)
    return config


def perspective_transform(img, angle=2, skew_factor=0.0008):
    """
    Apply a perspective transformation to make the icon look tilted from the bottom-right perspective.
    :param img: The input image.
    :param angle: The rotation angle in degrees.
    :param skew_factor: The factor by which to skew the perspective.
    :return: The transformed image.
    """
    width, height = img.size
    angle_rad = math.radians(angle)

    # Calculate the size of the new image to avoid chopping
    new_width = int(width * 0.50)
    new_height = int(height * 0.50)

    # Resize the image to avoid chopping
    resized_img = img.resize((new_width, new_height), Image.ANTIALIAS)

    # Rotation matrix
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    rotation_matrix = (
        cos_theta, -sin_theta, new_width / 2 * (1 - cos_theta) + new_height / 2 * sin_theta,
        sin_theta, cos_theta, new_height / 2 * (1 - cos_theta) - new_width / 2 * sin_theta
    )

    # Apply rotation around the center
    rotated_img = resized_img.transform((new_width, new_height), Image.AFFINE, rotation_matrix, resample=Image.BICUBIC)

    # Perspective skew matrix
    coeffs = (
        1, skew_factor, -new_width * skew_factor,
        0, 1, -new_height * skew_factor,
        0, skew_factor, 1
    )

    # Apply perspective transformation
    transformed_img = rotated_img.transform((new_width, new_height), Image.PERSPECTIVE, coeffs, resample=Image.BICUBIC)

    return transformed_img


def generate_background_image(config):
    canvas_size = (config["canvas_size"]["height"], config["canvas_size"]["width"])
    min_gap_ratio = config["min_gap_ratio"]
    image_dir = config["input_dir"]
    output_path = config["output_path"]
    image_transparency = config["image_transparency"]

    # Get all image files from the directory
    file_paths = sorted(glob.glob(os.path.join(image_dir, '*')))
    image_paths = []
    for path in file_paths:
        if path.endswith(".svg"):
            print(f"Warning: SVG files are not supported. Skipping file: {path}")
        elif os.path.isfile(path):
            image_paths.append(path)

    # Calculate the number of images
    num_images = len(image_paths)
    if num_images == 0:
        raise ValueError("No images found in the directory.")

    # Determine the maximum number of columns
    num_columns = int(math.ceil(math.sqrt(num_images * (canvas_size[0] / canvas_size[1]))))
    # distribute uniformly across each row
    num_rows = int(math.ceil(num_images / num_columns))
    num_columns = int(math.ceil(num_images / num_rows))

    print(num_images, 'will be inserted in grid size :', num_rows, 'x', num_columns)

    # Calculate the icon size maintaining 1:1 aspect ratio
    full_icon_size = min(canvas_size[0] // (num_columns + 1), canvas_size[1] // num_rows)
    icon_size = full_icon_size * 0.70

    # Calculate the minimum gap size based on the icon size
    min_gap_size = icon_size * min_gap_ratio

    # Create a blank canvas
    canvas = Image.new('RGBA', canvas_size, (255, 255, 255, image_transparency))

    # Calculate the positions and place each image onto the canvas
    current_image = 0
    print("Processing inputs :")
    for row in range(num_rows):
        # Calculate the number of columns in this row
        columns_in_row = num_columns

        if columns_in_row <= 0:
            continue

        # Calculate the total gap for this row
        total_gap = canvas_size[0] - (columns_in_row * icon_size)

        # If the total gap is smaller than the minimum required gap, adjust the icon size and recalculate total gap
        if total_gap < (columns_in_row + 1) * min_gap_size:
            icon_size = (canvas_size[0] - (columns_in_row + 1) * min_gap_size) / columns_in_row
            total_gap = canvas_size[0] - (columns_in_row * icon_size)

        # Calculate the equal gap size
        gap_size = total_gap / (columns_in_row + 1)

        # Adjust for the starting position for odd and even rows
        start_gap = gap_size * (1 if row % 2 == 0 else 2)

        # Place the images in the row
        for col in range(columns_in_row):
            if current_image >= num_images:
                break

            # Calculate the position
            x_position = start_gap + col * (icon_size + gap_size)
            y_position = (full_icon_size - icon_size) / 2 + row * full_icon_size

            print(str(current_image).rjust(3),image_paths[current_image])
            # Open and resize the image
            img = Image.open(image_paths[current_image]).convert("RGBA")
            img = img.resize((int(icon_size), int(icon_size)), Image.ANTIALIAS)

            # Paste the image onto the canvas
            canvas.paste(img, (int(x_position), int(y_position)), img)

            current_image += 1

    # Save the final image
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)
    canvas.save(output_path, format='PNG')
    print("\nGenerated images can be found in folder :", output_dir)

    # Add extra padding on all sides
    extra_padding_factor = config["extra_padding_factor"]
    new_canvas_size = (int(canvas_size[0] * extra_padding_factor), int(canvas_size[1] * extra_padding_factor))
    new_canvas = Image.new('RGBA', new_canvas_size, (255, 255, 255, image_transparency))

    # Calculate the position to paste the original canvas in the center
    x_offset = (new_canvas_size[0] - canvas_size[0]) // 2
    y_offset = (new_canvas_size[1] - canvas_size[1]) // 2

    # Paste the original canvas onto the new larger canvas
    new_canvas.paste(canvas, (x_offset, y_offset), canvas)
    new_canvas.save(output_path.replace('.png', '_extra_padding.png'), format='PNG')

    # Apply perspective transform to the entire canvas with padding for minimum loss of data
    angle = config["perspective_transform"]["angle"]
    skew_factor = config["perspective_transform"]["skew_factor"]
    transformed_canvas = perspective_transform(new_canvas, angle=angle, skew_factor=skew_factor)

    # Save the final image
    transformed_canvas.save(output_path.replace('.png', '_perspective.png'), format='PNG')


def main():
    config_file = 'config.json'
    config = load_config(config_file)
    generate_background_image(config)


if __name__ == '__main__':
    main()
