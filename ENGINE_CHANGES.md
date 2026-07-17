# Changes vs. the original pyBuildingEnergy repository

This document is a direct comparison between:

- **Upstream:** [`EURAC-EEBgroup/pyBuildingEnergy`](https://github.com/EURAC-EEBgroup/pyBuildingEnergy) (the original package)
- **This fork:** [`samiraghafarigousheh-sys/PyBuildingEnergy_AIBteam_AU`](https://github.com/samiraghafarigousheh-sys/PyBuildingEnergy_AIBteam_AU), specifically the vendored copy at `pyBuildingEnergy/`

## How the comparison was done

The vendored copy in this repo was checked out from upstream at version `2.0.3`, which corresponds to upstream commit [`9569b82`](https://github.com/EURAC-EEBgroup/pyBuildingEnergy/commit/9569b823cac4bcc50e8a3a40bd9188527748898a) ("update inputs file and fixing bug calculation options for ventilation", 2026‑01‑27). Diffing this repo's `pyBuildingEnergy/` against that exact upstream commit (rather than against upstream's current `master`, which has since moved on with unrelated features such as a full EN 15316 HVAC generation/distribution/emission suite and a ventilation-boundary rewrite) isolates only the changes actually made by this fork.

**Only three engine source files differ from upstream `2.0.3`:**

- `src/pybuildingenergy/source/utils.py` — the ISO 52016 calculation engine
- `src/pybuildingenergy/source/check_input.py` — the input validator
- `src/pybuildingenergy/source/DHW.py` — the domestic hot water calendar helper

Everything else in `src/pybuildingenergy/` (`__init__.py`, `global_inputs.py`, `pybuildingenergy.py`, `source/functions.py`, `source/generate_profile.py`, `source/graphs.py`, `source/iso_15316_1.py`, `source/ventilation.py`, `source/table_iso_16798_1.py`) is byte-for-byte identical to upstream `2.0.3`.

The changes were made while validating this engine's output against EnergyPlus for an Australian apartment case study (305, 50 Barry St, Carlton VIC) — a mid-floor apartment surrounded by other conditioned units — where several ISO 52016 assumptions baked into the original package (aimed mainly at detached, ground-contact, Northern-Hemisphere buildings) didn't hold and produced systematic errors against the EnergyPlus reference model.

## `source/utils.py` — ISO 52016 engine

### 1. Southern Hemisphere coldest-month was hardcoded to January

```python
# upstream
coldest_month = 1
building_object["building_parameters"]["coldest_month"] = coldest_month
```

The coldest month used for internal design-condition calculations was hardcoded to January, which is correct for the Northern Hemisphere but is midsummer in Australia.

**Fix:** the coldest month is now chosen from the building's latitude — July for latitude < 0 (Southern Hemisphere), January otherwise — and stored under `climate_parameters.coldest_month` instead of directly under `building_parameters`.

### 2. Ground-floor thermal resistance was a fixed constant, and missing R_si

```python
# upstream
thermal_resistance_floor = 5.3
equivalent_ground_thickness = wall_thickness + lambda_gr * (thermal_resistance_floor + R_se)
```

`Calculate_ground_floor` used a hardcoded `thermal_resistance_floor = 5.3 m²K/W` for every building regardless of the actual slab construction, and the ISO 13370 equivalent-thickness formula only added the external surface resistance (`R_se`), omitting the internal one (`R_si`).

**Fix:** the raw slab U-value is now looked up dynamically from the surface named `"Slab to ground"` in `building_surface` (falling back to 2.5 W/m²K if not found), and the floor resistance is derived from it: `Rf = 1/U_raw − R_si − R_se`. Both `R_si` and `R_se` are now included in the equivalent ground thickness calculation, matching the ISO 13370 definition.

### 3. Ground-coupling wrongly applied to interior partition walls

The basement-wall U-value correction (ISO 13370 soil-adjustment) triggered for any vertical surface (`tilt == 90`) with `sky_view_factor == 0`. Interior partition walls facing a neighbouring apartment or corridor also have `sky_view_factor == 0` (they don't see the sky) but are **not** in contact with the ground, so they were incorrectly getting their U-value overwritten with a heavily-insulated "soil-adjusted" value.

**Fix:** added `calc_basement_wall_u_value()` and excluded surfaces that carry a `name_adj_zone` (i.e. face a named adjacent zone) from the ISO 13370 correction — their U-value stays as the user-supplied value (e.g. 2.50 W/m²K for a party wall). The same guard was applied to the ground-contact area search (`sog_area`) used elsewhere in the engine.

### 4. Azimuth convention — double-rotation risk

There was no documentation at the point where surface azimuths are assigned to explain that `surface["orientation"]["azimuth"]` is **absolute** (0°=N, 90°=E, 180°=S, 270°=W) while `building["azimuth_relative_to_true_north"]` is an **additive offset** applied on top of it at solar-calculation time. Supplying already-absolute surface azimuths *and* a non-zero building offset silently double-rotates the building.

**Fix:** added an explicit comment at the point of use, and a corresponding validator warning (see `check_input.py` below).

### 5. Latent load only handled dehumidification, not humidification

The HVAC latent-load balance only ever removed moisture (dehumidification) when indoor humidity rose above the comfort setpoint during cooling; there was no corresponding humidification branch for when indoor air dropped below the comfort setpoint during heating, so heating-season latent load was always zero, and the engine had no humidity-ratio state at all.

**Fix:** added a full moisture mass-balance model:
- new helper `calc_humidity_ratio(T_db, RH, Patm)` converts temperature/RH to humidity ratio.
- new per-timestep state (`x_air_old`, zone air mass `M_air`) tracks indoor humidity ratio across the simulation.
- occupant moisture gains and ventilation moisture transport are now included each timestep.
- dehumidification (cooling, `x_air > 0.012 kg/kg`) and humidification (heating, `x_air < 0.004 kg/kg`) are both handled, each converted to a latent load in Watts.
- the hourly output DataFrame gained two new columns: `x_air_in` (indoor humidity ratio) and `Q_Latent` (latent load, W) alongside the existing `Q_HC`, `T_op`, `T_ext`.

### 6. No support for custom/extraction internal gains

The internal-gains calculation only recognised three hard-coded gain types: `occupants`, `appliances`, `lighting`. Any other entry in `building_parameters.internal_gains` (e.g. a process load, or an exhaust fan representing heat *extraction*) was silently ignored.

**Fix:** any additional `internal_gains` entry is now applied using its own hourly weekday/weekend schedule. A **negative** `full_load` value acts as heat extraction (e.g. a bathroom/kitchen exhaust fan) rather than a gain.

### 7. Phantom heat loss through conditioned adjacent zones

The temperature of an unconditioned adjacent zone (`theta_ztu`) was always derived from the ISO 13789 `b_ztu` reduction-factor formula, which assumes the neighbouring space floats with outdoor conditions. If the adjacent zone was actually another **conditioned** unit (a heated/cooled neighbouring apartment), this formula still pulled its temperature partway toward the outdoor temperature, producing a fictitious heat loss through the party wall even though the real ΔT across it is close to zero.

**Fix:** added a `conditioned` flag to the adjacent-zone configuration. When `adj_zone["conditioned"] is True`, the zone temperature is taken directly from `adj_zone["setpoint"]` instead of running it through the `b_ztu` formula. Applies to both the single- and multi-adjacent-zone code paths.

### 8. Surface-level thermal bridges were ignored when exposed perimeter was zero

Thermal bridges were only calculated from the building's exposed perimeter (`psi_value × exposed_perimeter`), which is zero for a mid-floor apartment with no ground contact — even though it still has real thermal bridges at window frames and slab-edge junctions with neighbouring units.

**Fix:** added a surface-level thermal-bridge term, `Σ (psi_junction × length_junction + psi_frame × perimeter_frame)`, summed across `building_surface` and added into `thermal_bridge_heat`. This now contributes correctly regardless of whether the surface has any ground-exposed perimeter.

### 9. Silent schedule/weather hour-offset

If the internal-gains schedule DataFrame and the weather DataFrame started on different clock hours (e.g. one indexed from midnight, the other from 1am), all internal gain schedules would be silently offset by an hour relative to the weather data, with no indication anything was wrong.

**Fix:** added a runtime check comparing `profile_df.index[0].hour` to `sim_df.index[0].hour` and raising a `warnings.warn` if they differ.

## `source/check_input.py` — input validator

Three new validator warnings were added to `sanitize_and_validate_BUI`, surfaced before a simulation runs rather than discovered after the fact in the output:

- **Ventilation profile flat at 1.0** — warns when `ventilation_profile.weekday` is a constant `1.0` across all 24 hours, since this applies full mechanical/natural ventilation rate overnight and through winter, which is rarely the intended behaviour (background infiltration is usually closer to ~0.15).
- **Azimuth double-rotation risk** — warns when `azimuth_relative_to_true_north != 0` while surfaces already carry cardinal (0/90/180/270°) azimuths, flagging the double-rotation risk described in utils.py fix #4 above, and lists the affected surface names.
- **Zero surface thermal capacity vs. non-`class_i` construction class** — warns when every surface has `thermal_capacity == 0` but `building.construction_class` is not `class_i`. In that combination the internal zone capacitance is still derived from the (non-zero) construction class even though no surface actually carries thermal mass, which inflates the residual term in the energy-balance Sankey diagram.

## `source/DHW.py` — domestic hot water calendar lookup

Upstream's `get_calendar_by_name(nation_name)` looked up a country in the `workalendar` registry, falling back to a small hard-coded map of Western-European countries (Italy, Germany, France, Spain, Austria, Switzerland) if the registry lookup failed.

**Fix:** the parameter was renamed to `location_name` (since state/territory names are also valid, not just countries), and the hard-coded fallback map was removed — a failed lookup now raises a clear `ValueError` directly. During development this fork temporarily carried an Australia-specific state/territory fallback map instead of the European one; that was subsequently removed in favour of relying purely on `workalendar`'s own registry (which already covers Australian states/territories), so no country/state is special-cased in the final version.

## Other differences

- **`pyproject.toml`** — `packaging` dependency pin loosened from `==25.0` to `>=23.2,<26` for broader environment compatibility (e.g. Google Colab).
- **`tests/test_general.py`** — the ventilation fixture used by one test was updated to the `type_ventilation` / `ventilation.ventilation_type` mechanical-ventilation config shape, and an assertion string was updated (`"Floor heating 1"` → `"Floor heating"`).
- **`src/pybuildingenergy/data/`** (upstream's built-in `building_archetype.py` / archetype JSON) is not present in this fork's vendored copy — it isn't used by the Barry St case study.
- **New case-study files** were added under `tests/`: `AIBpybuildingenergy_305_unit.py`, `climate_setpoints.py`, `sample.py`, `sample_test.py`, and `output_test/` — these configure and validate the Barry St, Carlton apartment model rather than changing the engine itself.

## Related: unit occupancy inputs (case-study config, not the engine)

`tests/AIBpybuildingenergy_305_unit.py` (the Barry St case-study configuration) had its occupant-dependent inputs corrected for a 2-person household:

- Occupants internal gain: `4 → 8 W/m²` (2 people × 80 W ÷ 20 m²)
- DHW `unit_count`: `1 → 2`

Window dimensions (1.5 × 1.1 m) and appliance gains (7 W/m²) from an earlier correction were retained.

## Note: upstream has moved on independently

Upstream `master` has continued to evolve since the `2.0.3` snapshot this fork is based on, adding a large EN 15316 HVAC generation/distribution/emission/storage suite (`heat_pump_15316_4_2.py`, `distribution_15316_3.py`, `emission_15316_2.py`, `cogeneration_15316_4_4.py`, etc.), an EN 16798‑5‑1 AHU/ventilation model, and a rewritten `S_ve`/`H_ve` ventilation-boundary formulation. None of that is present in this fork — it reflects upstream's independent development after this fork's snapshot, not something removed or reverted here.
