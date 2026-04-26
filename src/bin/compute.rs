use bessel_rs::{
    HankelKind, Scaling as BesselRsScaling, airy, airy_b, airy_bp, airyp, bessel_i, bessel_j,
    bessel_k, bessel_y, complex_airy, complex_airy_b, complex_bessel_i, complex_bessel_j,
    complex_bessel_k, complex_bessel_y, complex_hankel1, complex_hankel2, hankel,
};
use complex_bessel::{
    Scaling, airy_raw, airyprime_raw, besseli, besseli_scaled, besselj, besselj_scaled, besselk,
    besselk_scaled, bessely, bessely_scaled, biry_raw, biryprime_raw, hankel1, hankel1_scaled,
    hankel2, hankel2_scaled,
};
use num_complex::Complex;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::env;
use std::io::{self, Read};

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
struct ResultRecord {
    grid: String,
    function: String,
    idx: usize,
    nu: f64,
    z_re: f64,
    z_im: f64,
    re: Option<f64>,
    im: Option<f64>,
    status: String,
    precision: Option<String>,
}

fn compute_function_bessel_rs(
    fname: &str,
    nu: f64,
    z: Complex<f64>,
) -> (Option<f64>, Option<f64>, String, Option<String>) {
    let result = match fname {
        "airy" => airy(z),
        "airyprime" => airyp(z),
        "biry" => airy_b(z),
        "biryprime" => airy_bp(z),
        "besselj" => bessel_j(nu, z),
        "bessely" => bessel_y(nu, z),
        "besseli" => bessel_i(nu, z),
        "besselk" => bessel_k(nu, z),
        "hankel1" => hankel(nu, z, HankelKind::First),
        "hankel2" => hankel(nu, z, HankelKind::Second),
        "airy_scaled" => complex_airy(z, false, BesselRsScaling::Scaled).map(|v| v.0),
        "airyprime_scaled" => complex_airy(z, true, BesselRsScaling::Scaled).map(|v| v.0),
        "biry_scaled" => complex_airy_b(z, false, BesselRsScaling::Scaled),
        "biryprime_scaled" => complex_airy_b(z, true, BesselRsScaling::Scaled),
        "besselj_scaled" => complex_bessel_j(z, nu, BesselRsScaling::Scaled, 1).map(|v| v.0[0]),
        "bessely_scaled" => complex_bessel_y(z, nu, BesselRsScaling::Scaled, 1).map(|v| v.0[0]),
        "besseli_scaled" => complex_bessel_i(z, nu, BesselRsScaling::Scaled, 1).map(|v| v.0[0]),
        "besselk_scaled" => complex_bessel_k(z, nu, BesselRsScaling::Scaled, 1).map(|v| v.0[0]),
        "hankel1_scaled" => complex_hankel1(z, nu, BesselRsScaling::Scaled, 1).map(|v| v.0[0]),
        "hankel2_scaled" => complex_hankel2(z, nu, BesselRsScaling::Scaled, 1).map(|v| v.0[0]),
        _ => return (None, None, "unknown_function".into(), None),
    };

    match result {
        Ok(val) => (
            Some(val.re),
            Some(val.im),
            "ok".into(),
            Some("normal".into()),
        ),
        Err(_) => (None, None, "error".into(), None),
    }
}

