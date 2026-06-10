"""
climate_setpoints.py
--------------------
Automatically determines the NCC 2022 Climate Zone (1-8) for a given
address or lat/lon, then assigns the correct NCC setpoints.
"""

import requests
import time
from typing import Optional

NCC_SETPOINTS = {
    "zones_1_to_4": {
        "heating_setpoint": 20.0,
        "cooling_setpoint_bedroom": 24.0,
        "cooling_setpoint_living": 27.0,
        "heating_setback": 17.0,
        "cooling_setback": 27.0,
    },
    "zones_5_to_8": {
        "heating_setpoint": 20.0,
        "cooling_setpoint_bedroom": 24.0,
        "cooling_setpoint_living": 26.0,
        "heating_setback": 17.0,
        "cooling_setback": 27.0,
    },
}

POSTCODE_TO_NCC_ZONE = [
    (800,  851,  1),
    (852,  862,  1),
    (4870, 4895, 1),
    (4800, 4810, 1),
    (4000, 4299, 2),
    (4300, 4499, 2),
    (4500, 4699, 2),
    (4700, 4799, 2),
    (2440, 2490, 2),
    (2444, 2484, 2),
    (4720, 4850, 3),
    (2800, 2880, 3),
    (5000, 5199, 3),
    (6400, 6799, 3),
    (2600, 2620, 4),
    (2621, 2650, 4),
    (2630, 2649, 4),
    (2000, 2249, 5),
    (2250, 2439, 5),
    (2500, 2599, 5),
    (2650, 2799, 5),
    (3000, 3499, 6),
    (3500, 3699, 6),
    (3700, 3799, 6),
    (3800, 3999, 6),
    (5200, 5799, 6),
    (6000, 6199, 6),
    (6200, 6399, 6),
    (7000, 7999, 7),
    (3699, 3700, 7),
    (3958, 3999, 7),
    (2627, 2629, 8),
    (3699, 3699, 8),
]

def postcode_to_ncc_zone(postcode: int) -> Optional[int]:
    """
    Maps an Australian postcode to an NCC Climate Zone (1-8).
    Returns None if postcode is not found in the lookup table.
    """
    for start, end, zone in POSTCODE_TO_NCC_ZONE:
        if start <= postcode <= end:
            return zone
    return None

def geocode_address(address: str) -> dict:
    """
    Converts a free-text Australian address into coordinates and postcode.
    """
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": address,
        "countrycodes": "au",
        "format": "json",
        "addressdetails": 1,
        "limit": 1,
    }
    headers = {"User-Agent": "NCC-ClimateZoneLookup/1.0"}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        results = resp.json()
    except requests.RequestException as e:
        raise ValueError(f"Geocoding API error: {e}")

    if not results:
        raise ValueError(f"Address not found: '{address}'. Try adding suburb and state.")

    result = results[0]
    addr_detail = result.get("address", {})
    postcode_str = addr_detail.get("postcode", "")

    return {
        "lat": float(result["lat"]),
        "lon": float(result["lon"]),
        "postcode": int(postcode_str) if postcode_str.isdigit() else None,
        "display_name": result.get("display_name", ""),
    }

