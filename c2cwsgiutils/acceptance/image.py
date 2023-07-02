import os
from typing import TYPE_CHECKING, Any, Optional

import numpy as np
import skimage.color
import skimage.io
import skimage.metrics
import skimage.transform

if TYPE_CHECKING:
    from typing import TypeAlias

    NpNdarrayInt: TypeAlias = np.ndarray[np.uint8, Any]
else:
    NpNdarrayInt = np.ndarray


def check_image_file(
    result_folder: str,
    image_filename_to_check: str,
    expected_filename: str,
    level: float = 1.0,
    generate_expected_image: bool = False,
    use_mask: bool = True,
) -> None:
    """
    Test that the `image_filename_to_check` corresponds to the image `expected_filename`.

    If the images differ too much, `<result_folder>/<image_filename>.result.png` and
    `<result_folder>/<image_filename>.diff.png` are created with the corresponding content.

    Where `<image_filename>` is the name of the `expected_filename`.

    `generate_expected_image` can be set to `True` to generate the expected image, but it should be
    set to `False` in the committed code, because it also disable the test.

    If we found an image that ends with `.mask.png` instead of `.expected.png` of the `expected_filename`
    we use it as a mask.
    """
    result = skimage.io.imread(image_filename_to_check)
    assert result is not None, "Wrong image: " + image_filename_to_check
    check_image(result_folder, result, expected_filename, level, generate_expected_image, use_mask)


def check_image(
    result_folder: str,
    image_to_check: NpNdarrayInt,
    expected_filename: str,
    level: float = 1.0,
    generate_expected_image: bool = False,
    use_mask: bool = True,
) -> None:
    """
    Test that the `<image_to_check>` corresponds to the image `expected_filename`.

    If they don't corresponds the images `<result_folder>/<image_filename>.result.png` and
    `<result_folder>/<image_filename>.diff.png` are created with the corresponding content.

    Where `<image_filename>` is the name of the `expected_filename`.

    `generate_expected_image` can be set to `True` to generate the expected image, but it should be
    set to `False` in the committed code, because it also disable the test.

    If we found an image that ends with `.mask.png` instead of `.expected.png` of the `expected_filename`
    we use it as a mask.

    Note that the `image_to_check` is altered with the mask.
    """
    assert image_to_check is not None, "Image required"
    image_file_basename = os.path.splitext(os.path.basename(expected_filename))[0]
    mask_filename: Optional[str] = None
    if image_file_basename.endswith(".expected"):
        image_file_basename = os.path.splitext(image_file_basename)[0]
        if use_mask:
            mask_filename = os.path.join(
                os.path.dirname(expected_filename), image_file_basename + ".mask.png"
            )
            if not os.path.isfile(mask_filename):
                mask_filename = None
    result_filename = os.path.join(result_folder, f"{image_file_basename}.result.png")
    diff_filename = os.path.join(result_folder, f"{image_file_basename}.diff.png")

    if len(image_to_check.shape) == 3 and image_to_check.shape[2] == 4:
        image_to_check = skimage.color.rgba2rgb(image_to_check)

    mask = None
    if mask_filename is not None:
        mask = skimage.io.imread(mask_filename)
        if len(mask.shape) == 3 and mask.shape[2] == 3:
            mask = skimage.color.rgb2gray(mask)
        if len(mask.shape) == 3 and mask.shape[2] == 4:
            mask = skimage.color.rgba2gray(mask)

        assert mask is not None, "Wrong mask: " + mask_filename
        assert ((0 < mask) & (mask < 255)).sum() == 0, "Mask should be only black and white image"

        image_to_check[mask == 0] = [255, 255, 255]

    if np.issubdtype(image_to_check.dtype, np.floating):
        image_to_check = (image_to_check * 255).astype("uint8")

    if not os.path.exists(result_folder):
        os.makedirs(result_folder)
    if generate_expected_image:
        skimage.io.imsave(expected_filename, image_to_check)
        return
    if not os.path.isfile(expected_filename):
        skimage.io.imsave(result_filename, image_to_check)
        skimage.io.imsave(expected_filename, image_to_check)
        assert False, "Expected image not found: " + expected_filename
    expected = skimage.io.imread(expected_filename)
    assert expected is not None, "Wrong image: " + expected_filename

    if np.issubdtype(expected.dtype, np.floating):
        expected = (expected * 255).astype("uint8")

    if mask is not None:
        expected[mask == 0] = [255, 255, 255]

    score, diff = skimage.metrics.structural_similarity(
        expected, image_to_check, multichannel=True, full=True, channel_axis=2
    )
    diff = (255 - diff * 255).astype("uint8")

    if diff is None:
        skimage.io.imsave(result_filename, image_to_check)
        assert diff is not None, "No diff generated"
    if score < level:
        skimage.io.imsave(result_filename, image_to_check)
        skimage.io.imsave(diff_filename, diff)
        assert (
            score >= level
        ), f"{result_filename} != {expected_filename} => {diff_filename} ({score} < {level})"
