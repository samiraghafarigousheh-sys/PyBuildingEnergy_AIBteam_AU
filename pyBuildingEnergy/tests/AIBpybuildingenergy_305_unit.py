import os
import sys
import warnings
import numpy as np
import pandas as pd
import pytest

from pyBuildingEnergy.tests.climate_setpoints import get_ncc_setpoints, apply_setpoints_to_building

warnings.simplefilter(action='ignore', category=FutureWarning)
pd.options.mode.chained_assignment = None

_HERE = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '../src')))

from pybuildingenergy.source.utils import ISO52016
from pybuildingenergy.source.check_input import sanitize_and_validate_BUI
from pybuildingenergy.source.DHW import Volume_and_energy_DHW_calculation, generate_calendar

# ---------------------------------------------------------------------------
# 1) CONSTRUCTION U-VALUES & THERMAL CAPACITY
# ---------------------------------------------------------------------------
# U-values (W/m²·K) — Australian BCA 2006 minimum-spec
U_EXT_WALL = 1.00   # brick veneer / precast w/ R1.0 insulation
U_INT_WALL = 2.50   # concrete block + plasterboard, no insulation
U_INT_SLAB = 1.80   # 200 mm concrete intermediate floor
U_WINDOW   = 5.40   # aluminium-frame single glazing
G_WINDOW   = 0.65   # SHGC of clear single glazing

# Solar absorptance — confirmed dark red brick from exterior photo
ABS_EXT_WALL = 0.75
ABS_INT      = 0.0

# Areal thermal capacity (J/m²·K)
C_EXT_WALL = 450_000   # heavy concrete external wall
C_INT_WALL = 330_000   # concrete-block partition
C_INT_SLAB = 480_000   # 200 mm concrete slab
C_WINDOW   = 0

# ---------------------------------------------------------------------------
# 2) GEOMETRY  — Apt 305, 50 Barry St Carlton (studio, 3rd floor, west-facing)
#
#  Source: realestate.com.au listing + exterior photo
#  - West-facing overlooking Barry St ("westerly aspect, full width windows")
#  - Two horizontal-slider panes sized from exterior photo:
#    ~1.5 m wide x 1.1 m high each -> WWR ~24 % of west facade
#    (prev. 0.9 x 0.9 m = 12 % WWR was too small for "full width windows")
#  - "Higher than standard ceilings" retained at 2.7 m
#  - Single-occupant studio (~20 m²)
# ---------------------------------------------------------------------------
LEN_NS  = 5.0   # N-S length, m  (width of west facade along Barry St)
LEN_EW  = 4.0   # E-W depth,  m  (apartment depth)
HEIGHT  = 2.7   # ceiling height, m  (higher than standard 2.4 m)

FLOOR_AREA = LEN_NS * LEN_EW   # 20.0 m²
VOLUME     = FLOOR_AREA * HEIGHT  # 54.0 m³

A_WEST_GROSS  = LEN_NS * HEIGHT   # 13.5 m²  EXTERIOR — Barry St, has windows
A_EAST_GROSS  = LEN_NS * HEIGHT   # 13.5 m²  interior — to corridor
A_NORTH_GROSS = LEN_EW * HEIGHT   # 10.8 m²  interior — to Apt 306
A_SOUTH_GROSS = LEN_EW * HEIGHT   # 10.8 m²  interior — to Apt 304

# Two horizontal-slider windows on the WEST wall
# Sized from exterior photo: each pane ~1.5 m wide x 1.1 m high -> 1.65 m² each
# Total glazing 3.30 m² = 24 % of 13.5 m² west facade (prev. 0.9x0.9 was 12 %)
WIN_WIDTH_FIXED,    WIN_HEIGHT_FIXED    = 1.5, 1.1
WIN_WIDTH_OPERABLE, WIN_HEIGHT_OPERABLE = 1.5, 1.1

A_WINDOW_FIXED    = WIN_WIDTH_FIXED * WIN_HEIGHT_FIXED         # 1.65 m²
A_WINDOW_OPERABLE = WIN_WIDTH_OPERABLE * WIN_HEIGHT_OPERABLE   # 1.65 m²
A_WINDOW_TOTAL    = A_WINDOW_FIXED + A_WINDOW_OPERABLE         # 3.30 m²

