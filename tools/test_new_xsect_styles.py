#!/usr/bin/env python3
"""Test all new cross-section styles."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.cross_section_production import (
    extract_cross_section_multi_fields,
    create_production_cross_section,
)


def main():
    # Find available GRIB file
    run_dir = Path("outputs/hrrr/20251224/19z")

    if not run_dir.exists():
        outputs_dir = Path("outputs/hrrr")
        prs_files = sorted(outputs_dir.glob("**/F00/*wrfprs*.grib2"))
        if not prs_files:
            print("No pressure GRIB files found. Run processor first.")
            return
        grib_file = str(prs_files[-1])
    else:
        grib_files = list(run_dir.glob("F00/*wrfprs*.grib2"))
        if not grib_files:
            print("No F00 GRIB file found")
            return
        grib_file = str(grib_files[0])

    print(f"Using GRIB file: {grib_file}")

    # Denver to Chicago cross-section
    start_point = (39.74, -104.99)  # Denver
    end_point = (41.88, -87.63)     # Chicago

    output_dir = Path("outputs/xsect_new_styles")
    output_dir.mkdir(exist_ok=True)

    # Test all new styles
    new_styles = [
        "temp",        # Temperature (°C)
        "theta_e",     # Equivalent Potential Temperature
        "q",           # Specific Humidity
        "cloud_total", # Total Condensate
        "shear",       # Vertical Wind Shear
        "wetbulb",     # Wet-Bulb Temperature
        "icing",       # Supercooled Liquid Water
        "lapse_rate",  # Temperature Lapse Rate
    ]

    for style in new_styles:
        print(f"\n=== Testing {style} ===")

        try:
            # Extract data for this style
            data = extract_cross_section_multi_fields(
                grib_file, start_point, end_point,
                n_points=100, style=style
            )

            if data is None:
                print(f"  Failed to extract data for {style}")
                continue

            # Create cross-section
            output_path = create_production_cross_section(
                data=data,
                cycle="20251224_19Z",
                forecast_hour=0,
                output_dir=output_dir,
                style=style,
                dpi=120,
                fast_mode=True,  # Skip inset map for speed
            )

            if output_path:
                print(f"  Created: {output_path}")
            else:
                print(f"  Failed to create image for {style}")

        except Exception as e:
            print(f"  Error with {style}: {e}")
            import traceback
            traceback.print_exc()

    print("\n=== Done ===")
    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    main()
