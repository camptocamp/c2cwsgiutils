from c2cwsgiutils.scripts.genversion import _get_package_version


def test_get_package_version():
    name, version = _get_package_version("# Editable install with no version control (c2cwsgiutils==3.12.0)")
    assert name == "c2cwsgiutils"
    assert version == "3.12.0"

    name, version = _get_package_version(
        "# Editable install with no version control (c2cgeoportal-geoportal===latest)"
    )
    assert name == "c2cgeoportal-geoportal"
    assert version == "latest"

    name, version = _get_package_version("cee-syslog-handler==0.5.0")
    assert name == "cee-syslog-handler"
    assert version == "0.5.0"
