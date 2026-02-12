"""
Case Study Framework for AI Agent Weather Analysis

Orchestrates multi-transect, multi-temporal analysis of historical weather
events using the wxsection.com cross-section API. Designed for AI agents
to conduct structured case studies with reproducible output.

Usage:
    from tools.agent_tools.case_study import CaseStudy

    # From a curated event
    study = CaseStudy.from_event("20181108_00z", output_dir="camp_fire_study")
    results = study.analyze_all(fhrs=[6, 12, 18, 24])
    summary = study.generate_summary()

    # Custom case study
    study = CaseStudy("Derecho Analysis", cycle="20200810_12z", output_dir="derecho")
    study.add_standard_transects(center_lat=42.0, center_lon=-91.0)
    study.add_transect("Cedar Rapids direct", (42.5, -92.0), (41.5, -90.0))
    results = study.analyze_all(fhrs=range(6, 25))
"""
import json
import math
import os
from dataclasses import dataclass, field
from typing import Optional

from .cross_section import CrossSectionTool, CrossSectionData


# ---------------------------------------------------------------------------
# Standard product groupings by analysis type
# ---------------------------------------------------------------------------

STANDARD_PRODUCTS = {
    "synoptic": ["temperature", "wind_speed", "omega", "rh"],
    "fire_weather": ["wind_speed", "rh", "temperature", "theta_e"],
    "severe": ["omega", "wind_speed", "theta_e", "temperature"],
    "winter": ["temperature", "rh", "wind_speed", "omega"],
    "tropical": ["wind_speed", "omega", "rh", "theta_e"],
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TransectSpec:
    """Specification for a single cross-section transect line."""

    label: str
    start: tuple  # (lat, lon)
    end: tuple    # (lat, lon)
    products: list = field(default_factory=lambda: [
        "temperature", "wind_speed", "rh", "omega"
    ])
    description: str = ""

    @property
    def midpoint(self) -> tuple:
        """Geographic midpoint of the transect."""
        return (
            (self.start[0] + self.end[0]) / 2.0,
            (self.start[1] + self.end[1]) / 2.0,
        )

    @property
    def length_deg(self) -> float:
        """Approximate length in degrees (Euclidean)."""
        dlat = self.end[0] - self.start[0]
        dlon = self.end[1] - self.start[1]
        return math.sqrt(dlat ** 2 + dlon ** 2)

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "start": list(self.start),
            "end": list(self.end),
            "products": self.products,
            "description": self.description,
        }


