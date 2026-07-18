# `comparison_pybuildingenergy_vs_pybuildingenergyau.ipynb`

A three-way validation notebook: it runs the **same apartment** through the **official PyPI `pybuildingenergy` package**, this repo's **modified AIB fork**, and **EnergyPlus 24.1.0**, then compares annual heating/cooling demand and runs a small validation suite (determinism, energy balance, limit behaviour, seasonal pattern) against all three.

## Case study building

**Apt 305, 50 Barry St, Carlton VIC** — a 20 m² studio apartment (5.0 m × 4.0 m × 2.7 m), west-facing, surrounded by 5 conditioned neighbours (above, below, north, south, corridor to the east), built to Australian BCA 2006 minimum-spec construction:

| Parameter | Value |
|---|---|
| Location | lat −37.800, lon 144.968 (Melbourne, Southern Hemisphere) |
| Exterior wall U-value | 1.00 W/m²K (brick veneer, R1.0 insulation) |
| Interior partition U-value | 2.50 W/m²K (concrete block + plasterboard, no insulation) |
| Interior slab U-value | 1.80 W/m²K |
| Window | 5.40 W/m²K, SHGC 0.65, 1.62 m² total, west-facing |
| Thermal mass | **Zeroed** (C = 0 J/m²K) for all elements — an engine-method-only comparison, not a thermal-mass comparison |
| Internal gains | 2 occupants (8.0 W/m²), appliances (5.0 W/m²), lighting (3.0 W/m²) |
| Ventilation | 2.0 l/(s·m²) |
| HVAC | Ideal, unlimited-capacity heating/cooling |

## The three engines compared

| # | Engine | Source |
|---|---|---|
| 1 | **Original pyBuildingEnergy** | Installed fresh via `pip install pybuildingenergy` (official PyPI release) |
| 2 | **Modified AIB fork** | Read directly from this repo's `pyBuildingEnergy/src/` (clones the repo if not already checked out) |
| 3 | **EnergyPlus 24.1.0** | Downloaded/extracted from the official NREL release (~150 MB), driven via a hand-built IDF mirroring the same building dictionary |

All three are driven from a **single shared `build_bui()` function** so geometry, construction, internal gains, and (as far as each engine allows) setpoints are identical across engines — the notebook's stated goal is to isolate genuine *engine/methodology* differences from *input* differences.

> **Methodology note the notebook itself calls out:** EnergyPlus uses a full heat-balance engine (CTF conduction + combined radiative-convective surface balances); both ISO 52016 engines use the simplified 5R1C RC-network from ISO 52016-1. Results are expected to differ even with identical inputs — that gap is itself one of the things this notebook is measuring.

## Notebook structure

| Cells | Section | What it does |
|---|---|---|
| 0 | Setup | `pip install pybuildingenergy` (original engine); clones/locates this repo's fork source; sets `WEATHER_SOURCE = "pvgis"` (same TMY source for all engines) |
| 1 | `build_bui()` | The single building-dictionary builder shared by all three engines |
| 2 | Engine 1 run | Validates + runs the **original** PyPI engine, prints heating/cooling need |
| 3–4 | Engine 2 run | Purges cached `pybuildingenergy` modules so imports re-resolve to the fork; fetches NCC (National Construction Code) climate-zone setpoints for reference; validates + runs the **modified fork** |
| 5–6 | Comparison (2 engines) | Builds `comparison_df`, bar chart, saves CSV |
| 7–8 | **§6 What exactly is different** | An explicit, itemised table of every behavioural difference observed between the original and fork engines (see below) |
| 9 | **§7 EnergyPlus intro** | Explains the IdealLoadsAirSystem / NoMass / fixed-neighbour-temperature choices made for the EnergyPlus model |
| 10–13 | EnergyPlus run | Downloads EnergyPlus + a PVGIS-derived EPW, builds the IDF (schedules, geometry, HVAC), runs it, parses annual heating/cooling from the `.eso` output |
| 14 | Comparison (3 engines) | Extends `comparison_df` to all three engines, bar chart with value labels, saves CSV |
| 15–18 | **Validation suite V1–V5** | Automated checks (below) |
| 19 | *(empty)* | — |
| 20–21 | **§9 Monthly chart** | Interactive pyecharts grouped bar chart: monthly `Q_H`/`Q_C` for ISO 52016 (original) vs EnergyPlus |
| 22–23 | **Full Parameter Report** | Two side-by-side tables: inputs identical across all three engines, and engine-specific/methodological parameters that differ by design |

