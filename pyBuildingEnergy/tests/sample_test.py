import os
import sys
import warnings
import numpy as np
import pandas as pd
import pytest

from climate_setpoints import get_ncc_setpoints, apply_setpoints_to_building

warnings.simplefilter(action='ignore', category=FutureWarning)
pd.options.mode.chained_assignment = None

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pybuildingenergy.source.utils import ISO52016
from pybuildingenergy.source.check_input import sanitize_and_validate_BUI
from pybuildingenergy.source.DHW import Volume_and_energy_DHW_calculation, generate_calendar

@pytest.fixture
def building_data():
    _lat = -37.8136
    _lon = 144.9695
    _sp = get_ncc_setpoints(lat=_lat, lon=_lon)
    _single_cooling = (_sp["cooling_setpoint_bedroom"] + _sp["cooling_setpoint_living"]) / 2.0

    return {
        "building": {
            "name": "ML_Target_Building_001",
            "azimuth_relative_to_true_north": 41.8,
            "latitude": _lat,
            "longitude": _lon,
            "exposed_perimeter": 40,
            "height": 3,
            "wall_thickness": 0.3,
            "n_floors": 1,
            "building_type_class": "Residential_apartment",
            "adj_zones_present": False,
            "number_adj_zone": 2,
            "net_floor_area": 100,
            "construction_class": "class_i"
        },
        "adjacent_zones": [
            {
                "name": "adj_1",
                "orientation_zone": {"azimuth": 0},
                "area_facade_elements": np.array([20, 60, 30, 30, 50, 50], dtype=object),
                "typology_elements": np.array(['OP', 'OP', 'OP', 'OP', 'GR', 'OP'], dtype=object),
                "transmittance_U_elements": np.array([0.8196721311475411, 0.8196721311475411, 0.8196721311475411, 0.8196721311475411, 0.5156683855612851, 1.162633192818565], dtype=object),
                "orientation_elements": np.array(['NV', 'SV', 'EV', 'WV', 'HOR', 'HOR'], dtype=object),
                'volume': 300,
                'building_type_class': 'Residential_apartment',
                'a_use': 50
            },
            {
                "name": "adj_2",
                "orientation_zone": {"azimuth": 180},
                "area_facade_elements": np.array([20, 60, 30, 30, 50, 50], dtype=object),
                "typology_elements": np.array(['OP', 'OP', 'OP', 'OP', 'GR', 'OP'], dtype=object),
                "transmittance_U_elements": np.array([0.8196721311475411, 0.8196721311475411, 0.8196721311475411, 0.8196721311475411, 0.5156683855612851, 1.162633192818565], dtype=object),
                "orientation_elements": np.array(['NV', 'SV', 'EV', 'WV', 'HOR', 'HOR'], dtype=object),
                'volume': 300,
                'building_type_class': 'Residential_apartment',
                'a_use': 50
            }
        ],
        "building_surface": [
            {
                "name": "Roof surface",
                "type": "opaque",
                "area": 130,
                "sky_view_factor": 1.0,
                "u_value": 2.2,
                "solar_absorptance": 0.4,
                "thermal_capacity": 741500.0,
                "orientation": {"azimuth": 0, "tilt": 0},
                "name_adj_zone": None
            },
            {
                "name": "Opaque north surface",
                "type": "opaque",
                "area": 30,
                "sky_view_factor": 0.0,
                "basement_depth": 2.5,
                "u_value": 1.4,
                "solar_absorptance": 0.4,
                "thermal_capacity": 1416240.0,
                "orientation": {"azimuth": 0, "tilt": 90},
                "name_adj_zone": "adj_1"
            },
            {
                "name": "Opaque south surface",
                "type": "opaque",
                "area": 30,
                "sky_view_factor": 0.5,
                "u_value": 1.4,
                "solar_absorptance": 0.4,
                "thermal_capacity": 1416240.0,
                "orientation": {"azimuth": 180, "tilt": 90},
                "name_adj_zone": "adj_2"
            },
            {
                "name": "Opaque east surface",
                "type": "opaque",
                "area": 30,
                "sky_view_factor": 0.5,
                "u_value": 1.2,
                "solar_absorptance": 0.6,
                "thermal_capacity": 1416240.0,
                "orientation": {"azimuth": 90, "tilt": 90},
                "name_adj_zone": None
            },
            {
                "name": "Opaque west surface",
                "type": "opaque",
                "area": 30,
                "sky_view_factor": 0.5,
                "u_value": 1.2,
                "solar_absorptance": 0.7,
                "thermal_capacity": 1416240.0,
                "orientation": {"azimuth": 270, "tilt": 90},
                "name_adj_zone": None
            },
            {
                "name": "Slab to ground",
                "type": "opaque",
                "area": 100,
                "sky_view_factor": 0.0,
                "u_value": 1.6,
                "solar_absorptance": 0.6,
                "thermal_capacity": 405801,
                "orientation": {"azimuth": 0, "tilt": 0},
                "name_adj_zone": None
            },
            {
                "name": "Transparent east surface",
                "type": "transparent",
                "area": 25,
                "sky_view_factor": 0.5,
                "u_value": 5,
                "g_value": 0.726,
                "height": 2,
                "width": 1,
                "parapet": 1.1,
                "orientation": {"azimuth": 90, "tilt": 90},
                "shading": False,
                "shading_type": "horizontal_overhang",
                "width_or_distance_of_shading_elements": 0.5,
                "overhang_proprieties": {"width_of_horizontal_overhangs": 1},
                "name_adj_zone": None
            },
            {
                "name": "Transparent west surface",
                "type": "transparent",
                "area": 25,
                "sky_view_factor": 0.5,
                "u_value": 5,
                "g_value": 0.726,
                "height": 2,
                "width": 1,
                "parapet": 1.1,
                "orientation": {"azimuth": 270, "tilt": 90},
                "shading": False,
                "shading_type": "horizontal_overhang",
                "width_or_distance_of_shading_elements": 0.5,
                "overhang_proprieties": {"width_of_horizontal_overhangs": 1},
                "name_adj_zone": None
            }
        ],
        "units": {
            "area": "m²",
            "u_value": "W/m²K",
            "thermal_capacity": "J/kgK",
            "azimuth": "degrees (0=N, 90=E, 180=S, 270=W)",
            "tilt": "degrees (0=horizontal, 90=vertical)",
            "internal_gain": "W/m²",
            "internal_gain_profile": "Normalized to 0-1",
            "HVAC_profile": "0: off, 1: on"
        },
        "building_parameters": {
            "temperature_setpoints": {
                "heating_setpoint": _sp["heating_setpoint"],
                "heating_setback":  _sp["heating_setback"],
                "cooling_setpoint": _single_cooling,
                "cooling_setback":  _sp["cooling_setback"],
                "ncc_zone":         _sp["ncc_zone"],
                "units": "°C"
            },
            "system_capacities": {
                "heating_capacity": 10000000.0,
                "cooling_capacity": 12000000.0,
                "units": "W"
            },
            "airflow_rates": {
                "infiltration_rate": 1.0,
                "units": "ACH (air changes per hour)"
            },
            "internal_gains": [
                {
                    "name": "occupants",
                    "full_load": 4.2,
                    "weekday": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.5, 0.5, 0.5, 0.1, 0.1, 0.1, 0.1, 0.2, 0.2, 0.2, 0.5, 0.5, 0.5, 0.8, 0.8, 0.8, 1.0, 1.0],
                    "weekend": [1.0, 1.0, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 1.0, 1.0]
                },
                {
                    "name": "appliances",
                    "full_load": 3,
                    "weekday": [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.7, 0.7, 0.5, 0.5, 0.6, 0.6, 0.6, 0.6, 0.5, 0.5, 0.7, 0.7, 0.8, 0.8, 0.8, 0.6, 0.6],
                    "weekend": [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.7, 0.7, 0.5, 0.5, 0.6, 0.6, 0.6, 0.6, 0.5, 0.5, 0.7, 0.7, 0.8, 0.8, 0.8, 0.6, 0.6],
                },
                {
                    "name": "lighting",
                    "full_load": 3,
                    "weekday": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.15, 0.15, 0.15, 0.15, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.15, 0.15],
                    "weekend": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.15, 0.15, 0.15, 0.15, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.15, 0.15],
                }
            ],
            "construction": {
                "wall_thickness": 0.3,
                "thermal_bridges": 2,
                "units": "m (for thickness), W/mK (for thermal bridges)"
            },
            "climate_parameters": {
                "coldest_month": 1,
                "units": "1-12 (January-December)"
            },
            "heating_profile": {
                "weekday": [0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0],
                "weekend": [0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0],
            },
            "cooling_profile": {
                "weekday": [0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0],
                "weekend": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0]
            },
            "ventilation": {
                "ventilation_type": "custom",
                "flow_rate_per_person": 0.005,
                "custom_heat_transfer_coefficient_ventilation": 2.0,
                "weekday": [1.0] * 24,
                "weekend": [1.0] * 24
            },
            "ventilation_profile": {
                "weekday": [1.0] * 24,
                "weekend": [1.0] * 24
            }
        }
    }

