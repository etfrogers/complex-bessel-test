use bessel_rs::{
    HankelKind, airy, airy_b, airy_bp, airyp, bessel_i, bessel_j, bessel_k, bessel_y, hankel,
};
use complex_bessel::{
    airy as airy_cb, airyprime, besseli, besseli_scaled, besselj, besselj_scaled, besselk,
    besselk_scaled, bessely, bessely_scaled, biry, biryprime, hankel1, hankel1_scaled, hankel2,
    hankel2_scaled,
};
use num_complex::Complex;
use serde::{Deserialize, Serialize};
use std::env;
use std::io::{self, Read};
use std::time::Instant;

#[derive(Deserialize)]
struct TestGrid {
    unscaled_grid: GridSpec,
    scaled_grid: GridSpec,
}

#[derive(Deserialize)]
struct GridSpec {
    nu_values: Vec<f64>,
    re_values: Vec<f64>,
    im_values: Vec<f64>,
    functions: Vec<String>,
}

#[derive(Serialize)]
struct BenchRecord {
    grid: String,
    function: String,
    nu: f64,
    z_re: f64,
    z_im: f64,
    time_ns: u64,
}

fn call_function_bessel_rs(fname: &str, nu: f64, z: Complex<f64>) {
    let _ = match fname {
        "besselj" => std::hint::black_box(bessel_j(nu, z)),
        "bessely" => std::hint::black_box(bessel_y(nu, z)),
        "besseli" => std::hint::black_box(bessel_i(nu, z)),
        "besselk" => std::hint::black_box(bessel_k(nu, z)),
        "hankel1" => std::hint::black_box(hankel(nu, z, HankelKind::First)),
        "hankel2" => std::hint::black_box(hankel(nu, z, HankelKind::Second)),
        "airy" => std::hint::black_box(airy(z)),
        "airyprime" => std::hint::black_box(airyp(z)),
        "biry" => std::hint::black_box(airy_b(z)),
        "biryprime" => std::hint::black_box(airy_bp(z)),
        _ => Ok(Complex::new(0.0, 0.0)),
    };
}

fn call_function(fname: &str, nu: f64, z: Complex<f64>) {
    let _ = match fname {
        "besselj" => besselj(nu, z).map(|v| {
            std::hint::black_box(v);
        }),
        "bessely" => bessely(nu, z).map(|v| {
            std::hint::black_box(v);
        }),
        "besseli" => besseli(nu, z).map(|v| {
            std::hint::black_box(v);
        }),
        "besselk" => besselk(nu, z).map(|v| {
            std::hint::black_box(v);
        }),
        "hankel1" => hankel1(nu, z).map(|v| {
            std::hint::black_box(v);
        }),
        "hankel2" => hankel2(nu, z).map(|v| {
            std::hint::black_box(v);
        }),
        "airy" => airy_cb(z).map(|v| {
            std::hint::black_box(v);
        }),
        "airyprime" => airyprime(z).map(|v| {
            std::hint::black_box(v);
        }),
        "biry" => biry(z).map(|v| {
            std::hint::black_box(v);
        }),
        "biryprime" => biryprime(z).map(|v| {
            std::hint::black_box(v);
        }),
        "besselj_scaled" => besselj_scaled(nu, z).map(|v| {
            std::hint::black_box(v);
        }),
        "bessely_scaled" => bessely_scaled(nu, z).map(|v| {
            std::hint::black_box(v);
        }),
        "besseli_scaled" => besseli_scaled(nu, z).map(|v| {
            std::hint::black_box(v);
        }),
        "besselk_scaled" => besselk_scaled(nu, z).map(|v| {
            std::hint::black_box(v);
        }),
        "hankel1_scaled" => hankel1_scaled(nu, z).map(|v| {
            std::hint::black_box(v);
        }),
        "hankel2_scaled" => hankel2_scaled(nu, z).map(|v| {
            std::hint::black_box(v);
        }),
        "airy_scaled" => complex_bessel::airy_scaled(z).map(|v| {
            std::hint::black_box(v);
        }),
        "airyprime_scaled" => complex_bessel::airyprime_scaled(z).map(|v| {
            std::hint::black_box(v);
        }),
        "biry_scaled" => complex_bessel::biry_scaled(z).map(|v| {
            std::hint::black_box(v);
        }),
        "biryprime_scaled" => complex_bessel::biryprime_scaled(z).map(|v| {
            std::hint::black_box(v);
        }),
        _ => Ok(()),
    };
}

fn bench_grid(grid_name: &str, spec: &GridSpec, implementation: &str) -> Vec<BenchRecord> {
    let mut records = Vec::new();

    // Warmup: 100 dummy calls
    let warmup_z = Complex::new(1.0, 2.0);
    for _ in 0..100 {
        for func in &spec.functions {
            match implementation {
                "complex-bessel" => call_function(func, 0.5, warmup_z),
                "bessel-rs" => call_function_bessel_rs(func, 0.5, warmup_z),
                _ => panic!("Unknown implementation"),
            }
        }
    }

    for func in &spec.functions {
        for &nu in &spec.nu_values {
            for &re in &spec.re_values {
                for &im in &spec.im_values {
                    let z = Complex::new(re, im);

                    // Warmup this specific point
                    match implementation {
                        "complex-bessel" => call_function(func, nu, z),
                        "bessel-rs" => call_function_bessel_rs(func, nu, z),
                        _ => panic!("Unknown implementation"),
                    }

                    let nrep = 1000;
                    let start = Instant::now();
                    for _ in 0..nrep {
                        match implementation {
                            "complex-bessel" => call_function(func, nu, z),
                            "bessel-rs" => call_function_bessel_rs(func, nu, z),
                            _ => panic!("Unknown implementation"),
                        }
                    }
                    let elapsed = start.elapsed().as_nanos() as u64 / nrep;

                    records.push(BenchRecord {
                        grid: grid_name.to_string(),
                        function: func.clone(),
                        nu,
                        z_re: re,
                        z_im: im,
                        time_ns: elapsed,
                    });
                }
            }
        }
    }

    records
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 2 {
        eprintln!("Usage: {} <implementation>", args[0]);
        return;
    }
    let implementation = &args[1];

    let mut input = String::new();
    io::stdin()
        .read_to_string(&mut input)
        .expect("Failed to read stdin");

    let grid: TestGrid = serde_json::from_str(&input).expect("Failed to parse test_grid.json");

    eprintln!("Benchmarking Rust ({implementation})...");
    let mut all_records = Vec::new();
    all_records.extend(bench_grid("unscaled", &grid.unscaled_grid, implementation));
    all_records.extend(bench_grid("scaled", &grid.scaled_grid, implementation));
    eprintln!("Benchmarked {} points", all_records.len());

    let json = serde_json::to_string(&all_records).expect("Failed to serialize results");
    println!("{}", json);
}
