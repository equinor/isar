import pytest

from models.geometry.joints import Joints


def test_get_mission():
    with pytest.raises(ValueError):
        Joints(j1=10, j2=1)
        Joints(j1=-10, j2=1)
        Joints(j1=10, j2=None)
    assert Joints(j1=1, j2=1) is not None
    assert Joints(j1=1, j2=2) is not None
