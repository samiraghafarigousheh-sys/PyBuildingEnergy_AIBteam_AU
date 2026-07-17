# Changes to the pyBuildingEnergy Engine

This document tracks the modifications made to the vendored [`pyBuildingEnergy`](https://pypi.org/project/pybuildingenergy/) source (`pyBuildingEnergy/src/pybuildingenergy/`) in this fork, relative to the original upstream package. It covers the ISO 52016 calculation engine (`source/utils.py`), the input validator (`source/check_input.py`), and the domestic hot water module (`source/DHW.py`).

The changes were made to fix bugs found while comparing this engine's output against EnergyPlus for an Australian apartment case study (305, 50 Barry St, Carlton VIC), where the engine was producing results that didn't line up with a detailed EnergyPlus reference model.

## `source/utils.py` — ISO 52016 engine

### 1. Ground-coupling wrongly applied to interior partition walls

The basement-wall U-value correction (ISO 13370 soil-adjustment) triggered for any vertical surface (`tilt == 90`) with `sky_view_factor == 0`. Interior partition walls facing a neighbouring apartment or corridor also have `sky_view_factor == 0` (they don't see the sky) but are **not** in contact with the ground, so they were incorrectly getting their U-value overwritten with a heavily-insulated "soil-adjusted" value.

**Fix:** surfaces that carry a `name_adj_zone` (i.e. they face a named adjacent zone) are now excluded from the ISO 13370 ground-contact correction. Their U-value stays as the user-supplied value (e.g. 2.50 W/m²K for a party wall) instead of being silently overwritten.

The same guard was applied to the ground-contact area search (`sog_area`) used elsewhere in the engine, so a partition wall can no longer be mistaken for a slab-on-grade surface either.

### 2. Azimuth convention — double-rotation risk

There was no documentation at the point where surface azimuths are assigned to explain that `surface["orientation"]["azimuth"]` is **absolute** (0°=N, 90°=E, 180°=S, 270°=W) while `building["azimuth_relative_to_true_north"]` is an **additive offset** applied on top of it at solar-calculation time. Setting both — i.e. supplying already-absolute surface azimuths *and* a non-zero building offset — silently double-rotates the building's orientation.

**Fix:** added an explicit comment at the point of use, and a corresponding validator warning (see `check_input.py` below) that fires when a non-zero `azimuth_relative_to_true_north` is combined with cardinal (0/90/180/270°) surface azimuths.

### 3. Latent load only handled dehumidification, not humidification

The HVAC latent-load balance only ever removed moisture (dehumidification) when indoor humidity rose above the comfort setpoint during cooling. It had no corresponding logic for adding moisture (humidification) when the indoor air dropped below the comfort setpoint during heating — so heating-season latent load was silently reported as zero.

**Fix:** extended the moisture mass balance with a second branch: when `x_air < x_min_setpoint` (≈0.004 kg/kg, ~20% RH at 20°C) and the system is heating, moisture is added back up to the setpoint, and the associated energy is included in `Q_Latent` the same way dehumidification already was.

### 4. No support for custom/extraction internal gains

The internal-gains calculation only recognised three hard-coded gain types: `occupants`, `appliances`, `lighting`. Any other entry in `building_parameters.internal_gains` (e.g. a process load, or an exhaust fan representing heat *extraction*) was silently ignored.

**Fix:** after the three standard gains are applied, any remaining `internal_gains` entry is now applied using its own hourly weekday/weekend schedule. A **negative** `full_load` value is treated as heat extraction (e.g. a bathroom/kitchen exhaust fan), letting it reduce rather than add to the internal gains for that hour.

### 5. Phantom heat loss through conditioned adjacent zones

The temperature of an unconditioned adjacent zone (`theta_ztu`) was always derived from the ISO 13789 `b_ztu` reduction-factor formula, which assumes the neighbouring space floats with outdoor conditions. If the adjacent zone was actually another **conditioned** unit (e.g. a heated/cooled neighbouring apartment), this formula still pulled its temperature partway toward the outdoor temperature, producing a fictitious heat loss through the party wall even though the real ΔT across it is close to zero.

**Fix:** added a `conditioned` flag to the adjacent-zone configuration. When `adj_zone["conditioned"] is True`, the zone temperature is taken directly from `adj_zone["setpoint"]` instead of running it through the `b_ztu` formula — eliminating the phantom heat loss for apartments surrounded by other conditioned units. This applies to both the single-adjacent-zone and multi-zone code paths.

### 6. Surface-level thermal bridges were ignored when exposed perimeter was zero

Thermal bridges were only calculated from the building's exposed perimeter (`psi_value * exposed_perimeter`), which is zero for a mid-floor apartment with no ground contact — even though it still has real thermal bridges at window frames and slab-edge junctions with neighbouring units.

**Fix:** added a surface-level thermal-bridge term, `Σ (psi_junction × length_junction + psi_frame × perimeter_frame)`, summed across `building_surface` and added into `thermal_bridge_heat`. This now contributes correctly regardless of whether the surface has any ground-exposed perimeter.

### 7. Silent schedule/weather hour-offset

If the internal-gains schedule DataFrame and the weather DataFrame started on different clock hours (e.g. one indexed from midnight, the other from 1am), all internal gain schedules would be silently offset by an hour relative to the weather data, with no indication anything was wrong.

**Fix:** added a runtime check comparing `profile_df.index[0].hour` to `sim_df.index[0].hour` and raising a `warnings.warn` if they differ, so a mismatched schedule/weather-year pairing is now visible instead of silently skewing results.

## `source/check_input.py` — input validator

Three new validator warnings were added to `sanitize_and_validate_BUI`, surfaced to the user before a simulation runs rather than discovered after the fact in the output:

- **Ventilation profile flat at 1.0** — warns when `ventilation_profile.weekday` is a constant `1.0` across all 24 hours, since this applies full mechanical/natural ventilation rate overnight and through winter, which is rarely the intended behaviour (background infiltration is usually closer to ~0.15).
- **Azimuth double-rotation risk** — warns when `azimuth_relative_to_true_north != 0` while surfaces already carry cardinal (0/90/180/270°) azimuths, flagging the double-rotation risk described in utils.py fix #2 above, and lists the affected surface names.
- **Zero surface thermal capacity vs. non-`class_i` construction class** — warns when every surface has `thermal_capacity == 0` but `building.construction_class` is not `class_i`. In that combination the internal zone capacitance is still derived from the (non-zero) construction class even though no surface actually carries thermal mass, which inflates the residual term in the energy-balance Sankey diagram.

## `source/DHW.py` — domestic hot water calendar lookup

`get_calendar_by_name()` originally fell back to a hard-coded dictionary of Australian state/territory `workalendar` calendars (`Australia`, `NSW`, `Victoria`, `Queensland`, `SA`, `WA`, `Tasmania`, `ACT`, `NT`) if the standard `workalendar.registry` lookup failed.

**Fix:** removed the Australia-specific fallback and reverted to using the standard `workalendar` country/subdivision registry lookup only, raising a clear `ValueError` if a name can't be resolved. This keeps the calendar resolution generic (matching upstream behaviour) instead of special-casing one country.

## Related fix: unit occupancy inputs (example script)

Separately, `tests/AIBpybuildingenergy_305_unit.py` (the Barry St case-study configuration, not the engine itself) had its occupant-dependent inputs corrected for a 2-person household:

- Occupants internal gain: `4 → 8 W/m²` (2 people × 80 W ÷ 20 m²)
- DHW `unit_count`: `1 → 2`

Window dimensions (1.5 × 1.1 m) and appliance gains (7 W/m²) from an earlier correction were retained.