## Key result: three-engine annual comparison

From the notebook's last saved run:

| Engine | Setpoints | Heating (kWh/yr) | Cooling (kWh/yr) | Heating (kWh/m²/yr) | Cooling (kWh/m²/yr) |
|---|---|---:|---:|---:|---:|
| Original pyBuildingEnergy (PyPI) | Fixed 18 °C / 26 °C | 0.0 | 2,572.0 | 0.0 | 128.6 |
| Modified AIB fork | NCC zone 6 (20.0 °C / 26.0 °C) | 157.8 | 1,277.6 | 7.9 | 63.9 |
| EnergyPlus 24.1.0 | 18 °C / 26 °C (DualSetpoint) | 0.0 | 74.5 | 0.0 | 3.7 |

The headline pattern: **both ISO 52016 engines report far more cooling demand than EnergyPlus**, and the fork roughly halves the original engine's cooling estimate (2,572 → 1,278 kWh/yr) — consistent with the fork's ISO 13370 partition-wall fix removing a large, spurious "ground-adjacent" U-value correction that the original engine was wrongly applying to interior party walls (see below). EnergyPlus's much lower cooling number reflects the full heat-balance vs. simplified-RC methodology gap the notebook flags up front, not a bug in either ISO 52016 engine.

> **⚠️ Setpoint caveat in this saved run:** the notebook's *current* Cell 3 source overrides the fork's setpoints to match Engine 1 & 3 exactly (18 °C / 15 °C / 26 °C / 28 °C) for a fair comparison, explicitly calling the NCC auto-derivation "for reference only — NOT applied." But the **saved output** above still shows `"NCC zone 6 (20.0C / 26.0C)"` — i.e. it was captured from an *earlier* run, before that override was added to the code. The comparison table is not stale in terms of code correctness, just in terms of which setpoint policy was active; re-running the notebook end-to-end would be needed to get numbers under the current identical-setpoints logic.

## §6 — What exactly is different between the two ISO 52016 engines

The notebook's own itemised diff (`differences` table, cell 8), reproduced here:

| Area | Original engine (PyPI) | Modified engine (AIB fork) |
|---|---|---|
| Heating/cooling setpoints | Fixed values from the BUI dict (18 °C / 26 °C) | *(current code)* Explicitly overridden to match Engine 1 & 3; NCC auto-derivation computed for reference only, not applied |
| Interior wall U-values (ISO 13370) | Interior partition walls (sky_view_factor = 0) get their U-value overwritten by the basement-wall ground-coupling correction | **Fix applied**: surfaces with a `name_adj_zone` are recognised as interior partitions, not ground-contact elements, and are excluded from the correction — U-values stay at the supplied 2.50 / 1.80 W/m²K |
| Weather source | PVGIS TMY (same as fork, in this notebook) | PVGIS TMY here; the fork's own unit test instead defaults to a hardcoded local Sydney EPW |
| Schedule injection | Only via the BUI dict's `internal_gains` block | Same, plus optional explicit `*_schedule_workdays`/`*_schedule_weekend` keyword overrides |
| Latent heat / humidity | None — `Q_HC` (sensible only) | Adds `Q_Latent` and `x_air_in` (indoor moisture ratio) columns |
| Domestic hot water | Not part of the main calculation; separate function call needed | Same separate function, but combined into a single annual total in the fork's tests |
| Return signature | 2-tuple: `(hourly_sim, annual_results_df)` | 3-tuple: `(hourly_sim, annual_results_df, sankey_data)` |
| Validation messages | Partly in Italian (e.g. `"exposed_perimeter era 0; impostato a 1.0"`) | Equivalent messages in English |

## Validation suite (V1–V5)