def get_ncc_setpoints(
    address: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    postcode: Optional[int] = None,
    ncc_zone: Optional[int] = None,
) -> dict:
    """
    Determines NCC 2022 heating and cooling setpoints for a building location.
    """
    resolved_postcode = postcode
    display_name = ""
    source = ""

    if ncc_zone is not None:
        source = "directly provided"

    elif resolved_postcode is not None:
        source = "postcode provided"

    elif address is not None:
        print(f"  Geocoding address: '{address}' ...")
        geo = geocode_address(address)
        resolved_postcode = geo["postcode"]
        display_name = geo["display_name"]
        source = f"geocoded from address"
        print(f"  Resolved to: {display_name}")
        print(f"  Postcode: {resolved_postcode}, Lat: {geo['lat']:.4f}, Lon: {geo['lon']:.4f}")
        time.sleep(1)

    elif lat is not None and lon is not None:
        print(f"  Reverse geocoding coordinates: ({lat}, {lon}) ...")
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {"lat": lat, "lon": lon, "format": "json", "addressdetails": 1}
        headers = {"User-Agent": "NCC-ClimateZoneLookup/1.0"}
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        postcode_str = result.get("address", {}).get("postcode", "")
        resolved_postcode = int(postcode_str) if postcode_str.isdigit() else None
        display_name = result.get("display_name", "")
        source = "reverse geocoded from lat/lon"
        print(f"  Resolved to: {display_name}")
        print(f"  Postcode: {resolved_postcode}")
        time.sleep(1)

    else:
        raise ValueError(
            "Provide at least one of: ncc_zone, postcode, address, or lat+lon."
        )

    if ncc_zone is None:
        if resolved_postcode is None:
            raise ValueError(
                "Could not determine postcode from the provided input. "
                "Please provide postcode or ncc_zone directly."
            )
        ncc_zone = postcode_to_ncc_zone(resolved_postcode)
        if ncc_zone is None:
            raise ValueError(
                f"Postcode {resolved_postcode} not found in NCC zone lookup table. "
                f"Please provide ncc_zone directly (1-8)."
            )

    if not 1 <= ncc_zone <= 8:
        raise ValueError(f"NCC zone must be between 1 and 8, got {ncc_zone}.")

    if ncc_zone <= 4:
        zone_group = "zones_1_to_4"
    else:
        zone_group = "zones_5_to_8"

    setpoints = NCC_SETPOINTS[zone_group].copy()

    return {
        "ncc_zone": ncc_zone,
        "zone_group": zone_group,
        "source": source,
        "display_name": display_name,
        "postcode": resolved_postcode,
        **setpoints,
    }

def apply_setpoints_to_building(building_data: dict, setpoints: dict) -> dict:
    """
    Injects the resolved NCC setpoints directly into the building_data
    temperature_setpoints block used by pybuildingenergy.
    """
    building_data["building_parameters"]["temperature_setpoints"].update({
        "heating_setpoint": setpoints["heating_setpoint"],
        "heating_setback":  setpoints["heating_setback"],
        "cooling_setpoint": setpoints["cooling_setpoint_bedroom"],
        "cooling_setback":  setpoints["cooling_setback"],
    })
    
    building_data["building_parameters"]["temperature_setpoints"]["ncc_zone"] = setpoints["ncc_zone"]
    building_data["building_parameters"]["temperature_setpoints"]["cooling_setpoint_bedroom"] = setpoints["cooling_setpoint_bedroom"]
    building_data["building_parameters"]["temperature_setpoints"]["cooling_setpoint_living"] = setpoints["cooling_setpoint_living"]
    return building_data


if __name__ == "__main__":
    print("=" * 60)
    print("NCC 2022 Climate Zone + Setpoint Lookup")
    print("=" * 60)

    print("\n--- Address lookup ---")
    sp = get_ncc_setpoints(address="Melbourne VIC Australia")
    print(f"  NCC Zone:               {sp['ncc_zone']}")
    print(f"  Heating setpoint:       {sp['heating_setpoint']}°C")
    print(f"  Cooling (bedroom):      {sp['cooling_setpoint_bedroom']}°C")
    print(f"  Cooling (living areas): {sp['cooling_setpoint_living']}°C")
    print(f"  Heating setback:        {sp['heating_setback']}°C")
    print(f"  Cooling setback:        {sp['cooling_setback']}°C")

    print("\n--- Postcode lookup ---")
    sp2 = get_ncc_setpoints(postcode=2000)
    print(f"  Postcode 2000 → NCC Zone: {sp2['ncc_zone']}")
    print(f"  Cooling (living areas):   {sp2['cooling_setpoint_living']}°C")

    print("\n--- Direct NCC zone ---")
    sp3 = get_ncc_setpoints(ncc_zone=6)
    print(f"  Zone 6 → Cooling (bedroom):  {sp3['cooling_setpoint_bedroom']}°C")
    print(f"  Zone 6 → Cooling (living):   {sp3['cooling_setpoint_living']}°C")