A_WEST_OPAQUE = A_WEST_GROSS - A_WINDOW_TOTAL  # 10.20 m²

# EPW weather file path — update to match your local path
EPW_PATH = r"C:\Users\prakh\OneDrive\Desktop\ISO 52016-1\pybuildinenergy_AIB\pyBuildingEnergy\tests\AUS_VIC.Melbourne_IWEC.epw"


@pytest.fixture
def building_data():
    _lat = -37.800
    _lon = 144.968
    _sp  = get_ncc_setpoints(lat=_lat, lon=_lon)
    _single_cooling = (_sp["cooling_setpoint_bedroom"] + _sp["cooling_setpoint_living"]) / 2.0

    return {
        "building": {
            "name": "Apt_305_50_Barry_St_Carlton",
            "azimuth_relative_to_true_north": 270,
            "latitude":  _lat,
            "longitude": _lon,
            "exposed_perimeter": 18,
            "height": HEIGHT,
            "wall_thickness": 0.20,
            "n_floors": 1,
            "building_type_class": "Residential_apartment",
            # adj_zones_present=False: neighbouring apartments are conditioned
            # at the same setpoint — net heat transfer ~0, modelled as adiabatic
            "adj_zones_present": False,
            "number_adj_zone": 0,
            "net_floor_area": FLOOR_AREA,
            "construction_class": "class_iii",
        },

        "adjacent_zones": [
            {   # Apt 405 — studio above
                "name": "apt_above",
                "orientation_zone": {"azimuth": 270.0},
                "area_facade_elements":     np.array([A_WEST_GROSS, A_NORTH_GROSS, A_EAST_GROSS, A_SOUTH_GROSS, FLOOR_AREA, FLOOR_AREA]),
                "typology_elements":        np.array(["OP", "OP", "OP", "OP", "OP", "OP"]),
                "transmittance_U_elements": np.array([U_EXT_WALL, U_INT_WALL, U_INT_WALL, U_INT_WALL, U_INT_SLAB, U_INT_SLAB]),
                "orientation_elements":     np.array(["WV", "NV", "EV", "SV", "HOR", "HOR"]),
                "volume": VOLUME,
                "building_type_class": "Residential_apartment",
                "a_use": FLOOR_AREA,
            },
            {   # Apt 205 — studio below
                "name": "apt_below",
                "orientation_zone": {"azimuth": 270.0},
                "area_facade_elements":     np.array([A_WEST_GROSS, A_NORTH_GROSS, A_EAST_GROSS, A_SOUTH_GROSS, FLOOR_AREA, FLOOR_AREA]),
                "typology_elements":        np.array(["OP", "OP", "OP", "OP", "OP", "OP"]),
                "transmittance_U_elements": np.array([U_EXT_WALL, U_INT_WALL, U_INT_WALL, U_INT_WALL, U_INT_SLAB, U_INT_SLAB]),
                "orientation_elements":     np.array(["WV", "NV", "EV", "SV", "HOR", "HOR"]),
                "volume": VOLUME,
                "building_type_class": "Residential_apartment",
                "a_use": FLOOR_AREA,
            },
            {   # Apt 306 — studio to the NORTH
                "name": "apt_north",
                "orientation_zone": {"azimuth": 0.0},
                "area_facade_elements":     np.array([A_WEST_GROSS, A_NORTH_GROSS, A_EAST_GROSS, A_SOUTH_GROSS, FLOOR_AREA, FLOOR_AREA]),
                "typology_elements":        np.array(["OP", "OP", "OP", "OP", "OP", "OP"]),
                "transmittance_U_elements": np.array([U_INT_WALL, U_INT_WALL, U_INT_WALL, U_INT_WALL, U_INT_SLAB, U_INT_SLAB]),
                "orientation_elements":     np.array(["WV", "NV", "EV", "SV", "HOR", "HOR"]),
                "volume": VOLUME,
                "building_type_class": "Residential_apartment",
                "a_use": FLOOR_AREA,
            },
            {   # Apt 304 — studio to the SOUTH
                "name": "apt_south",
                "orientation_zone": {"azimuth": 180.0},
                "area_facade_elements":     np.array([A_WEST_GROSS, A_NORTH_GROSS, A_EAST_GROSS, A_SOUTH_GROSS, FLOOR_AREA, FLOOR_AREA]),
                "typology_elements":        np.array(["OP", "OP", "OP", "OP", "OP", "OP"]),
                "transmittance_U_elements": np.array([U_INT_WALL, U_INT_WALL, U_INT_WALL, U_INT_WALL, U_INT_SLAB, U_INT_SLAB]),
                "orientation_elements":     np.array(["WV", "NV", "EV", "SV", "HOR", "HOR"]),
                "volume": VOLUME,
                "building_type_class": "Residential_apartment",
                "a_use": FLOOR_AREA,
            },
            {   # Corridor — runs along the east side of the floor plate
                "name": "corridor",
                "orientation_zone": {"azimuth": 90.0},
                "area_facade_elements":     np.array([81.0, 5.4, 81.0, 5.4, 60.0, 60.0]),
                "typology_elements":        np.array(["OP", "OP", "OP", "OP", "OP", "OP"]),
                "transmittance_U_elements": np.array([U_INT_WALL] * 6),
                "orientation_elements":     np.array(["WV", "NV", "EV", "SV", "HOR", "HOR"]),
                "volume": 162.0,
                "building_type_class": "Residential_apartment",
                "a_use": 60.0,
            },
        ],

        "building_surface": [
            # 1) WEST EXTERIOR WALL — opaque brick (Barry St facade)
            {
                "name": "West exterior wall (opaque)",
                "type": "opaque",
                "area": A_WEST_OPAQUE,
                "sky_view_factor": 0.5,
                "u_value": U_EXT_WALL,
                "solar_absorptance": ABS_EXT_WALL,
                "thermal_capacity": C_EXT_WALL,
                "orientation": {"azimuth": 270.0, "tilt": 90.0},
                "name_adj_zone": None,
                "height": HEIGHT,
                "length": LEN_NS,
            },
            # 2-6) INTERIOR SURFACES — neighbours conditioned at same setpoint,
            # net heat transfer ~0; U=0.001 keeps thermal mass in simulation.
            {
                "name": "North wall to Apt 306",
                "type": "opaque",
                "area": A_NORTH_GROSS,
                "sky_view_factor": 0.5,
                "u_value": 0.001,
                "solar_absorptance": ABS_INT,
                "thermal_capacity": C_INT_WALL,
                "orientation": {"azimuth": 0.0, "tilt": 90.0},
                "name_adj_zone": None,
                "height": HEIGHT,
                "length": LEN_EW,
            },
            {
                "name": "South wall to Apt 304",
                "type": "opaque",
                "area": A_SOUTH_GROSS,
                "sky_view_factor": 0.5,
                "u_value": 0.001,
                "solar_absorptance": ABS_INT,
                "thermal_capacity": C_INT_WALL,
                "orientation": {"azimuth": 180.0, "tilt": 90.0},
                "name_adj_zone": None,
                "height": HEIGHT,
                "length": LEN_EW,
            },
            {
                "name": "East wall to corridor",
                "type": "opaque",
                "area": A_EAST_GROSS,
                "sky_view_factor": 0.5,
                "u_value": 0.001,
                "solar_absorptance": ABS_INT,
                "thermal_capacity": C_INT_WALL,
                "orientation": {"azimuth": 90.0, "tilt": 90.0},
                "name_adj_zone": None,
                "height": HEIGHT,
                "length": LEN_NS,
            },
            {
                "name": "Floor to Apt 205",
                "type": "opaque",
                "area": FLOOR_AREA,
                "sky_view_factor": 0.5,
                "u_value": 0.001,
                "solar_absorptance": ABS_INT,
                "thermal_capacity": C_INT_SLAB,
                "orientation": {"azimuth": 0.0, "tilt": 0.0},
                "name_adj_zone": None,
                "height": LEN_NS,
                "length": LEN_EW,
            },
            {
                "name": "Ceiling to Apt 405",
                "type": "opaque",
                "area": FLOOR_AREA,
                "sky_view_factor": 0.5,
                "u_value": 0.001,
                "solar_absorptance": ABS_INT,
                "thermal_capacity": C_INT_SLAB,
                "orientation": {"azimuth": 0.0, "tilt": 0.0},
                "name_adj_zone": None,
                "height": LEN_NS,
                "length": LEN_EW,
            },
            # 7) WEST WINDOW — fixed left-hand pane (1.5 m x 1.1 m)
            {
                "name": "West window — fixed",
                "type": "transparent",
                "area": A_WINDOW_FIXED,
                "sky_view_factor": 0.5,
                "u_value": U_WINDOW,
                "solar_absorptance": 0.5,
                "thermal_capacity": C_WINDOW,
                "orientation": {"azimuth": 270.0, "tilt": 90.0},
                "name_adj_zone": None,
                "height": WIN_HEIGHT_FIXED,
                "g_value": G_WINDOW,
                "width": WIN_WIDTH_FIXED,
                "parapet": 1.0,
                "shading": True,
                "shading_type": "horizontal_overhang",
                "width_or_distance_of_shading_elements": 0.05,
                "overhang_proprieties": {"width_of_horizontal_overhangs": 0.25},
            },
            # 8) WEST WINDOW — operable horizontal slider (1.5 m x 1.1 m)
            {
                "name": "West window — operable",
                "type": "transparent",
                "area": A_WINDOW_OPERABLE,
                "sky_view_factor": 0.5,
                "u_value": U_WINDOW,
                "solar_absorptance": 0.5,
                "thermal_capacity": C_WINDOW,
                "orientation": {"azimuth": 270.0, "tilt": 90.0},
                "name_adj_zone": None,
                "height": WIN_HEIGHT_OPERABLE,
                "g_value": G_WINDOW,
                "width": WIN_WIDTH_OPERABLE,
                "parapet": 1.0,
                "shading": True,
                "shading_type": "horizontal_overhang",
                "width_or_distance_of_shading_elements": 0.05,
                "overhang_proprieties": {"width_of_horizontal_overhangs": 0.25},
            },
        ],

        "units": {
            "area": "m²",
            "u_value": "W/m²K",
            "thermal_capacity": "J/kgK",
            "azimuth": "degrees (0=N, 90=E, 180=S, 270=W)",
            "tilt": "degrees (0=horizontal, 90=vertical)",
            "internal_gain": "W/m²",
            "internal_gain_profile": "Normalized to 0-1",
            "HVAC_profile": "0: off, 1: on",
        },

        "building_parameters": {
            "temperature_setpoints": {
                "heating_setpoint": _sp["heating_setpoint"],
                "heating_setback":  _sp["heating_setback"],
                "cooling_setpoint": _single_cooling,
                "cooling_setback":  _sp["cooling_setback"],
                "ncc_zone":         _sp["ncc_zone"],
                "units": "°C",
            },
            "system_capacities": {
                "heating_capacity": 10_000_000.0,
                "cooling_capacity": 10_000_000.0,
                "units": "W",
            },
            "ventilation": {
                "ventilation_type": "occupancy",
                "flow_rate_per_person": 2.0,
                "custom_heat_transfer_coefficient_ventilation": 0.0,
                "weekday": [1.0] * 24,
                "weekend": [1.0] * 24,
            },
            "ventilation_profile": {
                "weekday": [1.0] * 24,
                "weekend": [1.0] * 24,
            },
            "airflow_rates": {
                "infiltration_rate": 1.0,
                "units": "ACH (air changes per hour)",
            },
            "internal_gains": [
                {
                    "name": "occupants",
                    # 1 person x ~80 W sensible / 20 m² = 4 W/m²
                    # (prev. 8 W/m² implied 2 persons for a single studio)
                    "full_load": 4.0,
                    #            0    1    2    3    4    5    6    7    8    9   10   11   12   13   14   15   16   17   18   19   20   21   22   23
                    "weekday": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.5, 0.4, 0.5, 0.5, 0.5, 0.4, 0.5, 0.5, 0.5, 0.5, 0.5, 1.0, 1.0, 1.0, 1.0],
                    "weekend": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.8, 0.7, 0.7, 0.7, 0.7, 0.5, 0.5, 0.7, 0.8, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
                },
                {
                    "name": "appliances",
                    # Student studio: laptop, TV, microwave, fridge ~140 W peak
                    # 140 W / 20 m² = 7 W/m²  (prev. 25 W/m² = 500 W — commercial level)
                    "full_load": 7.0,
                    "weekday": [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.2, 0.3, 0.2, 0.2, 0.2, 0.2, 0.3, 0.2, 0.2, 0.2, 0.2, 0.3, 0.3, 0.4, 1.0, 0.6, 0.4, 0.2],
                    "weekend": [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.2, 0.3, 0.4, 0.3, 0.3, 0.4, 0.3, 0.3, 0.3, 0.3, 0.4, 0.4, 0.5, 1.0, 0.6, 0.4, 0.2],
                },
                {
                    "name": "lighting",
                    "full_load": 3.0,
                    "weekday": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.3, 0.3, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.5, 0.8, 0.8, 0.8, 0.7, 0.4, 0.1],
                    "weekend": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.3, 0.3, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.3, 0.5, 0.8, 0.8, 0.8, 0.7, 0.4, 0.1],
                },
            ],
            "construction": {
                "wall_thickness": 0.20,
                "thermal_bridges": 1.5,
                "units": "m (thickness), W/mK (thermal bridges)",
            },
            "climate_parameters": {
                "coldest_month": 7,
                "units": "1-12 (January-December)",
            },
            "heating_profile": {
                "weekday": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 0.0],
                "weekend": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0],
            },
            "cooling_profile": {
                "weekday": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0],
                "weekend": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0],
            },
        },
    }