| Check | What it tests | Result (last saved run) |
|---|---|---|
| **V1 — Determinism** | Same input run twice must give bit-exact output | ✅ PASS for all three engines |
| **V2 — Annual energy balance** | `Q_HC ≈ Q_tr + Q_ve − Q_sol − Q_int` | Skipped for both ISO engines — neither exposes transmission/ventilation/solar/internal components in a directly summable form (`hourly_sim` only has `T_op`/`T_ext`/`Q_H`/`Q_C`; the fork's Sankey dict uses different key names than the check expects) |
| **V3 — Near-zero insulation + zero gains** | Demand should drop >90%, driven only by ventilation losses | ❌ for all three: Original −69.4%, AIB fork −25.7%, EnergyPlus −951% (i.e. demand *rose* — the V3 IDF patch didn't zero the window U-value correctly in the regex substitution). The final conservation check (ventilation-only loss ≈ 781 kWh/yr, estimated vs. EnergyPlus's 783.4 kWh/yr) does line up well, suggesting the *magnitude* is broadly right even though the percentage-drop framing fails |
| **V4 — Zero internal gains, normal insulation** | Cooling should drop, heating may rise slightly | Descriptive only in the saved output (no pass/fail printed) — Original 0→2,572 kWh unchanged (gains removal didn't reduce cooling in this run), AIB fork 157.8→132.8 kWh heating / 1,277.6→920.1 kWh cooling, EnergyPlus 0→0 kWh heating / 74.5→8.5 kWh cooling |
| **V5 — Seasonal pattern** (Melbourne: heating should peak Jun–Aug, cooling Dec–Feb) | ❌ Original: heating peaks Jan (should be winter), cooling peaks Mar (should be summer). ❌ AIB fork: heating peaks Sep, cooling peaks Mar. Only EnergyPlus's cooling peak (Jan) is correct — its heating peak (Jan) is not. |

**V5 is the most important finding in this notebook**: at the time this notebook was run, *none* of the three engines reliably showed Melbourne's expected Southern-Hemisphere seasonal pattern, and the two ISO 52016 engines were worst-affected. This is consistent with — and predates — the later fix in this fork's engine (`ENGINE_CHANGES.md`, Stage 3 item 1) that made the "coldest month" hemisphere-aware (previously hardcoded to January, correct only for the Northern Hemisphere) instead of latitude-derived. A re-run of this notebook against the current engine state would be needed to confirm whether V5 now passes for the AIB fork.

## §9 — Monthly consumption chart

An interactive pyecharts grouped bar chart (`Q_H` vs `Q_C`, ISO 52016-original vs EnergyPlus, one bar pair per month) with a toolbox (save/restore/data-view/switch line↔bar) and a zoom slider. Built from the same monthly-aggregation helpers used by the V5 check.

## Full Parameter Report (cells 22–23)

Two tables printed at the very end, useful as a build-config audit trail:

1. **Shared inputs** — location, geometry, envelope U-values/absorptance, zeroed thermal mass, setpoints, internal gains, ventilation rate, HVAC capacity — confirmed identical (or equivalent-by-construction, e.g. EnergyPlus's `Material:NoMass`) across all three engines.
2. **Engine-specific parameters** — simulation method (5R1C RC-network vs. full CTF heat balance), time step (hourly vs. 10-minute for EnergyPlus), thermal bridge handling, latent/humidity output availability, DHW integration, Sankey data, adjacent-zone temperature treatment (`ISO 13789 b_ztu` computed vs. EnergyPlus's fixed 21 °C `OtherSideCoefficients`), the ISO 13370 correction status, and weather fetch mechanism.

## Requirements to re-run

- Network access to PyPI (`pip install pybuildingenergy`), PVGIS (`re.jrc.ec.europa.eu`, for both the TMY weather data and the EnergyPlus EPW conversion), and GitHub (to clone this repo if not already checked out).
- ~150 MB download for EnergyPlus 24.1.0 (cached at `/opt/energyplus` / `/content/` — the notebook skips re-downloading if already present).
- Designed for Google Colab (paths like `/content/...`, `!pip install` cells) but falls back to a local repo checkout if `pyBuildingEnergy/src` already exists relative to the working directory.
- Full run time: the ISO 52016 engines each simulate 9,504 hourly timesteps (a full year plus a December warm-up month); each engine run takes roughly 1.5–2.5 minutes, and the validation suite re-runs several of them multiple times, so a full end-to-end execution takes on the order of 15–20 minutes.
