"""Compare Rust, Fortran, scipy results against mpmath ground truth.

Produces comparison.json with accuracy statistics and error distributions.
"""

import json
import math
import os
from collections import defaultdict

AIRY_FUNCS = {
    "airy",
    "airyprime",
    "biry",
    "biryprime",
    "airy_scaled",
    "airyprime_scaled",
    "biry_scaled",
    "biryprime_scaled",
}

NEGATIVE_NU_VALUES = {-0.5, -1.5, -2.0}

# Functions that display as short names in results
DISPLAY_NAMES = {
    "besselj": "J",
    "bessely": "Y",
    "besseli": "I",
    "besselk": "K",
    "hankel1": "H1",
    "hankel2": "H2",
    "airy": "Ai",
    "airyprime": "Ai'",
    "biry": "Bi",
    "biryprime": "Bi'",
    "besselj_scaled": "J_s",
    "bessely_scaled": "Y_s",
    "besseli_scaled": "I_s",
    "besselk_scaled": "K_s",
    "hankel1_scaled": "H1_s",
    "hankel2_scaled": "H2_s",
    "airy_scaled": "Ai_s",
    "airyprime_scaled": "Ai'_s",
    "biry_scaled": "Bi_s",
    "biryprime_scaled": "Bi'_s",
}


def relative_error(computed_re, computed_im, ref_re, ref_im):
    """Compute relative error between computed and reference complex values.

    Returns None when both values are near zero (comparison meaningless).
    math.hypot is used to avoid overflow on large intermediate values.
    """
    diff_re = computed_re - ref_re
    diff_im = computed_im - ref_im
    diff_mag = math.hypot(diff_re, diff_im)

    ref_mag = math.hypot(ref_re, ref_im)

    # Both values near zero: comparison meaningless (e.g. analytic zeros,
    # f64 underflow at extreme orders). Skip these points entirely.
    if ref_mag < 1e-14 and diff_mag < 1e-14:
        return None

    if ref_mag < 1e-300:
        # Reference essentially zero but computed is not: real problem
        return diff_mag

    return diff_mag / ref_mag


def load_results(path):
    """Load a results JSON file. Returns list of dicts."""
    with open(path) as f:
        return json.load(f)


def index_by_key(records, include_negative_nu=True):
    """Build dict keyed by (grid, function, nu, z_re, z_im) -> record."""
    idx = {}
    for r in records:
        nu = r["nu"]
        if not include_negative_nu and nu in NEGATIVE_NU_VALUES:
            continue
        key = (r["grid"], r["function"], r["nu"], r["z_re"], r["z_im"])
        idx[key] = r
    return idx