@pytest.fixture
def output_dir():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    test_output = os.path.join(current_dir, "output_test")
    
    if not os.path.exists(test_output):
        os.makedirs(test_output)
        
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

    bui_checked, issues = pybui.sanitize_and_validate_BUI(building_data, fix=True)
    errors = [e for e in issues if e["level"] == "ERROR"]
    assert len(errors) == 0, "Errors in data validation"

    hourly_sim, annual_results_df, sankey_data = pybui.ISO52016.Temperature_and_Energy_needs_calculation(
        bui_checked,
        weather_source="pvgis"
    )

    assert hourly_sim is not None
    assert annual_results_df is not None
    assert len(hourly_sim) > 0
    assert "x_air_in" in hourly_sim.columns, "Missing x_air_in column! Latent engine failed."
    assert "Q_Latent" in hourly_sim.columns, "Missing Q_Latent column! Latent engine failed."

    building_area = building_data["building"]["net_floor_area"]
    year = 2009

    country_calendar = generate_calendar("NSW", year)
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
        mode_calc            = "volume_type_bui",
        building_type_B3     = None,
        building_area        = building_area,
        unit_count           = 1,
        building_type_B5     = "Dwelling",
        residential_typology = "apartments_dwellings - AVG",
        calculation_method   = "correlation",
        year                 = year,
        country_calendar     = country_calendar,
    )

    Q_DHW_annual_Wh = float(yearly_cons)

    Q_H_annual = float(annual_results_df["Q_H_annual"].iloc[0])
    Q_C_annual = float(annual_results_df["Q_C_annual"].iloc[0])
    Q_total    = Q_H_annual + Q_C_annual + Q_DHW_annual_Wh

    assert Q_DHW_annual_Wh > 0, "DHW yearly energy should be positive"
    assert yearly_volume > 0,   "DHW yearly volume should be positive"

    annual_results_df["Q_H_annual_kWh"] = Q_H_annual / 1000.0
    annual_results_df["Q_C_annual_kWh"] = Q_C_annual / 1000.0
    annual_results_df["Q_DHW_annual_kWh"] = Q_DHW_annual_Wh / 1000.0
    annual_results_df["Q_total_annual_kWh"] = Q_total / 1000.0

    diff = len(hourly_sim) - len(daily_cons_energy)
    if diff > 0:
        dhw_energy_padded = daily_cons_energy[-diff:] + daily_cons_energy
        dhw_volume_padded = daily_cons_volume[-diff:] + daily_cons_volume
    else:
        dhw_energy_padded = daily_cons_energy
        dhw_volume_padded = daily_cons_volume

    hourly_sim["Q_DHW_Wh"] = dhw_energy_padded
    hourly_sim["V_DHW_m3"] = dhw_volume_padded

    hourly_sim_path = os.path.join(output_dir, "hourly_sim_test.csv")
    annual_sim_path = os.path.join(output_dir, "annual_results_test.csv")
    
    hourly_sim.to_csv(hourly_sim_path)
    annual_results_df.to_csv(annual_sim_path)

    assert os.path.exists(hourly_sim_path)
    assert os.path.exists(annual_sim_path)
    
    print("\nSETPOINTS USED IN SIMULATION:")
    print(bui_checked["building_parameters"]["temperature_setpoints"])