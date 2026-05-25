"""
Compute the evaluation metrics for CORDEX.

Usage:
    python cordex_metrics.py <target_path> <prediction_path>

Example:
    python cordex_metrics.py /path/to/target /path/to/prediction

Metrics computed:
    - RMSE
    - Bias SDII
    - Bias RX1DAY
    - Bias CWD
    - RALSD
    - Wasserstein distance
"""

import argparse
import xarray as xr

import indices
import diagnostics


def compute_pr_metrics(x0: xr.Dataset, x1: xr.Dataset) -> None:
    """Compute precipitation diagnostics metrics."""

    # RMSE over time dimension
    rmse = diagnostics.rmse(x0, x1, var="pr", dim="time")

    # Bias of SDII
    bias_sdii = diagnostics.bias_index(
        x0,
        x1,
        index_fn=indices.sdii,
        var="pr",
    )

    # Bias of annual maximum 1-day precipitation
    bias_rx1day = diagnostics.bias_index(
        x0,
        x1,
        index_fn=indices.rx1day,
        var="pr",
    )

    # Bias of maximum wet spell length
    bias_cwd = diagnostics.bias_index(
        x0,
        x1,
        index_fn=indices.cwd,
        var="pr",
    )

    # Power Spectral Density
    psd_x0, psd_x1 = diagnostics.psd(x0, x1, var="pr")

    # Radially Averaged Log Spectral Distance
    ralsd_value = diagnostics.ralsd(psd_x0, psd_x1)

    # Wasserstein distance between precipitation distributions
    wd_pr = diagnostics.wasserstein_distance(
        x0,
        x1,
        var="pr",
        season="summer",
    )

    # Print metrics
    print("\n=== Metrics ===")
    print(f"RMSE:\n{rmse}\n")
    print(f"Bias SDII:\n{bias_sdii}\n")
    print(f"Bias RX1DAY:\n{bias_rx1day}\n")
    print(f"Bias CWD:\n{bias_cwd}\n")
    print(f"RALSD:\n{ralsd_value}\n")
    print(f"Wasserstein Distance (summer precipitation):\n{wd_pr}\n")


def compute_tasmax_metrics(x0: xr.Dataset, x1: xr.Dataset) -> None:
    """Compute tasmax diagnostics metrics."""

    rmse = diagnostics.rmse(x0, x1, var="tasmax", dim="time")

    bias_txx = diagnostics.bias_index(
        x0, x1, index_fn=indices.txx, var="tasmax"
    )

    bias_mean = diagnostics.bias_index(
        x0, x1, index_fn=indices.mean, var="tasmax"
    )

    bias_summer_days = diagnostics.bias_index(
        x0, x1, index_fn=indices.su, var="tasmax"
    )

    psd_x0, psd_x1 = diagnostics.psd(x0, x1, var="tasmax")

    ralsd_value = diagnostics.ralsd(psd_x0, psd_x1)

    wd_scalar = diagnostics.wasserstein_distance(
        x0, x1, var="tasmax"
    )

    wd_field = diagnostics.wasserstein_distance(
        x0, x1, var="tasmax", spatial=True
    )

    print("\n=== tasmax Metrics ===")
    print(f"RMSE:\n{rmse}\n")
    print(f"Bias TXX:\n{bias_txx}\n")
    print(f"Bias Mean:\n{bias_mean}\n")
    print(f"Bias Summer Days:\n{bias_summer_days}\n")
    print(f"RALSD:\n{ralsd_value}\n")
    print(f"Wasserstein Distance Scalar:\n{wd_scalar}\n")
    print(f"Wasserstein Distance Field:\n{wd_field}\n")


def main():
    """ Compute pr & tasmax diagnostics metrics. """
    parser = argparse.ArgumentParser(description="Compute pr & tasmax diagnostics metrics.")
    parser.add_argument("target", help="Path to target/reference folder")
    parser.add_argument("prediction", help="Path to prediction folder")
    args = parser.parse_args()

    x0 = xr.open_dataset(args.target)
    x1 = xr.open_dataset(args.prediction)

    compute_pr_metrics(x0, x1)
    compute_tasmax_metrics(x0, x1)

    # Compute correlation bias between temperature and precipitation
    correlation_bias = diagnostics.bias_multivariable_correlation(
        x0,
        x1,
        var_x="tasmax",
        var_y="pr"
    )
    print("\n=== Correlation Bias ===")
    print(f"Correlation Bias:\n{correlation_bias}\n")


if __name__ == "__main__":
    main()
