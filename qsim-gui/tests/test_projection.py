"""Tests for 3D-to-2D Bloch sphere projection geometry."""

import math

import pytest
from qsim_gui.widgets.projection import BlochProjection


@pytest.mark.req("FR-4.3", "FR-4.4")
def test_origin_projects_to_sphere_center() -> None:
    proj = BlochProjection(center_x=100.0, center_y=100.0, radius=50.0)
    ox, oy = proj.project(0.0, 0.0, 0.0)
    assert ox == pytest.approx(100.0, abs=1e-6)
    assert oy == pytest.approx(100.0, abs=1e-6)


@pytest.mark.req("FR-4.3", "FR-4.4", "FR-4.5")
def test_six_axis_endpoints_project_to_distinct_points() -> None:
    proj = BlochProjection(center_x=100.0, center_y=100.0, radius=50.0)

    # Unit axis endpoints
    axes = {
        "+X": (1.0, 0.0, 0.0),
        "-X": (-1.0, 0.0, 0.0),
        "+Y": (0.0, 1.0, 0.0),
        "-Y": (0.0, -1.0, 0.0),
        "+Z": (0.0, 0.0, 1.0),
        "-Z": (0.0, 0.0, -1.0),
    }

    projected_points = {}
    for name, (x, y, z) in axes.items():
        px, py = proj.project(x, y, z)
        projected_points[name] = (px, py)

    # All six endpoints must be distinct
    points_list = list(projected_points.values())
    for i in range(len(points_list)):
        for j in range(i + 1, len(points_list)):
            p1 = points_list[i]
            p2 = points_list[j]
            dist = ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5
            assert dist > 1.0, f"Axis points {i} and {j} collided: {p1} vs {p2}"

    # +Z must be vertically above center (y < center_y) and -Z below center (y > center_y)
    assert projected_points["+Z"][1] < 100.0
    assert projected_points["-Z"][1] > 100.0
    assert projected_points["+Z"][0] == pytest.approx(100.0, abs=1e-6)
    assert projected_points["-Z"][0] == pytest.approx(100.0, abs=1e-6)


@pytest.mark.req("FR-4.17", "FR-4.18")
def test_orbit_projection_preserves_sphere_radius_and_depth() -> None:
    for yaw, elevation in ((0.0, 0.0), (0.7, -0.5), (2.8, 1.2)):
        proj = BlochProjection(100.0, 100.0, 50.0, yaw, elevation)
        for point in ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)):
            px, py = proj.project(*point)
            depth = proj.view_coordinates(*point)[2]
            assert math.hypot(px - 100.0, py - 100.0) ** 2 + (50.0 * depth) ** 2 == pytest.approx(
                50.0**2
            )
        assert proj.project(0.0, 0.0, 0.0) == (100.0, 100.0)
