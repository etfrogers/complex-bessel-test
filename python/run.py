"""Pipeline orchestration CLI — replaces Makefile.

Usage:
    uv run --project python python/run.py <command> [<command> ...]
    ./run <command> [<command> ...]

Commands can be chained: ./run build grid compute-rust bench-rust compare dashboard
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
IMAGES = ROOT / "images"
FORTRAN = ROOT / "fortran"
FORTRAN_BUILD = FORTRAN / ".build"


def run_cmd(args, **kwargs):
    """Run a subprocess command; exit on failure."""
    print(f"  $ {' '.join(str(a) for a in args)}", flush=True)
    proc = subprocess.run(args, **kwargs)
    if proc.returncode != 0:
        sys.exit(proc.returncode)


def run_python_script(name, *args):
    """Run a sibling Python script using the same interpreter."""
    script = Path(__file__).parent / name
    run_cmd([sys.executable, str(script), *args])


# ── Build ──


def cmd_build_rust():
    print("Building Rust...", flush=True)
    run_cmd(["cargo", "build", "--release"], cwd=ROOT)


def cmd_build_fortran():
    print("Building Fortran...", flush=True)
    toms644_src = FORTRAN / "toms644"
    if not toms644_src.exists():
        print("ERROR: fortran/toms644 not found", file=sys.stderr)
        sys.exit(1)

    FORTRAN_BUILD.mkdir(parents=True, exist_ok=True)
    zbsubs = FORTRAN_BUILD / "zbsubs.f"

    # Extract zbsubs.f from combined toms644 file
    run_cmd(
        [
            "awk",
            '/^C\\*\\*\\* / { fname = $2; if (fname == "Readme") { skip = 1; next } skip = 0; next }\n'
            'skip == 0 && fname == "zbsubs.f" { print }',
            str(toms644_src),
        ],
        stdout=open(zbsubs, "w"),
    )

    # Fix separator lines for gfortran compatibility
    run_cmd(["sed", "-i.bak", "s/^--*/C ---/", str(zbsubs)])
    (zbsubs.parent / (zbsubs.name + ".bak")).unlink()

    machcon = FORTRAN / "machcon_ieee.f"

    # Compile compute_grid
    run_cmd(
        [
            "gfortran",
            "-O2",
            "-std=legacy",
            "-o",
            str(FORTRAN / "compute_grid"),
            str(FORTRAN / "compute_grid.f"),
            str(machcon),
            str(zbsubs),
        ]
    )

    # Compile bench_fortran
    run_cmd(
        [
            "gfortran",
            "-O2",
            "-std=legacy",
            "-o",
            str(FORTRAN / "bench_fortran"),
            str(FORTRAN / "bench.f"),
            str(machcon),
            str(zbsubs),
        ]
    )


def cmd_build():
    cmd_build_rust()
    cmd_build_fortran()


# ── Grid ──


def cmd_grid():
    print("Generating test grid...", flush=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    run_python_script("generate_grid.py")


# ── Compute ──


def cmd_compute_rust():
    print("Computing Rust results (complex-bessel)...", flush=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    grid = RESULTS / "test_grid.json"
    out = RESULTS / "rust_results.json"
    with open(grid) as fin, open(out, "w") as fout:
        run_cmd(
            [str(ROOT / "target" / "release" / "compute"), "complex-bessel"],
            stdin=fin,
            stdout=fout,
            stderr=subprocess.DEVNULL,
        )


def cmd_compute_bessel_rs():
    print("Computing Rust results (bessel-rs)...", flush=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    grid = RESULTS / "test_grid.json"
    out = RESULTS / "bessel_rs_results.json"
    with open(grid) as fin, open(out, "w") as fout:
        run_cmd(
            [str(ROOT / "target" / "release" / "compute"), "bessel-rs"],
            stdin=fin,
            stdout=fout,
            stderr=subprocess.DEVNULL,
        )


def cmd_compute_real_bessel():
    print("Computing Rust results (real-bessel)...", flush=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    grid = RESULTS / "test_grid.json"
    out = RESULTS / "real_bessel_results.json"
    with open(grid) as fin, open(out, "w") as fout:
        run_cmd(
            [str(ROOT / "target" / "release" / "compute"), "real-bessel"],
            stdin=fin,
            stdout=fout,
            stderr=subprocess.DEVNULL,
        )


def cmd_compute_fortran():
    print("Computing Fortran results...", flush=True)
    run_python_script("compute_fortran.py", "--mode", "compute")


def cmd_compute_scipy():
    print("Computing SciPy results...", flush=True)
    run_python_script("compute_scipy.py", "--mode", "compute")


def cmd_compute_mpmath():
    print("Computing mpmath results...", flush=True)
    run_python_script("compute_mpmath.py")


def cmd_compute():
    cmd_compute_rust()
    cmd_compute_bessel_rs()
    cmd_compute_real_bessel()
    cmd_compute_fortran()
    cmd_compute_scipy()


# ── Bench ──


def cmd_bench_rust():
    print("Benchmarking Rust (complex-bessel)...", flush=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    grid = RESULTS / "test_grid.json"
    out = RESULTS / "rust_bench.json"
    with open(grid) as fin, open(out, "w") as fout:
        run_cmd(
            [str(ROOT / "target" / "release" / "bench"), "complex-bessel"],
            stdin=fin,
            stdout=fout,
        )


def cmd_bench_bessel_rs():
    print("Benchmarking Rust (bessel-rs)...", flush=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    grid = RESULTS / "test_grid.json"
    out = RESULTS / "bessel_rs_bench.json"
    with open(grid) as fin, open(out, "w") as fout:
        run_cmd(
            [str(ROOT / "target" / "release" / "bench"), "bessel-rs"],
            stdin=fin,
            stdout=fout,
        )


def cmd_bench_real_bessel():
    print("Benchmarking Rust (real-bessel)...", flush=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    grid = RESULTS / "test_grid.json"
    out = RESULTS / "real_bessel_bench.json"
    with open(grid) as fin, open(out, "w") as fout:
        run_cmd(
            [str(ROOT / "target" / "release" / "bench"), "real-bessel"],
            stdin=fin,
            stdout=fout,
        )


def cmd_bench_fortran():
    print("Benchmarking Fortran...", flush=True)
    run_python_script("compute_fortran.py", "--mode", "bench")


def cmd_bench_scipy():
    print("Benchmarking SciPy...", flush=True)
    run_python_script("compute_scipy.py", "--mode", "bench")


def cmd_bench():
    cmd_bench_rust()
    cmd_bench_bessel_rs()
    cmd_bench_real_bessel()
    cmd_bench_fortran()
    cmd_bench_scipy()


# ── Compare & Dashboard ──


def cmd_compare():
    print("Comparing results...", flush=True)
    run_python_script("compare.py")


def cmd_dashboard():
    print("Generating dashboard...", flush=True)
    IMAGES.mkdir(parents=True, exist_ok=True)
    run_python_script("dashboard.py")


# ── All ──


def cmd_all():
    cmd_build()
    cmd_grid()
    cmd_compute()
    cmd_bench()
    cmd_compare()
    cmd_dashboard()


def cmd_all_heavy():
    cmd_build()
    cmd_grid()
    cmd_compute_mpmath()
    cmd_compute()
    cmd_bench()
    cmd_compare()
    cmd_dashboard()


# ── Clean ──


def cmd_clean():
    print("Cleaning...", flush=True)
    for f in RESULTS.glob("*.json"):
        f.unlink()
        print(f"  rm {f}")
    for ext in ("*.svg", "*.pdf"):
        for f in IMAGES.glob(ext):
            f.unlink()
            print(f"  rm {f}")
    run_cmd(["cargo", "clean"], cwd=ROOT)
    for name in ["compute_grid", "bench_fortran"]:
        p = FORTRAN / name
        if p.exists():
            p.unlink()
            print(f"  rm {p}")
    if FORTRAN_BUILD.exists():
        shutil.rmtree(FORTRAN_BUILD)
        print(f"  rm -rf {FORTRAN_BUILD}")


# ── CLI ──

COMMANDS = {
    "build": cmd_build,
    "build-rust": cmd_build_rust,
    "build-fortran": cmd_build_fortran,
    "grid": cmd_grid,
    "compute": cmd_compute,
    "compute-rust": cmd_compute_rust,
    "compute-bessel-rs": cmd_compute_bessel_rs,
    "compute-real-bessel": cmd_compute_real_bessel,
    "compute-fortran": cmd_compute_fortran,
    "compute-scipy": cmd_compute_scipy,
    "compute-mpmath": cmd_compute_mpmath,
    "bench": cmd_bench,
    "bench-rust": cmd_bench_rust,
    "bench-bessel-rs": cmd_bench_bessel_rs,
    "bench-real-bessel": cmd_bench_real_bessel,
    "bench-fortran": cmd_bench_fortran,
    "bench-scipy": cmd_bench_scipy,
    "compare": cmd_compare,
    "dashboard": cmd_dashboard,
    "all": cmd_all,
    "all-heavy": cmd_all_heavy,
    "clean": cmd_clean,
}


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline orchestration for complex-bessel-test",
    )
    parser.add_argument(
        "commands",
        nargs="+",
        choices=list(COMMANDS.keys()),
        metavar="command",
        help=f"Commands to run: {', '.join(COMMANDS.keys())}",
    )
    args = parser.parse_args()

    for cmd_name in args.commands:
        print(f"\n=== {cmd_name} ===", flush=True)
        COMMANDS[cmd_name]()


if __name__ == "__main__":
    main()