@dataclass
class AnalysisResult:
    """Result of analyzing one transect / cycle / fhr / product combination."""

    transect: TransectSpec
    cycle: str
    fhr: int
    product: str
    image_path: str
    data: CrossSectionData
    stats: dict
    notes: list = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize for JSON export (excluding raw CrossSectionData)."""
        return {
            "transect_label": self.transect.label,
            "cycle": self.cycle,
            "fhr": self.fhr,
            "product": self.product,
            "image_path": self.image_path,
            "stats": self.stats,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# CaseStudy - main framework class
# ---------------------------------------------------------------------------

class CaseStudy:
    """Framework for structured, multi-transect weather event analysis.

    Manages transect definitions, drives the cross-section API to generate
    images and extract data, computes statistics, and exports results in
    formats suitable for reports and further agent processing.
    """

    def __init__(
        self,
        event_name: str,
        cycle: str,
        output_dir: str,
        base_url: str = "http://127.0.0.1:5565",
    ):
        """Initialize a case study.

        Args:
            event_name: Human-readable event name.
            cycle: HRRR cycle key, e.g. "20181108_00z".
            output_dir: Root directory for all output (figures, data, etc.).
            base_url: Dashboard API base URL.
        """
        self.event_name = event_name
        self.cycle = cycle
        self.output_dir = os.path.abspath(output_dir)
        self.base_url = base_url

        self.figures_dir = os.path.join(self.output_dir, "figures")
        self.data_dir = os.path.join(self.output_dir, "data")
        self.sections_dir = os.path.join(self.output_dir, "sections")

        os.makedirs(self.figures_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.sections_dir, exist_ok=True)

        self.transects: list[TransectSpec] = []
        self.results: dict[str, list[AnalysisResult]] = {}
        self.metadata: dict = {
            "event_name": event_name,
            "cycle": cycle,
            "base_url": base_url,
        }

        self._tool = CrossSectionTool(base_url=base_url)

    # -- Class method constructors ------------------------------------------

    @classmethod
    def from_event(
        cls,
        cycle_key: str,
        output_dir: str,
        base_url: str = "http://127.0.0.1:5565",
    ) -> "CaseStudy":
        """Create a CaseStudy from a curated event in the API.

        Fetches the event metadata and automatically populates transects
        from the event's suggested_sections, if available.

        Args:
            cycle_key: Event cycle key, e.g. "20181108_00z".
            output_dir: Root directory for output.
            base_url: Dashboard API base URL.

        Returns:
            Initialized CaseStudy with transects from the event.

        Raises:
            RuntimeError: If the event cannot be fetched.
        """
        tool = CrossSectionTool(base_url=base_url)
        try:
            event = tool.get_event(cycle_key)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to fetch event '{cycle_key}': {exc}"
            ) from exc

        name = event.get("name", cycle_key)
        study = cls(
            event_name=name,
            cycle=cycle_key,
            output_dir=output_dir,
            base_url=base_url,
        )

        # Store full event metadata
        study.metadata["event"] = event

        # Populate transects from suggested_sections
        coords = event.get("coordinates", {})
        sections = coords.get("suggested_sections", [])
        for section in sections:
            study.add_transect(
                label=section["label"],
                start=tuple(section["start"]),
                end=tuple(section["end"]),
                products=section.get("products"),
                description=f"Curated section from event: {name}",
            )

        return study

    # -- Transect management ------------------------------------------------

    def add_transect(
        self,
        label: str,
        start: tuple,
        end: tuple,
        products: list = None,
        description: str = "",
    ) -> TransectSpec:
        """Add a transect to the case study.

        Args:
            label: Short identifier for the transect (used in filenames).
            start: (lat, lon) start point.
            end: (lat, lon) end point.
            products: List of product names. Defaults to synoptic set.
            description: Optional longer description.

        Returns:
            The created TransectSpec.
        """
        spec = TransectSpec(
            label=label,
            start=tuple(start),
            end=tuple(end),
            products=products if products is not None else list(
                STANDARD_PRODUCTS["synoptic"]
            ),
            description=description,
        )
        self.transects.append(spec)
        return spec

    def add_standard_transects(
        self,
        center_lat: float,
        center_lon: float,
        radius_deg: float = 3.0,
    ) -> list[TransectSpec]:
        """Auto-generate four cardinal/diagonal transects centered on a point.

        Creates N-S, E-W, NW-SE, and NE-SW transects spanning
        2 * radius_deg across the center point.

        Args:
            center_lat: Center latitude.
            center_lon: Center longitude.
            radius_deg: Half-length of each transect in degrees.

        Returns:
            List of the four created TransectSpec objects.
        """
        specs = []

        # N-S transect
        specs.append(self.add_transect(
            label="N-S",
            start=(center_lat + radius_deg, center_lon),
            end=(center_lat - radius_deg, center_lon),
            description=f"North-South through ({center_lat:.2f}, {center_lon:.2f})",
        ))

        # E-W transect
        specs.append(self.add_transect(
            label="E-W",
            start=(center_lat, center_lon - radius_deg),
            end=(center_lat, center_lon + radius_deg),
            description=f"East-West through ({center_lat:.2f}, {center_lon:.2f})",
        ))

        # NW-SE transect
        diag = radius_deg * math.sqrt(2) / 2
        specs.append(self.add_transect(
            label="NW-SE",
            start=(center_lat + diag, center_lon - diag),
            end=(center_lat - diag, center_lon + diag),
            description=f"NW-SE through ({center_lat:.2f}, {center_lon:.2f})",
        ))

        # NE-SW transect
        specs.append(self.add_transect(
            label="NE-SW",
            start=(center_lat + diag, center_lon + diag),
            end=(center_lat - diag, center_lon - diag),
            description=f"NE-SW through ({center_lat:.2f}, {center_lon:.2f})",
        ))

        return specs

    def _find_transect(self, label: str) -> TransectSpec:
        """Look up a transect by label.

        Raises:
            KeyError: If no transect with that label exists.
        """
        for t in self.transects:
            if t.label == label:
                return t
        raise KeyError(
            f"No transect with label '{label}'. "
            f"Available: {[t.label for t in self.transects]}"
        )

    def _safe_filename(self, text: str) -> str:
        """Convert a label to a filesystem-safe string."""
        safe = text.lower().replace(" ", "_")
        return "".join(c for c in safe if c.isalnum() or c in ("_", "-"))

    # -- Analysis -----------------------------------------------------------

    def _compute_stats(self, data: CrossSectionData) -> dict:
        """Compute summary statistics from cross-section data.

        Returns dict with surface_stats, column_min, column_max, and
        level_500_stats (if the data extends to 500 hPa).
        """
        stats = {}

        # Surface statistics
        stats["surface"] = data.surface_stats()

        # Column extremes (surface to 300 hPa)
        stats["column_min"] = data.column_min_below(300)
        stats["column_max"] = data.column_max_below(300)

        # 500 hPa level stats if available
        if data.pressures and min(data.pressures) <= 500:
            vals_500 = data.level_values(500)
            if vals_500:
                stats["level_500"] = {
                    "min": round(min(vals_500), 2),
                    "max": round(max(vals_500), 2),
                    "mean": round(sum(vals_500) / len(vals_500), 2),
                    "count": len(vals_500),
                }
            else:
                stats["level_500"] = {
                    "min": None, "max": None, "mean": None, "count": 0
                }
        else:
            stats["level_500"] = {
                "min": None, "max": None, "mean": None, "count": 0
            }

        # Transect spatial extent
        dists = data.distances
        if dists:
            stats["transect_length_km"] = round(max(dists) - min(dists), 1)
        else:
            stats["transect_length_km"] = None

        stats["n_points"] = data.n_points
        stats["n_levels"] = data.n_levels

        return stats

    def analyze_transect(
        self,
        transect_label: str,
        fhrs: list,
        products: list = None,
    ) -> list[AnalysisResult]:
        """Analyze a single transect across forecast hours and products.

        For each (fhr, product) pair, generates a cross-section image,
        fetches numerical data, and computes summary statistics.

        Args:
            transect_label: Label of a previously added transect.
            fhrs: List of forecast hours to analyze.
            products: Product list override. If None, uses the transect's
                      own product list.

        Returns:
            List of AnalysisResult objects for all (fhr, product) combos.
        """
        transect = self._find_transect(transect_label)
        products = products if products is not None else transect.products
        safe_label = self._safe_filename(transect.label)
        results = []

        for fhr in fhrs:
            for product in products:
                # Build output path
                fname = f"{safe_label}_{product}_f{fhr:02d}.png"
                image_path = os.path.join(self.figures_dir, fname)

                # Generate image
                img_ok = self._tool.generate_image(
                    start=transect.start,
                    end=transect.end,
                    cycle=self.cycle,
                    fhr=fhr,
                    product=product,
                    output_path=image_path,
                )

                if not img_ok:
                    print(f"  SKIP: image failed for {fname}")
                    continue

                # Fetch numerical data
                data = self._tool.get_data(
                    start=transect.start,
                    end=transect.end,
                    cycle=self.cycle,
                    fhr=fhr,
                    product=product,
                )

                if data is None:
                    print(f"  SKIP: data failed for {fname}")
                    continue

                # Compute statistics
                stats = self._compute_stats(data)

                result = AnalysisResult(
                    transect=transect,
                    cycle=self.cycle,
                    fhr=fhr,
                    product=product,
                    image_path=image_path,
                    data=data,
                    stats=stats,
                    notes=[],
                )
                results.append(result)
                print(f"  OK: {fname}  "
                      f"(sfc {stats['surface'].get('min')}"
                      f"-{stats['surface'].get('max')})")

        # Store results keyed by transect label
        if transect_label not in self.results:
            self.results[transect_label] = []
        self.results[transect_label].extend(results)

        return results

    def analyze_all(
        self,
        fhrs: list,
    ) -> dict[str, list[AnalysisResult]]:
        """Run analyze_transect for every registered transect.

        Args:
            fhrs: List of forecast hours to analyze.

        Returns:
            Dict mapping transect labels to lists of AnalysisResult.
        """
        all_results = {}
        for transect in self.transects:
            print(f"Analyzing transect: {transect.label}")
            results = self.analyze_transect(transect.label, fhrs)
            all_results[transect.label] = results
        return all_results

    # -- Temporal analysis --------------------------------------------------

    def temporal_evolution(
        self,
        transect_label: str,
        product: str,
        fhr_range: list,
    ) -> list[dict]:
        """Track how a field evolves over time along one transect.

        Fetches data for each forecast hour in fhr_range, computes
        surface and mid-level statistics, and returns a time series
        suitable for trend analysis.

        Args:
            transect_label: Label of a previously added transect.
            product: Single product name to track.
            fhr_range: List of forecast hours (e.g. range(0, 49)).

        Returns:
            List of dicts, one per forecast hour, containing:
              - fhr: forecast hour
              - surface_stats: {min, max, mean, count}
              - level_500_stats: {min, max, mean, count}
              - column_min: minimum value in column (sfc to 300 hPa)
              - column_max: maximum value in column (sfc to 300 hPa)
        """
        transect = self._find_transect(transect_label)
        evolution = []

        for fhr in fhr_range:
            data = self._tool.get_data(
                start=transect.start,
                end=transect.end,
                cycle=self.cycle,
                fhr=fhr,
                product=product,
            )

            if data is None:
                evolution.append({
                    "fhr": fhr,
                    "surface_stats": {"min": None, "max": None,
                                      "mean": None, "count": 0},
                    "level_500_stats": {"min": None, "max": None,
                                        "mean": None, "count": 0},
                    "column_min": None,
                    "column_max": None,
                })
                continue

            stats = self._compute_stats(data)
            evolution.append({
                "fhr": fhr,
                "surface_stats": stats["surface"],
                "level_500_stats": stats["level_500"],
                "column_min": stats["column_min"],
                "column_max": stats["column_max"],
            })

        return evolution

    # -- Comparison ---------------------------------------------------------

    def compare_events(
        self,
        other_case_study: "CaseStudy",
        transect_label: str,
        product: str,
        fhr: int,
    ) -> dict:
        """Compare the same transect/product/fhr between two events.

        Both case studies must have a transect with the given label
        (typically added via add_standard_transects on the same point,
        or manually with matching labels).

        Args:
            other_case_study: Another CaseStudy instance to compare against.
            transect_label: Transect label present in both studies.
            product: Product name to compare.
            fhr: Forecast hour to compare.

        Returns:
            Dict with stats for both events and computed deltas.
        """
        t_self = self._find_transect(transect_label)
        t_other = other_case_study._find_transect(transect_label)

        data_a = self._tool.get_data(
            start=t_self.start, end=t_self.end,
            cycle=self.cycle, fhr=fhr, product=product,
        )
        data_b = other_case_study._tool.get_data(
            start=t_other.start, end=t_other.end,
            cycle=other_case_study.cycle, fhr=fhr, product=product,
        )

        stats_a = self._compute_stats(data_a) if data_a else {}
        stats_b = self._compute_stats(data_b) if data_b else {}

        # Compute deltas where both have surface stats
        deltas = {}
        sfc_a = stats_a.get("surface", {})
        sfc_b = stats_b.get("surface", {})
        for key in ("min", "max", "mean"):
            va = sfc_a.get(key)
            vb = sfc_b.get(key)
            if va is not None and vb is not None:
                deltas[f"surface_{key}_delta"] = round(va - vb, 2)

        col_min_a = stats_a.get("column_min")
        col_min_b = stats_b.get("column_min")
        if col_min_a is not None and col_min_b is not None:
            deltas["column_min_delta"] = round(col_min_a - col_min_b, 2)

        col_max_a = stats_a.get("column_max")
        col_max_b = stats_b.get("column_max")
        if col_max_a is not None and col_max_b is not None:
            deltas["column_max_delta"] = round(col_max_a - col_max_b, 2)

        return {
            "transect_label": transect_label,
            "product": product,
            "fhr": fhr,
            "event_a": {
                "name": self.event_name,
                "cycle": self.cycle,
                "stats": stats_a,
            },
            "event_b": {
                "name": other_case_study.event_name,
                "cycle": other_case_study.cycle,
                "stats": stats_b,
            },
            "deltas": deltas,
        }

    # -- Summary and export -------------------------------------------------

    def generate_summary(self) -> dict:
        """Aggregate all results into a structured summary.

        Returns:
            Dict containing:
              - event_name, cycle, transect_count, total_figures
              - key_findings: per-transect peak surface values
              - peak_values: global extremes across all results
              - temporal_peaks: per-product peak fhr (if multiple fhrs)
        """
        summary = {
            "event_name": self.event_name,
            "cycle": self.cycle,
            "transect_count": len(self.transects),
            "total_figures": sum(
                len(r) for r in self.results.values()
            ),
            "key_findings": [],
            "peak_values": {},
            "temporal_peaks": {},
        }

        # Per-transect key findings
        for label, result_list in self.results.items():
            if not result_list:
                continue

            findings = {"transect": label, "products": {}}
            for r in result_list:
                sfc = r.stats.get("surface", {})
                prod = r.product
                if prod not in findings["products"]:
                    findings["products"][prod] = {
                        "surface_max": sfc.get("max"),
                        "surface_min": sfc.get("min"),
                        "peak_fhr": r.fhr,
                    }
                else:
                    existing = findings["products"][prod]
                    if (sfc.get("max") is not None
                            and (existing["surface_max"] is None
                                 or sfc["max"] > existing["surface_max"])):
                        existing["surface_max"] = sfc["max"]
                        existing["peak_fhr"] = r.fhr
                    if (sfc.get("min") is not None
                            and (existing["surface_min"] is None
                                 or sfc["min"] < existing["surface_min"])):
                        existing["surface_min"] = sfc["min"]

            summary["key_findings"].append(findings)

        # Global peak values and temporal peaks across all results
        for label, result_list in self.results.items():
            for r in result_list:
                prod = r.product
                sfc_max = r.stats.get("surface", {}).get("max")
                sfc_min = r.stats.get("surface", {}).get("min")
                col_max = r.stats.get("column_max")
                col_min = r.stats.get("column_min")

                if prod not in summary["peak_values"]:
                    summary["peak_values"][prod] = {
                        "global_surface_max": sfc_max,
                        "global_surface_min": sfc_min,
                        "global_column_max": col_max,
                        "global_column_min": col_min,
                    }
                else:
                    pv = summary["peak_values"][prod]
                    if sfc_max is not None and (
                        pv["global_surface_max"] is None
                        or sfc_max > pv["global_surface_max"]
                    ):
                        pv["global_surface_max"] = sfc_max
                    if sfc_min is not None and (
                        pv["global_surface_min"] is None
                        or sfc_min < pv["global_surface_min"]
                    ):
                        pv["global_surface_min"] = sfc_min
                    if col_max is not None and (
                        pv["global_column_max"] is None
                        or col_max > pv["global_column_max"]
                    ):
                        pv["global_column_max"] = col_max
                    if col_min is not None and (
                        pv["global_column_min"] is None
                        or col_min < pv["global_column_min"]
                    ):
                        pv["global_column_min"] = col_min

                # Track which fhr had the peak surface max per product
                if prod not in summary["temporal_peaks"]:
                    summary["temporal_peaks"][prod] = {
                        "peak_surface_max": sfc_max,
                        "peak_fhr": r.fhr,
                        "peak_transect": label,
                    }
                else:
                    tp = summary["temporal_peaks"][prod]
                    if sfc_max is not None and (
                        tp["peak_surface_max"] is None
                        or sfc_max > tp["peak_surface_max"]
                    ):
                        tp["peak_surface_max"] = sfc_max
                        tp["peak_fhr"] = r.fhr
                        tp["peak_transect"] = label

        return summary

    def export_data(self, format: str = "json") -> str:
        """Export all numerical results to a JSON file.

        Args:
            format: Output format (only "json" currently supported).

        Returns:
            Path to the exported file.
        """
        export = {
            "metadata": self.metadata,
            "transects": [t.to_dict() for t in self.transects],
            "results": {},
        }

        for label, result_list in self.results.items():
            export["results"][label] = [r.to_dict() for r in result_list]

        export["summary"] = self.generate_summary()

        out_path = os.path.join(self.data_dir, f"case_study_export.{format}")
        with open(out_path, "w") as f:
            json.dump(export, f, indent=2, default=str)

        print(f"Exported case study data to {out_path}")
        return out_path

    def get_figure_manifest(self) -> list[dict]:
        """List all generated figures with metadata.

        Returns a list of dicts suitable for inclusion in LaTeX reports
        or agent-driven document assembly.

        Returns:
            List of dicts with keys: path, filename, transect, product,
            fhr, cycle, caption.
        """
        manifest = []

        for label, result_list in self.results.items():
            for r in result_list:
                if not os.path.exists(r.image_path):
                    continue
                manifest.append({
                    "path": r.image_path,
                    "filename": os.path.basename(r.image_path),
                    "transect": r.transect.label,
                    "product": r.product,
                    "fhr": r.fhr,
                    "cycle": r.cycle,
                    "caption": (
                        f"{r.product.replace('_', ' ').title()} cross-section "
                        f"along {r.transect.label}, "
                        f"F{r.fhr:02d} from {r.cycle}"
                    ),
                })

        return manifest


# ---------------------------------------------------------------------------
# Module-level comparison utilities
# ---------------------------------------------------------------------------

def compare_events_batch(
    events: list[dict],
    transect: dict,
    products: list[str],
    fhr: int,
    base_url: str = "http://127.0.0.1:5565",
) -> dict:
    """Compare the same transect across multiple events.

    Each event dict must contain:
      - "cycle": cycle key (e.g. "20181108_00z")
      - "name": event name (optional, defaults to cycle key)

    The transect dict must contain:
      - "start": (lat, lon)
      - "end": (lat, lon)
      - "label": transect label (optional)

    Args:
        events: List of event dicts with at least "cycle" key.
        transect: Dict with "start" and "end" tuples.
        products: List of product names to compare.
        fhr: Forecast hour for comparison.
        base_url: Dashboard API base URL.

    Returns:
        Dict with per-event, per-product statistics and cross-event ranking.
    """
    tool = CrossSectionTool(base_url=base_url)
    label = transect.get("label", "comparison_transect")
    start = tuple(transect["start"])
    end = tuple(transect["end"])

    comparison = {
        "transect_label": label,
        "fhr": fhr,
        "events": {},
        "rankings": {},
    }

    for event in events:
        cycle = event["cycle"]
        name = event.get("name", cycle)
        event_stats = {}

        for product in products:
            data = tool.get_data(
                start=start, end=end,
                cycle=cycle, fhr=fhr, product=product,
            )
            if data is None:
                event_stats[product] = None
                continue

            sfc = data.surface_stats()
            event_stats[product] = {
                "surface": sfc,
                "column_min": data.column_min_below(300),
                "column_max": data.column_max_below(300),
            }

        comparison["events"][name] = {
            "cycle": cycle,
            "stats": event_stats,
        }

    # Build rankings: which event had the highest/lowest surface values
    for product in products:
        ranked = []
        for name, edata in comparison["events"].items():
            pstats = edata["stats"].get(product)
            if pstats is not None:
                sfc_max = pstats["surface"].get("max")
                if sfc_max is not None:
                    ranked.append({"event": name, "surface_max": sfc_max})

        ranked.sort(key=lambda x: x["surface_max"], reverse=True)
        comparison["rankings"][product] = ranked

    return comparison


def find_peak_conditions(
    case_study: CaseStudy,
    metric: str = "wind_speed",
    level: str = "surface",
) -> dict:
    """Find when and where peak conditions occur in a case study.

    Scans all results in the case study for the highest value of the
    given metric, returning the transect label, forecast hour, and
    the peak value.

    Args:
        case_study: A CaseStudy instance with populated results.
        metric: Product name to search for (e.g. "wind_speed", "rh").
        level: "surface" for surface max, or "column" for column max.

    Returns:
        Dict with peak_value, peak_fhr, peak_transect, and all_values
        (sorted list of every value found).
    """
    peak = {
        "metric": metric,
        "level": level,
        "peak_value": None,
        "peak_fhr": None,
        "peak_transect": None,
        "all_values": [],
    }

    for label, result_list in case_study.results.items():
        for r in result_list:
            if r.product != metric:
                continue

            if level == "surface":
                val = r.stats.get("surface", {}).get("max")
            elif level == "column":
                val = r.stats.get("column_max")
            else:
                val = r.stats.get("surface", {}).get("max")

            if val is None:
                continue

            peak["all_values"].append({
                "value": val,
                "fhr": r.fhr,
                "transect": label,
            })

            if peak["peak_value"] is None or val > peak["peak_value"]:
                peak["peak_value"] = val
                peak["peak_fhr"] = r.fhr
                peak["peak_transect"] = label

    # Sort descending by value
    peak["all_values"].sort(key=lambda x: x["value"], reverse=True)

    return peak
