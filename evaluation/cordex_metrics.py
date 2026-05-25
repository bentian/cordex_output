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
from pathlib import Path
import matplotlib.pyplot as plt
import xarray as xr

import indices
import diagnostics

DEBUG = False # Set to True to enable debugging

OUTPUT_DIR = Path("metrics_plots")
OUTPUT_DIR.mkdir(exist_ok=True)

def save_metric_plot(metric, title, filename):
    """Save metric as PNG."""

    plt.figure(figsize=(6, 4))

    # Convert Dataset -> DataArray
    if isinstance(metric, xr.Dataset):
        if len(metric.data_vars) == 0:
            plt.text(
                0.5,
                0.5,
                "Empty Dataset",
                ha="center",
                va="center",
                fontsize=16,
            )
            plt.axis("off")

        else:
            metric = next(iter(metric.data_vars.values()))

    # Plot DataArray
    if isinstance(metric, xr.DataArray):
        # Scalar
        if metric.ndim == 0:
            value = float(metric.values)

            plt.text(
                0.5,
                0.5,
                f"{value:.4f}",
                ha="center",
                va="center",
                fontsize=20,
            )
            plt.axis("off")

        # 1D line plot
        elif metric.ndim == 1:
            metric.plot()

        # 2D map/image
        elif metric.ndim == 2:
            metric.plot()

        # Higher dimensions -> average extra dims
        else:
            dims_to_mean = metric.dims[:-2]
            metric.mean(dim=dims_to_mean).plot()
    else:
        # Plain scalar
        plt.text(
            0.5,
            0.5,
            f"{float(metric):.4f}",
            ha="center",
            va="center",
            fontsize=20,
        )
        plt.axis("off")

    plt.title(title)
    plt.tight_layout()

    output_path = OUTPUT_DIR / filename
    plt.savefig(output_path, dpi=200)
    plt.close()

    print(f"Saved: {output_path}")


def compute_pr_metrics(x0: xr.Dataset, x1: xr.Dataset) -> None:
    """Compute precipitation diagnostics metrics."""

    metrics = {
        "rmse": lambda: diagnostics.rmse(
            x0, x1, var="pr", dim="time"
        ),

        "bias_sdii": lambda: diagnostics.bias_index(
            x0, x1, index_fn=indices.sdii, var="pr"
        ),

        "bias_rx1day": lambda: diagnostics.bias_index(
            x0, x1, index_fn=indices.rx1day, var="pr"
        ),

        "bias_cwd": lambda: diagnostics.bias_index(
            x0, x1, index_fn=indices.cwd, var="pr"
        ),

        "ralsd_pr": lambda: diagnostics.ralsd(
            *diagnostics.psd(x0, x1, var="pr")
        ),

        # "wd_pr": lambda: diagnostics.wasserstein_distance(
        #     x0, x1, var="pr", season="summer"
        # ),
    }

    print("\n=== PR Metrics ===")
    for name, fn in metrics.items():
        metric = fn()
        save_metric_plot(
            metric,
            title=name,
            filename=f"pr_{name}.png",
        )


def compute_tasmax_metrics(x0: xr.Dataset, x1: xr.Dataset) -> None:
    """Compute tasmax diagnostics metrics."""

    metrics = {
        "rmse": lambda: diagnostics.rmse(
            x0, x1, var="tasmax", dim="time"
        ),

        "bias_txx": lambda: diagnostics.bias_index(
            x0, x1, index_fn=indices.txx, var="tasmax"
        ),

        "bias_mean": lambda: diagnostics.bias_index(
            x0, x1, index_fn=indices.mean, var="tasmax"
        ),

        "bias_summer_days": lambda: diagnostics.bias_index(
            x0, x1, index_fn=indices.su, var="tasmax"
        ),

        "ralsd_tasmax": lambda: diagnostics.ralsd(
            *diagnostics.psd(x0, x1, var="tasmax")
        ),

        "wd_scalar": lambda: diagnostics.wasserstein_distance(
            x0, x1, var="tasmax"
        ),

        "wd_field": lambda: diagnostics.wasserstein_distance(
            x0, x1, var="tasmax", spatial=True
        ),
    }

    print("\n=== TASMAX Metrics ===")
    for name, fn in metrics.items():
        metric = fn()
        save_metric_plot(
            metric,
            title=name,
            filename=f"tasmax_{name}.png",
        )


def compute_correlation_bias(x0: xr.Dataset, x1: xr.Dataset) -> None:
    """Compute correlation bias between temperature and precipitation."""

    correlation_bias = diagnostics.bias_multivariable_correlation(
        x0,
        x1,
        var_x="tasmax",
        var_y="pr"
    )

    print("\n=== Correlation Bias ===")
    save_metric_plot(
        correlation_bias,
        title="Correlation Bias",
        filename="correlation_bias.png",
    )

def main():
    """ Compute pr & tasmax diagnostics metrics. """
    parser = argparse.ArgumentParser(description="Compute pr & tasmax diagnostics metrics.")
    parser.add_argument("target", help="Path to target/reference folder")
    parser.add_argument("prediction", help="Path to prediction folder")
    args = parser.parse_args()

    # target = "../../input/data/cordex/SA_domain/test/mid_century/target/pr_tasmax_ACCESS-CM2_2041-2060.nc"
    # prediction = "../submission/NO_OROG/SA_Domain/ESD_pseudo_reality/mid_century/imperfect/Predictions_pr_tasmax_ACCESS-CM2_2041-2060.nc"

    x0 = xr.open_dataset(args.target)
    x1 = xr.open_dataset(args.prediction).mean("member")
    if DEBUG:
        x0, x1 = x0.isel(time=slice(0, 10)), x1.isel(time=slice(0, 10))

    # compute_pr_metrics(x0, x1)
    # compute_tasmax_metrics(x0, x1)
    compute_correlation_bias(x0, x1)

    print(f"\nAll plots saved to: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
