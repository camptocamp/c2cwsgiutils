import json
import subprocess  # nosec
from pathlib import Path
from typing import TYPE_CHECKING, Any

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
    result_folder: str | Path,
    image_filename_to_check: str | Path,
    expected_filename: str | Path,
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
    assert result is not None, f"Wrong image: {image_filename_to_check}"
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
    result_folder: str | Path,
    image_to_check: NpNdarrayInt,
    expected_filename: str | Path,
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
    result_folder = Path(result_folder)
    expected_filename = Path(expected_filename)
    image_file_basename = expected_filename.stem
    mask_filename: Path | None = None
    if image_file_basename.endswith(".expected"):
        image_file_basename = Path(image_file_basename).stem
        if use_mask:
            mask_filename = expected_filename.with_name(image_file_basename + ".mask.png")
            if not mask_filename.is_file():
                mask_filename = None
    result_filename = result_folder / f"{image_file_basename}.actual-masked.png"
    diff_filename = result_folder / f"{image_file_basename}.diff.png"

    image_to_check = normalize_image(image_to_check)

    mask = None
    if mask_filename is not None:
        background_color = [255, 255, 255]
        for color in range(3):
            img_hist, _ = skimage.exposure.histogram(
                image_to_check[..., color],
                nbins=256,
                source_range="dtype",
            )
            background_color[color] = np.argmax(img_hist)

        mask = skimage.io.imread(mask_filename)

        assert mask is not None, "Wrong mask: " + str(mask_filename)

        # Normalize the mask
        if len(mask.shape) == 3 and mask.shape[2] == 3:
            mask = skimage.color.rgb2gray(mask)

        if len(mask.shape) == 3 and mask.shape[2] == 4:
            mask = skimage.color.rgba2gray(mask)

        if np.issubdtype(mask.dtype, np.floating):
            mask = (mask * 255).astype("uint8")

        assert ((mask > 0) & (mask < 255)).sum() == 0, "Mask should be only black and white image"

        # Convert to boolean
        mask = mask == 0

        assert mask.shape[0] == image_to_check.shape[0] and mask.shape[1] == image_to_check.shape[1], (  # noqa: PT018
            f"Mask and image should have the same shape ({mask.shape} != {image_to_check.shape})"
        )
        image_to_check[mask] = background_color

    if not result_folder.exists():
        result_folder.mkdir(parents=True)
    if generate_expected_image:
        skimage.io.imsave(expected_filename, image_to_check)
        return
    if not expected_filename.is_file():
        skimage.io.imsave(expected_filename, image_to_check)
        raise AssertionError("Expected image not found: " + str(expected_filename))
    expected = skimage.io.imread(expected_filename)
    assert expected is not None, "Wrong image: " + str(expected_filename)
    expected = normalize_image(expected)

    if mask is not None:
        assert expected.shape[0] == mask.shape[0] and expected.shape[1] == mask.shape[1], (  # noqa: PT018
            f"Mask and expected image should have the same shape ({mask.shape} != {expected.shape})"
        )
        expected[mask] = background_color

    assert expected.shape == image_to_check.shape, (
        f"Images have different shapes expected {expected.shape} != actual {image_to_check.shape}"
    )
    score, diff = skimage.metrics.structural_similarity(
        expected,
        image_to_check,
        multichannel=True,
        full=True,
        channel_axis=2,
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
    result_folder: str | Path,
    expected_filename: str | Path,
    width: int = 800,
    height: int = 600,
    sleep: int = 100,
    headers: dict[str, str] | None = None,
    media: list[dict[str, str]] | None = None,
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

    if not Path(__file__).parent.joinpath("node_modules").exists():
        subprocess.run(["npm", "install"], cwd=Path(__file__).parent, check=True)  # noqa: S603,S607

    image_file_basename = Path(expected_filename).stem
    if image_file_basename.endswith(".expected"):
        image_file_basename = Path(image_file_basename).stem

    result_folder = Path(result_folder).resolve()
    actual_filename = result_folder / f"{image_file_basename}.actual.png"
    subprocess.run(  # noqa: S603,S607,RUF100
        [  # noqa: S607
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
        cwd=Path(__file__).parent,
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
