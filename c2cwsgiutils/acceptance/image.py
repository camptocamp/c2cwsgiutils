import json
import os
import subprocess  # nosec
from typing import TYPE_CHECKING, Any, Optional

import numpy as np  # pylint: disable=import-error
import skimage.color  # pylint: disable=import-error
import skimage.io  # pylint: disable=import-error
import skimage.metrics  # pylint: disable=import-error
import skimage.transform  # pylint: disable=import-error

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

    If the images differ too much, `<result_folder>/<image_filename>.actual-masked.png` and
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


def normalize_image(image: NpNdarrayInt) -> NpNdarrayInt:
    """
    Normalize the image to be comparable.

    - Remove the alpha channel
    - Convert to uint8
    """
    if len(image.shape) == 3 and image.shape[2] == 4:
        image = skimage.color.rgba2rgb(image)
    if np.issubdtype(image.dtype, np.floating):
        image = (image * 255).astype("uint8")
    return image


def check_image(  # pylint: disable=too-many-locals,too-many-statements
    result_folder: str,
    image_to_check: NpNdarrayInt,
    expected_filename: str,
    level: float = 1.0,
    generate_expected_image: bool = False,
    use_mask: bool = True,
) -> None:
    """
    Test that the `<image_to_check>` corresponds to the image `expected_filename`.

    If they don't corresponds the images `<result_folder>/<image_filename>.actual-masked.png` and
    `<result_folder>/<image_filename>.diff.png` are created with the corresponding content.

    Where `<image_filename>` is the name of the `expected_filename`.

    `generate_expected_image` can be set to `True` to generate the expected image, but it should be
    set to `False` in the committed code, because it also disable the test.

    If we found an image that ends with `.mask.png` instead of `.expected.png` of the `expected_filename`
    we use it as a mask.

    Note that the `image_to_check` is altered with the mask.

    Args:
      result_folder: The folder where to store the actual image and the diff
      image_to_check: The image to check
      expected_filename: The expected image filename
      level: The minimum similarity level (between 0.0 and 1.0), default to 1.0
      generate_expected_image: If `True` generate the expected image instead of checking it
      use_mask: If `False` don't use the mask event if the file exists
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
    result_filename = os.path.join(result_folder, f"{image_file_basename}.actual-masked.png")
    diff_filename = os.path.join(result_folder, f"{image_file_basename}.diff.png")

    image_to_check = normalize_image(image_to_check)

    mask = None
    if mask_filename is not None:
        background_color = [255, 255, 255]
        for color in range(3):
            img_hist, _ = skimage.exposure.histogram(
                image_to_check[..., color], nbins=256, source_range="dtype"
            )
            background_color[color] = np.argmax(img_hist)

        mask = skimage.io.imread(mask_filename)

        assert mask is not None, "Wrong mask: " + mask_filename

        # Normalize the mask
        if len(mask.shape) == 3 and mask.shape[2] == 3:
            mask = skimage.color.rgb2gray(mask)

        if len(mask.shape) == 3 and mask.shape[2] == 4:
            mask = skimage.color.rgba2gray(mask)

        if np.issubdtype(mask.dtype, np.floating):
            mask = (mask * 255).astype("uint8")

        assert ((0 < mask) & (mask < 255)).sum() == 0, "Mask should be only black and white image"

        # Convert to boolean
        mask = mask == 0

        assert (
            mask.shape[0] == image_to_check.shape[0] and mask.shape[1] == image_to_check.shape[1]
        ), f"Mask and image should have the same shape ({mask.shape} != {image_to_check.shape})"
        image_to_check[mask] = background_color

    if not os.path.exists(result_folder):
        os.makedirs(result_folder)
    if generate_expected_image:
        skimage.io.imsave(expected_filename, image_to_check)
        return
    if not os.path.isfile(expected_filename):
        skimage.io.imsave(expected_filename, image_to_check)
        assert False, "Expected image not found: " + expected_filename
    expected = skimage.io.imread(expected_filename)
    assert expected is not None, "Wrong image: " + expected_filename
    expected = normalize_image(expected)

    if mask is not None:
        assert (
            expected.shape[0] == mask.shape[0] and expected.shape[1] == mask.shape[1]
        ), f"Mask and expected image should have the same shape ({mask.shape} != {expected.shape})"
        expected[mask] = background_color

    assert (
        expected.shape == image_to_check.shape
    ), f"Images have different shapes expected {expected.shape} != actual {image_to_check.shape}"
    score, diff = skimage.metrics.structural_similarity(
        expected, image_to_check, multichannel=True, full=True, channel_axis=2
    )
    diff = (255 - diff * 255).astype("uint8")

    if diff is not None and score >= level:
        return

    skimage.io.imsave(result_filename, image_to_check)
    if diff is not None:
        skimage.io.imsave(diff_filename, diff)

    assert diff is not None, "No diff generated"
    assert score >= level, f"{result_filename} != {expected_filename} => {diff_filename} ({score} < {level})"


def check_screenshot(
    url: str,
    result_folder: str,
    expected_filename: str,
    width: int = 800,
    height: int = 600,
    sleep: int = 100,
    headers: Optional[dict[str, str]] = None,
    media: Optional[list[dict[str, str]]] = None,
    level: float = 1.0,
    generate_expected_image: bool = False,
    use_mask: bool = True,
) -> None:
    """
    Test that the screenshot of the `url` corresponds to the image `expected_filename`.

    Requires nodejs to be installed.

    See also `check_image` for the other parameters.

    Arguments:
      url: The URL to screenshot
      width: The width of the generated screenshot
      height: The height of the generated screenshot
      sleep: The number of milliseconds to wait before taking the screenshot
      headers: The headers to send in the request to the server
      media: The list of media to emulate in the browser (e.g. to simulate a browser in dark mode)
      expected_filename: See `check_image`
      result_folder: See `check_image`
      level: See `check_image`
      generate_expected_image: See `check_image`
      use_mask: See `check_image`
    """
    if headers is None:
        headers = {}
    if media is None:
        media = []

    if not os.path.exists(os.path.join(os.path.dirname(__file__), "node_modules")):
        subprocess.run(["npm", "install"], cwd=os.path.dirname(__file__), check=True)  # nosec

    image_file_basename = os.path.splitext(os.path.basename(expected_filename))[0]
    if image_file_basename.endswith(".expected"):
        image_file_basename = os.path.splitext(image_file_basename)[0]

    result_folder = os.path.abspath(result_folder)
    actual_filename = os.path.join(result_folder, f"{image_file_basename}.actual.png")
    subprocess.run(  # nosec
        [
            "node",
            "screenshot.js",
            f"--url={url}",
            f"--width={width}",
            f"--height={height}",
            f"--sleep={sleep}",
            f"--headers={json.dumps(headers)}",
            f"--media={json.dumps(media)}",
            f"--output={actual_filename}",
        ],
        cwd=os.path.dirname(__file__),
        check=True,
    )
    check_image(
        result_folder,
        skimage.io.imread(actual_filename)[:, :, :3],
        expected_filename,
        level,
        generate_expected_image,
        use_mask,
    )