@pytest.fixture
def output_dir():
    test_output = os.path.join(_HERE, "output_305_unit")
    os.makedirs(test_output, exist_ok=True)
    return test_output


def test_import_package():
    import pybuildingenergy as pybui
    assert hasattr(pybui, "__version__")


@pytest.mark.parametrize("fix", [True, False])
def test_sanitize_and_validate_bui(building_data, fix):
    import pybuildingenergy as pybui
    bui_result, report = pybui.sanitize_and_validate_BUI(building_data, fix=fix)
    assert bui_result is not None
    assert isinstance(report, list)
    errors = [e for e in report if e["level"] == "ERROR"]
    assert len(errors) == 0, f"Errors found: {errors}"


def test_iso52016_calculation(building_data, output_dir):
    import pybuildingenergy as pybui

    _lat = building_data["building"]["latitude"]
    _lon = building_data["building"]["longitude"]

    bui_checked, issues = pybui.sanitize_and_validate_BUI(building_data, fix=True)
    errors = [e for e in issues if e["level"] == "ERROR"]
    assert len(errors) == 0, f"Errors in data validation: {errors}"

    use_epw = os.path.isfile(EPW_PATH)
    sim_kwargs = dict(
        weather_source="epw" if use_epw else "pvgis",
        path_weather_file=EPW_PATH if use_epw else None,
        occupants_schedule_workdays=bui_checked["building_parameters"]["internal_gains"][0]["weekday"],
        occupants_schedule_weekend=bui_checked["building_parameters"]["internal_gains"][0]["weekend"],
        appliances_schedule_workdays=bui_checked["building_parameters"]["internal_gains"][1]["weekday"],
        appliances_schedule_weekend=bui_checked["building_parameters"]["internal_gains"][1]["weekend"],
        lighting_schedule_workdays=bui_checked["building_parameters"]["internal_gains"][2]["weekday"],
        lighting_schedule_weekend=bui_checked["building_parameters"]["internal_gains"][2]["weekend"],
    )

    hourly_sim, annual_results_df, sankey_data = pybui.ISO52016.Temperature_and_Energy_needs_calculation(
        bui_checked, **sim_kwargs
    )

    assert hourly_sim is not None
    assert annual_results_df is not None
    assert len(hourly_sim) > 0
    assert "x_air_in" in hourly_sim.columns, "Missing x_air_in — latent engine failed"
    assert "Q_Latent" in hourly_sim.columns, "Missing Q_Latent — latent engine failed"

    # ---- DHW calculation ------------------------------------------------
    building_area = building_data["building"]["net_floor_area"]
    year = 2009

    country_calendar = generate_calendar("Victoria", year)
    n_working    = int((country_calendar["values"] == "Working").sum())
    n_nonworking = int((country_calendar["values"] == "Non-Working").sum())
    n_holiday    = int((country_calendar["values"] == "Holiday").sum())
    total_days   = len(country_calendar)

    hourly_fractions = pd.DataFrame({
        "Workday": [0.01, 0.01, 0.01, 0.01, 0.01, 0.02,
                    0.04, 0.06, 0.06, 0.04, 0.03, 0.04,
                    0.05, 0.04, 0.03, 0.03, 0.04, 0.06,
                    0.07, 0.07, 0.06, 0.05, 0.04, 0.02],
        "Weekend": [0.01, 0.01, 0.01, 0.01, 0.01, 0.01,
                    0.02, 0.04, 0.06, 0.07, 0.07, 0.06,
                    0.06, 0.05, 0.05, 0.04, 0.04, 0.05,
                    0.06, 0.06, 0.05, 0.04, 0.03, 0.02],
        "Holiday": [0.01, 0.01, 0.01, 0.01, 0.01, 0.01,
                    0.02, 0.04, 0.06, 0.07, 0.07, 0.06,
                    0.06, 0.05, 0.05, 0.04, 0.04, 0.05,
                    0.06, 0.06, 0.05, 0.04, 0.03, 0.02],
    })
    sum_fractions = pd.DataFrame(hourly_fractions.sum(), columns=["fractions"])

    (
        yearly_cons,
        V_W_nd_d,
        monthly_volume,
        yearly_volume,
        Q_W_nd_d,
        V_W_nd_h_i,
        daily_cons_volume,
        daily_cons_energy,
    ) = Volume_and_energy_DHW_calculation(
        n_workdays           = n_working,
        n_weekends           = n_nonworking,
        n_holidays           = n_holiday,
        sum_fractions        = sum_fractions,
        total_days           = total_days,
        hourly_fractions     = hourly_fractions,
        teta_W_draw          = 40.0,
        teta_w_c_ref         = 10.0,
        teta_w_h_ref         = 60.0,
        teta_W_cold          = 10.0,
        mode_calc            = "number_of_units",
        building_type_B3     = None,
        building_area        = building_area,
        unit_count           = 1,   # single studio — prev. 2 doubled DHW to 89 L/day
        building_type_B5     = "Dwelling",
        residential_typology = "apartments_dwellings - AVG",
        calculation_method   = "correlation",
        year                 = year,
        country_calendar     = country_calendar,
    )

    Q_DHW_annual_kWh = float(yearly_cons)
    Q_DHW_annual_Wh  = Q_DHW_annual_kWh * 1000.0

    Q_H_annual      = float(annual_results_df["Q_H_annual"].iloc[0])
    Q_C_annual      = float(annual_results_df["Q_C_annual"].iloc[0])
    Q_Latent_annual = float(hourly_sim["Q_Latent"].iloc[-8760:].sum())
    Q_total         = Q_H_annual + Q_C_annual + Q_DHW_annual_Wh + Q_Latent_annual

    assert Q_DHW_annual_Wh  > 0, "DHW yearly energy should be positive"
    assert yearly_volume     > 0, "DHW yearly volume should be positive"
    assert Q_Latent_annual  >= 0, "Latent annual should be non-negative"

    annual_results_df["Q_H_annual_kWh"]      = Q_H_annual / 1000.0
    annual_results_df["Q_C_annual_kWh"]      = Q_C_annual / 1000.0
    annual_results_df["Q_DHW_annual_kWh"]    = Q_DHW_annual_kWh
    annual_results_df["Q_Latent_annual_kWh"] = Q_Latent_annual / 1000.0
    annual_results_df["Q_total_annual_kWh"]  = Q_total / 1000.0

    diff = len(hourly_sim) - len(daily_cons_energy)
    if diff > 0:
        dhw_energy_padded = daily_cons_energy[-diff:] + daily_cons_energy
        dhw_volume_padded = daily_cons_volume[-diff:] + daily_cons_volume
    else:
        dhw_energy_padded = daily_cons_energy
        dhw_volume_padded = daily_cons_volume

    hourly_sim["Q_DHW_Wh"] = dhw_energy_padded
    hourly_sim["V_DHW_m3"] = dhw_volume_padded

    hourly_sim_path  = os.path.join(output_dir, "hourly_sim_305.csv")
    annual_sim_path  = os.path.join(output_dir, "annual_results_305.csv")

    hourly_sim.to_csv(hourly_sim_path)
    annual_results_df.to_csv(annual_sim_path)

    assert os.path.exists(hourly_sim_path)
    assert os.path.exists(annual_sim_path)

    sp   = bui_checked["building_parameters"]["temperature_setpoints"]
    ncc  = sp.get("ncc_zone", "N/A")
    t_h  = sp.get("heating_setpoint", "N/A")
    t_hb = sp.get("heating_setback",  "N/A")
    t_c  = sp.get("cooling_setpoint", "N/A")
    t_cb = sp.get("cooling_setback",  "N/A")

    Q_H_peak_W = float(hourly_sim["Q_H"].max())  if "Q_H" in hourly_sim.columns else float("nan")
    Q_C_peak_W = float(hourly_sim["Q_C"].max())  if "Q_C" in hourly_sim.columns else float("nan")
    T_max      = float(hourly_sim["T_op"].max()) if "T_op" in hourly_sim.columns else float("nan")
    T_min      = float(hourly_sim["T_op"].min()) if "T_op" in hourly_sim.columns else float("nan")

    sep = "=" * 52

    print(f"\n{sep}")
    print(f"  APT 305 — 50 Barry St Carlton  |  ISO 52016-1")
    print(sep)

    print(f"\n  BUILDING")
    print(f"    Floor area          : {FLOOR_AREA:6.1f} m²")
    print(f"    Volume              : {VOLUME:6.1f} m³")
    print(f"    NCC climate zone    : {ncc}")
    print(f"    Location            : {_lat:.3f}°, {_lon:.3f}°")
    print(f"    Weather source      : {'EPW' if use_epw else 'PVGIS'}")

    print(f"\n  GLAZING")
    print(f"    West window (x2)    : {WIN_WIDTH_FIXED:.1f} m x {WIN_HEIGHT_FIXED:.1f} m = {A_WINDOW_TOTAL:.2f} m² total")
    print(f"    WWR (west facade)   : {A_WINDOW_TOTAL/A_WEST_GROSS*100:.0f} %")

    print(f"\n  SETPOINTS")
    print(f"    Heating setpoint    : {t_h} °C")
    print(f"    Heating setback     : {t_hb} °C")
    print(f"    Cooling setpoint    : {t_c} °C")
    print(f"    Cooling setback     : {t_cb} °C")

    print(f"\n  ANNUAL ENERGY DEMAND")
    print(f"    {'Item':<28} {'kWh/yr':>8}  {'kWh/m2·yr':>10}")
    print(f"    {'-'*48}")
    print(f"    {'Space heating':<28} {Q_H_annual/1000:>8.1f}  {Q_H_annual/1000/FLOOR_AREA:>10.1f}")
    print(f"    {'Space cooling':<28} {Q_C_annual/1000:>8.1f}  {Q_C_annual/1000/FLOOR_AREA:>10.1f}")
    print(f"    {'Latent (dehumid.) load':<28} {Q_Latent_annual/1000:>8.1f}  {Q_Latent_annual/1000/FLOOR_AREA:>10.1f}")
    print(f"    {'Domestic hot water':<28} {Q_DHW_annual_kWh:>8.1f}  {Q_DHW_annual_kWh/FLOOR_AREA:>10.1f}")
    print(f"    {'-'*48}")
    print(f"    {'TOTAL':<28} {Q_total/1000:>8.1f}  {Q_total/1000/FLOOR_AREA:>10.1f}")

    print(f"\n  PEAK LOADS")
    print(f"    Peak heating power  : {Q_H_peak_W/1000:6.2f} kW  ({Q_H_peak_W/FLOOR_AREA:.0f} W/m²)")
    print(f"    Peak cooling power  : {Q_C_peak_W/1000:6.2f} kW  ({Q_C_peak_W/FLOOR_AREA:.0f} W/m²)")

    print(f"\n  OPERATIVE TEMPERATURE RANGE")
    print(f"    Max (free-running)  : {T_max:6.1f} °C")
    print(f"    Min (free-running)  : {T_min:6.1f} °C")

    print(f"\n  DOMESTIC HOT WATER")
    print(f"    Annual energy       : {Q_DHW_annual_kWh:6.1f} kWh/yr")
    print(f"    Annual volume       : {yearly_volume*1000:6.0f} L/yr  ({yearly_volume*1000/365:.1f} L/day avg)")

    print(f"\n  OUTPUT FILES")
    print(f"    Hourly results      : {hourly_sim_path}")
    print(f"    Annual results      : {annual_sim_path}")
    print(f"\n{sep}\n")
