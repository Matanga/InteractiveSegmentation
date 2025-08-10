# This utility provides a high-level wrapper for Pillow's 2D perspective transformation.
# The core find_coeffs function is a standard algorithm for solving the
# system of linear equations for perspective transform coefficients.

import numpy
from PIL import Image


def find_coeffs(source_points, target_points):
    """
    Finds the coefficients for a perspective transform.

    Args:
        source_points: A list of four (x, y) tuples from the source image.
        target_points: A list of four (x, y) tuples for the target image.

    Returns:
        A list of 8 coefficients.
    """
    matrix = []
    for s, t in zip(source_points, target_points):
        matrix.append([s[0], s[1], 1, 0, 0, 0, -t[0] * s[0], -t[0] * s[1]])
        matrix.append([0, 0, 0, s[0], s[1], 1, -t[1] * s[0], -t[1] * s[1]])

    A = numpy.matrix(matrix, dtype=float)
    B = numpy.array(target_points).reshape(8)

    # Solve the system of linear equations
    res = numpy.dot(numpy.linalg.inv(A.T * A) * A.T, B)
    return numpy.array(res).reshape(8)


class PerspectiveTransform:
    """
    A helper class to apply a perspective warp to a PIL Image.
    This class wraps Pillow's Image.transform with a more intuitive API.
    """

    def __init__(self, target_corners: list):
        """
        Initializes the transformer by calculating the necessary coefficients.

        Args:
            target_corners: A list of four (x, y) tuples defining the
                            destination quadrilateral.
        """
        self.target_corners = target_corners
        self.coeffs = None

    def transform_image(self, image: Image.Image) -> tuple[Image.Image, tuple[int, int]]:
        """
        Applies the perspective warp to the given image.

        Args:
            image: The flat PIL Image to be transformed.

        Returns:
            A tuple containing:
            - The new, warped PIL.Image.Image.
            - The (x, y) coordinates for the top-left paste position.
        """
        # Assume the source image corners are its bounding box
        source_corners = [
            (0, 0),
            (image.width, 0),
            (image.width, image.height),
            (0, image.height)
        ]

        # Calculate the coefficients that map the image corners to the target quad
        self.coeffs = find_coeffs(source_corners, self.target_corners)

        # Determine the size of the output image from the target corners
        min_x = int(min(c[0] for c in self.target_corners))
        min_y = int(min(c[1] for c in self.target_corners))
        max_x = int(max(c[0] for c in self.target_corners))
        max_y = int(max(c[1] for c in self.target_corners))

        output_width = max_x - min_x
        output_height = max_y - min_y

        # Pillow's transform requires the corners relative to the new cropped image
        quad_as_polygon = [(x - min_x, y - min_y) for x, y in self.target_corners]

        # Warp the image
        warped_image = image.transform(
            (output_width, output_height),
            Image.PERSPECTIVE,
            data=self.coeffs,
            resample=Image.BICUBIC  # Use a high-quality resampler
        )

        paste_position = (min_x, min_y)

        return warped_image, paste_position