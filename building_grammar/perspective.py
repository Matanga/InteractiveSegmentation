import numpy
from PIL import Image


def find_coeffs(source_points, target_points):
    """
    Finds the coefficients for a perspective transform using a robust
    least-squares solver.
    """
    matrix = []
    for s, t in zip(source_points, target_points):
        matrix.append([s[0], s[1], 1, 0, 0, 0, -t[0] * s[0], -t[0] * s[1]])
        matrix.append([0, 0, 0, s[0], s[1], 1, -t[1] * s[0], -t[1] * s[1]])

    A = numpy.matrix(matrix, dtype=float)
    B = numpy.array(target_points).reshape(8)

    try:
        # Use the more stable pseudo-inverse (least-squares) solver
        # This is the key change that fixes the distortion.
        res = numpy.dot(numpy.linalg.pinv(A), B)
        return numpy.array(res).reshape(8)

    except numpy.linalg.LinAlgError:
        # This is a fallback in case of a catastrophic failure.
        print("WARNING: Could not solve perspective transform. Returning identity.")
        # Return an "identity" transform (a=1, e=1, others=0) which does nothing.
        return numpy.array([1, 0, 0, 0, 1, 0, 0, 0])


class PerspectiveTransform:
    """A helper class to apply a perspective warp to a PIL Image."""

    def __init__(self, target_corners: list):
        self.target_corners = target_corners

    def transform_image(self, image: Image.Image) -> tuple[Image.Image, tuple[int, int]]:
        """
        Applies the perspective warp to the given image.
        """
        source_corners = [
            (0, 0),
            (image.width, 0),
            (image.width, image.height),
            (0, image.height)
        ]

        min_x = int(min(c[0] for c in self.target_corners))
        min_y = int(min(c[1] for c in self.target_corners))
        max_x = int(max(c[0] for c in self.target_corners))
        max_y = int(max(c[1] for c in self.target_corners))

        output_width = max_x - min_x
        output_height = max_y - min_y
        paste_position = (min_x, min_y)

        if output_width <= 0 or output_height <= 0:
            return Image.new("RGBA", (1, 1)), (0, 0)

        # =======================================================
        # --- THE FIX IS HERE ---
        # Change `for x in ...` to `for x, y in ...` to unpack the tuple
        # =======================================================
        local_target_corners = [(x - min_x, y - min_y) for x, y in self.target_corners]

        coeffs = find_coeffs(source_corners, local_target_corners)

        warped_image = image.transform(
            (output_width, output_height),
            Image.PERSPECTIVE,
            data=coeffs,
            resample=Image.BICUBIC
        )

        return warped_image, paste_position