def main():
    results_dir = os.path.join(os.path.dirname(__file__), "..", "results")

    print("Loading results...", flush=True)
    rust = load_results(os.path.join(results_dir, "rust_results.json"))
    bessel_rs = load_results(os.path.join(results_dir, "bessel_rs_results.json"))
    fortran = load_results(os.path.join(results_dir, "fortran_results.json"))
    mpmath_data = load_results(os.path.join(results_dir, "mpmath_results.json"))
    scipy_data = load_results(os.path.join(results_dir, "scipy_results.json"))

    # Index mpmath by key
    mpmath_idx = index_by_key(mpmath_data)

    # Index Fortran by key (nu >= 0 only)
    fortran_idx = index_by_key(fortran, include_negative_nu=False)

    # ── 1. Accuracy vs mpmath ──
    print("Computing accuracy vs mpmath...", flush=True)
    accuracy = defaultdict(lambda: {"rust": [], "bessel_rs": [], "fortran": [], "scipy": []})

    # Rust vs mpmath
    for r in rust:
        key = (r["grid"], r["function"], r["nu"], r["z_re"], r["z_im"])
        if r["status"] not in ("ok", "reduced_precision") or r["re"] is None:
            continue
        mp = mpmath_idx.get(key)
        if not mp or mp["status"] != "ok" or mp["re"] is None:
            continue
        ref_re = float(mp["re"])
        ref_im = float(mp["im"])
        err = relative_error(r["re"], r["im"], ref_re, ref_im)
        if err is not None:
            accuracy[r["function"]]["rust"].append(err)

    # bessel-rs vs mpmath
    for r in bessel_rs:
        key = (r["grid"], r["function"], r["nu"], r["z_re"], r["z_im"])
        if r["status"] not in ("ok", "reduced_precision") or r["re"] is None:
            continue
        mp = mpmath_idx.get(key)
        if not mp or mp["status"] != "ok" or mp["re"] is None:
            continue
        ref_re = float(mp["re"])
        ref_im = float(mp["im"])
        err = relative_error(r["re"], r["im"], ref_re, ref_im)
        if err is not None:
            accuracy[r["function"]]["bessel_rs"].append(err)

    # Fortran vs mpmath (nu >= 0 only)
    for r in fortran:
        key = (r["grid"], r["function"], r["nu"], r["z_re"], r["z_im"])
        if r["ierr"] not in (0, 3) or r["re"] is None:
            continue
        mp = mpmath_idx.get(key)
        if not mp or mp["status"] != "ok" or mp["re"] is None:
            continue
        ref_re = float(mp["re"])
        ref_im = float(mp["im"])
        err = relative_error(r["re"], r["im"], ref_re, ref_im)
        if err is not None:
            accuracy[r["function"]]["fortran"].append(err)

    # scipy vs mpmath
    for r in scipy_data:
        key = (r["grid"], r["function"], r["nu"], r["z_re"], r["z_im"])
        if r["status"] != "ok" or r["re"] is None:
            continue
        mp = mpmath_idx.get(key)
        if not mp or mp["status"] != "ok" or mp["re"] is None:
            continue
        ref_re = float(mp["re"])
        ref_im = float(mp["im"])
        err = relative_error(r["re"], r["im"], ref_re, ref_im)
        if err is not None:
            accuracy[r["function"]]["scipy"].append(err)

    # Summarize accuracy
    accuracy_summary = {}
    for func, data in accuracy.items():
        accuracy_summary[func] = {}
        for impl_name, errors in data.items():
            if errors:
                accuracy_summary[func][impl_name] = {
                    "count": len(errors),
                    "max_err": max(errors),
                    "median_err": sorted(errors)[len(errors) // 2],
                    "mean_err": sum(errors) / len(errors),
                    "p99_err": sorted(errors)[int(len(errors) * 0.99)],
                }
            else:
                accuracy_summary[func][impl_name] = {
                    "count": 0,
                    "max_err": None,
                    "median_err": None,
                    "mean_err": None,
                    "p99_err": None,
                }

    # ── 2. Rust vs Fortran direct comparison (nu >= 0 only) ──
    print("Computing Rust vs Fortran...", flush=True)
    rust_vs_fortran = defaultdict(
        lambda: {
            "errors": [],
            "status_match": 0,
            "status_mismatch": 0,
            "mismatches": [],
        }
    )

    rust_idx = index_by_key(rust, include_negative_nu=False)

    for key, fr in fortran_idx.items():
        rr = rust_idx.get(key)
        if rr is None:
            continue

        func = key[1]

        # Status comparison
        rust_ok = rr["status"] in ("ok", "reduced_precision")
        fortran_ok = fr["ierr"] in (0, 3)

        # Map Rust status to Fortran IERR equivalent
        rust_ierr_equiv = {
            "ok": 0,
            "invalid_input": 1,
            "overflow": 2,
            "reduced_precision": 3,
            "total_precision_loss": 4,
            "convergence_failure": 5,
        }.get(rr["status"], -1)

        if rust_ierr_equiv == fr["ierr"]:
            rust_vs_fortran[func]["status_match"] += 1
        else:
            rust_vs_fortran[func]["status_mismatch"] += 1
            if len(rust_vs_fortran[func]["mismatches"]) < 20:
                rust_vs_fortran[func]["mismatches"].append(
                    {
                        "nu": key[2],
                        "z_re": key[3],
                        "z_im": key[4],
                        "rust_status": rr["status"],
                        "fortran_ierr": fr["ierr"],
                    }
                )

        # Value comparison (only when both ok)
        if rust_ok and fortran_ok and rr["re"] is not None and fr["re"] is not None:
            err = relative_error(rr["re"], rr["im"], fr["re"], fr["im"])
            if err is not None:
                rust_vs_fortran[func]["errors"].append(err)

    # Summarize Rust vs Fortran
    rvf_summary = {}
    for func, data in rust_vs_fortran.items():
        errors = data["errors"]
        rvf_summary[func] = {
            "count": len(errors),
            "max_err": max(errors) if errors else None,
            "median_err": sorted(errors)[len(errors) // 2] if errors else None,
            "status_match": data["status_match"],
            "status_mismatch": data["status_mismatch"],
            "mismatches": data["mismatches"],
        }

    # ── 3. Error summary ──
    print("Computing error summary...", flush=True)
    error_summary = defaultdict(lambda: defaultdict(int))

    for r in rust:
        error_summary[r["function"]]["total"] += 1
        error_summary[r["function"]][r["status"]] += 1

    # ── Save ──
    # Save all error distributions for dashboard
    error_distributions = {
        "accuracy_vs_mpmath": {},
        "rust_vs_fortran": {},
    }

    for func, data in accuracy.items():
        error_distributions["accuracy_vs_mpmath"][func] = {}
        for impl_name, errors in data.items():
            # Filter out inf/nan for violin plot rendering, clamp zeros to 1e-17
            finite = [e for e in errors if math.isfinite(e)]
            clamped = [max(e, 1e-17) for e in finite]
            error_distributions["accuracy_vs_mpmath"][func][impl_name] = clamped

    for func, data in rust_vs_fortran.items():
        finite = [e for e in data["errors"] if math.isfinite(e)]
        clamped = [max(e, 1e-17) for e in finite]
        error_distributions["rust_vs_fortran"][func] = clamped

    comparison = {
        "accuracy_vs_mpmath": accuracy_summary,
        "rust_vs_fortran": rvf_summary,
        "error_summary": dict(error_summary),
        "error_distributions": error_distributions,
    }

    out_path = os.path.join(results_dir, "comparison.json")
    with open(out_path, "w") as f:
        json.dump(comparison, f, indent=2, default=str)

    print(f"\nComparison saved to {out_path}")

    # Print summary
    print("\n=== Accuracy vs mpmath (max / p99 relative error) ===")
    for func in sorted(accuracy_summary.keys()):
        data = accuracy_summary[func]
        parts = []
        for impl_name in ["rust", "bessel_rs", "fortran", "scipy"]:
            d = data.get(impl_name, {})
            if d.get("max_err") is not None:
                parts.append(
                    f"{impl_name}: max={d['max_err']:.2e} p99={d['p99_err']:.2e} (n={d['count']})"
                )
        dname = DISPLAY_NAMES.get(func, func)
        print(f"  {dname:6s}: {', '.join(parts)}")

    print("\n=== Rust vs Fortran (max relative error, nu >= 0 only) ===")
    for func in sorted(rvf_summary.keys()):
        d = rvf_summary[func]
        dname = DISPLAY_NAMES.get(func, func)
        max_e = f"{d['max_err']:.2e}" if d["max_err"] is not None else "N/A"
        print(
            f"  {dname:6s}: max={max_e}, status_match={d['status_match']}, mismatch={d['status_mismatch']}"
        )

    print("\n=== Error summary (Rust) ===")
    for func in sorted(error_summary.keys()):
        counts = error_summary[func]
        dname = DISPLAY_NAMES.get(func, func)
        ok = counts.get("ok", 0)
        total = counts.get("total", 0)
        overflow = counts.get("overflow", 0)
        invalid = counts.get("invalid_input", 0)
        print(f"  {dname:6s}: {ok}/{total} ok, {overflow} overflow, {invalid} invalid")


if __name__ == "__main__":
    main()