fn compute_function(
    fname: &str,
    nu: f64,
    z: Complex<f64>,
) -> (Option<f64>, Option<f64>, String, Option<String>) {
    // Airy _raw functions: return AiryResult with Accuracy status
    if let Some(raw_result) = match fname {
        "airy" => Some(airy_raw(z, Scaling::Unscaled)),
        "airyprime" => Some(airyprime_raw(z, Scaling::Unscaled)),
        "biry" => Some(biry_raw(z, Scaling::Unscaled)),
        "biryprime" => Some(biryprime_raw(z, Scaling::Unscaled)),
        "airy_scaled" => Some(airy_raw(z, Scaling::Exponential)),
        "airyprime_scaled" => Some(airyprime_raw(z, Scaling::Exponential)),
        "biry_scaled" => Some(biry_raw(z, Scaling::Exponential)),
        "biryprime_scaled" => Some(biryprime_raw(z, Scaling::Exponential)),
        _ => None,
    } {
        return match raw_result {
            Ok(ar) => {
                let (status, precision) = match ar.status {
                    complex_bessel::Accuracy::Normal => ("ok", "normal"),
                    complex_bessel::Accuracy::Reduced => ("reduced_precision", "reduced"),
                };
                (
                    Some(ar.value.re),
                    Some(ar.value.im),
                    status.into(),
                    Some(precision.into()),
                )
            }
            Err(complex_bessel::Error::InvalidInput) => (None, None, "invalid_input".into(), None),
            Err(complex_bessel::Error::Overflow) => (None, None, "overflow".into(), None),
            Err(complex_bessel::Error::TotalPrecisionLoss) => {
                (None, None, "total_precision_loss".into(), None)
            }
            Err(complex_bessel::Error::ConvergenceFailure) => {
                (None, None, "convergence_failure".into(), None)
            }
        };
    }

    // Non-Airy Bessel functions
    let result = match fname {
        "besselj" => besselj(nu, z),
        "bessely" => bessely(nu, z),
        "besseli" => besseli(nu, z),
        "besselk" => besselk(nu, z),
        "hankel1" => hankel1(nu, z),
        "hankel2" => hankel2(nu, z),
        "besselj_scaled" => besselj_scaled(nu, z),
        "bessely_scaled" => bessely_scaled(nu, z),
        "besseli_scaled" => besseli_scaled(nu, z),
        "besselk_scaled" => besselk_scaled(nu, z),
        "hankel1_scaled" => hankel1_scaled(nu, z),
        "hankel2_scaled" => hankel2_scaled(nu, z),
        _ => return (None, None, "unknown_function".into(), None),
    };

    match result {
        Ok(val) => (
            Some(val.re),
            Some(val.im),
            "ok".into(),
            Some("normal".into()),
        ),
        Err(complex_bessel::Error::InvalidInput) => (None, None, "invalid_input".into(), None),
        Err(complex_bessel::Error::Overflow) => (None, None, "overflow".into(), None),
        Err(complex_bessel::Error::TotalPrecisionLoss) => {
            (None, None, "total_precision_loss".into(), None)
        }
        Err(complex_bessel::Error::ConvergenceFailure) => {
            (None, None, "convergence_failure".into(), None)
        }
    }
}

fn is_airy(fname: &str) -> bool {
    matches!(
        fname,
        "airy"
            | "airyprime"
            | "biry"
            | "biryprime"
            | "airy_scaled"
            | "airyprime_scaled"
            | "biry_scaled"
            | "biryprime_scaled"
    )
}

fn process_grid(grid_name: &str, spec: &GridSpec, implementation: &str) -> Vec<ResultRecord> {
    let mut records = Vec::new();

    // Pre-compute Airy results: cache by (z_re, z_im, function) -> result
    type AiryCacheEntry = (Option<f64>, Option<f64>, String, Option<String>);
    let mut airy_cache: HashMap<(u64, u64, String), AiryCacheEntry> = HashMap::new();

    let n_re = spec.re_values.len();
    let n_im = spec.im_values.len();

    for func in &spec.functions {
        if is_airy(func) {
            // Only compute unique z points for Airy (nu-independent)
            for &re in spec.re_values.iter() {
                for &im in spec.im_values.iter() {
                    let key = (re.to_bits(), im.to_bits(), func.clone());
                    airy_cache.entry(key).or_insert_with(|| {
                        let z = Complex::new(re, im);
                        match implementation {
                            "complex-bessel" => compute_function(func, 0.0, z),
                            "bessel-rs" => compute_function_bessel_rs(func, 0.0, z),
                            _ => panic!("Unknown implementation"),
                        }
                    });
                }
            }
        }
    }

    for func in &spec.functions {
        let is_airy_fn = is_airy(func);

        for (ni, &nu) in spec.nu_values.iter().enumerate() {
            for (ri, &re) in spec.re_values.iter().enumerate() {
                for (ii, &im) in spec.im_values.iter().enumerate() {
                    let idx = ni * n_re * n_im + ri * n_im + ii;
                    let z = Complex::new(re, im);

                    let (res_re, res_im, status, precision) = if is_airy_fn {
                        let key = (re.to_bits(), im.to_bits(), func.clone());
                        airy_cache.get(&key).unwrap().clone()
                    } else {
                        match implementation {
                            "complex-bessel" => compute_function(func, nu, z),
                            "bessel-rs" => compute_function_bessel_rs(func, nu, z),
                            _ => panic!("Unknown implementation"),
                        }
                    };

                    records.push(ResultRecord {
                        grid: grid_name.to_string(),
                        function: func.clone(),
                        idx,
                        nu,
                        z_re: re,
                        z_im: im,
                        re: res_re,
                        im: res_im,
                        status,
                        precision,
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

    let mut all_records = Vec::new();

    all_records.extend(process_grid(
        "unscaled",
        &grid.unscaled_grid,
        implementation,
    ));
    all_records.extend(process_grid("scaled", &grid.scaled_grid, implementation));

    let json = serde_json::to_string(&all_records).expect("Failed to serialize results");
    println!("{}", json);
}
