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

## 4.5 Validation checks

A suite of five automated checks (notebook cells 15–18) is applied to all three engines, both before and after the Stage 2 and Stage 3 engine modifications documented in `ENGINE_CHANGES.md`, using this comparison notebook as the execution framework. The purpose of the checks is twofold: to confirm internal consistency of each engine, and to identify which aspects of the discrepancy between the ISO engines and EnergyPlus are attributable to correctable defects rather than fundamental method-level differences.

**V1 — Determinism.** Each engine is executed twice on identical inputs and outputs compared for agreement. This verifies the absence of non-deterministic state and is a prerequisite for interpreting any subsequent difference as physically meaningful.

**V2 — Annual energy balance (Sankey closure).** For the pyBuildingEnergy engines, the Sankey decomposition is used to compute the closure residual across the main heat-transfer components: transmission losses, ventilation losses, cooling energy extracted, and change in thermal storage. A residual exceeding 5% identifies sub-models where energy is not conserved and directs further diagnostic investigation. This check is applied to the ISO engines only.

**V3 — Limit behaviour: near-perfect insulation and zero gains.** All U-values are set to 0.001 W/(m²K) and all internal gains removed. Total annual demand should fall by more than 90% relative to the baseline; the ventilation-only residual is cross-checked analytically (≈781 kWh/yr) against EnergyPlus's result of 783.4 kWh/yr.

**V4 — Limit behaviour: zero internal gains, normal insulation.** Internal gains are removed while insulation remains unchanged. Cooling demand is expected to fall substantially and heating demand to rise modestly, since internal gains are both the dominant summer load driver and a significant winter free-heating source.

**V5 — Seasonal pattern (Southern Hemisphere).** Monthly heating is expected to peak in June–August and monthly cooling in December–February. A reversed seasonal peak indicates an error in the solar position algorithm, the hemisphere convention, or the coldest-month parameter — making this the most diagnostically informative check for the Australian application context.

### Implementation status in this notebook

| Check | Implementation | Status |
|---|---|---|
| **V1** | Runs each ISO engine twice (`_run_orig`/`_run_mod`) and EnergyPlus twice (`_ep_run_and_parse`), compares with `np.array_equal` | ✅ Matches the specification above |
| **V2** | **Fixed.** Previously always printed "insufficient component data — skipping balance check" because the helper searched for flat keys (`Q_tr`, `Q_ve`, `Q_sol`, `Q_int`) that don't exist anywhere in this engine's actual return value. The real structure is `sankey_data = {"inputs": {...}, "outputs": {...}, "energy_accumulated_zone": ...}` (named entries like `"Heating"`, `"Internal gains"`, `"Ventilation (losses)"`, `"Transmission - <surface name>"`). Rewritten to consume that structure directly and apply the 5% threshold from the methodology above. One subtlety: the engine's own Sankey builder folds any unclosed balance into an explicit `"Transmission (residual)"` output bucket so the *diagram* visually balances — that bucket is excluded from the V2 closure sum, since it *is* the imbalance being measured (including it would make the residual trivially ~0% by construction). Scoped to the ISO engines only, per the methodology — EnergyPlus's HTML component-load report is a different decomposition, not a Sankey closure of the same input/output split, so the previous notebook's partial/fragile attempt to fold it into V2 was dropped rather than left half-working. | ✅ Fixed for the Modified AIB fork. Genuinely not applicable to the unmodified Original engine — its 2-tuple return has no Sankey data at all (Sankey output is itself one of this fork's additions), which V2 now reports explicitly instead of the previous vague message. |
| **V3 / V4** | `>90%` drop threshold (`drop_threshold=0.90`) and the analytical ventilation-loss cross-check are already implemented as specified | ✅ Matches the specification above |
| **V5** | Monthly chunking already implemented as specified; a separate root-cause bug (the prepended December warm-up month never being stripped from `hourly_sim`, silently shifting every monthly analysis forward by one month) was found and fixed — see `ENGINE_CHANGES.md`, Stage 3 item 10 | ✅ Matches the specification above, and no longer confounded by the warm-up-month shift |

### Result (last full notebook run)

| Check | Result |
|---|---|
| V1 | ✅ PASS for all three engines |
| V2 | Not run under the fixed implementation yet in a full Colab execution (this environment has no PVGIS/EnergyPlus network access to reproduce the Barry St case study end-to-end). The corrected logic was verified against a live run of the fork engine on a different, simpler building fixture in an offline sandbox test: it exactly reproduces the engine's own internal `SANKEY CHECK` console line (17.7% residual) instead of silently reporting "insufficient data" — i.e. it now correctly surfaces a real, pre-existing energy-balance gap in the fork's transmission/thermal-bridge accounting for diagnostic follow-up, which is precisely V2's stated purpose. A fresh full run of this notebook is needed for the Barry St-specific number. |
| V3 | ❌ for all three at the time of the last saved run: Original −69.4%, AIB fork −25.7%, EnergyPlus −951% (i.e. demand *rose* — the V3 IDF patch didn't zero the window U-value correctly in the regex substitution). The analytical cross-check (ventilation-only loss ≈ 781 kWh/yr vs. EnergyPlus's 783.4 kWh/yr) does line up well, suggesting the *magnitude* is broadly right even though the percentage-drop framing failed for that run. |
| V4 | Descriptive only in the saved output (no pass/fail printed) — Original 0→2,572 kWh unchanged (gains removal didn't reduce cooling in this run), AIB fork 157.8→132.8 kWh heating / 1,277.6→920.1 kWh cooling, EnergyPlus 0→0 kWh heating / 74.5→8.5 kWh cooling |
| V5 | At the time of the last saved run: ❌ Original (heating peaks Jan, should be winter; cooling peaks Mar, should be summer). ❌ AIB fork (heating peaks Sep; cooling peaks Mar). Only EnergyPlus's cooling peak (Jan) was correct — its heating peak (Jan) was not. This was **the most important finding** from this notebook: none of the three engines reliably showed Melbourne's expected Southern-Hemisphere seasonal pattern, and the two ISO 52016 engines were worst-affected — consistent with the warm-up-month shift bug above and the separate hemisphere-aware-coldest-month fix (`ENGINE_CHANGES.md`, Stage 3 item 1). A fresh full run is needed to confirm V5 now passes for the AIB fork with both fixes in place. |

## 4.6 Accuracy metrics

The methodology also defines a set of accuracy metrics (following Ballarini et al. [3] and ASHRAE Guideline 14 [14]) used to quantify agreement between the ISO 52016-1 engines and EnergyPlus. That metric set is not reproduced in this document — see the source methodology write-up for the definitions.

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
