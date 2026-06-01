"""
Compute and visualize CORDEX evaluation metrics.

This script compares a target/reference dataset against a prediction dataset
and saves diagnostic metrics as PNG figures.

## Metrics computed

Precipitation (pr):
- RMSE
- Bias SDII (Simple Daily Intensity Index)
- Bias RX1DAY (Annual Maximum 1-Day Precipitation)
- Bias CWD (Consecutive Wet Days)
- Power Spectral Density (target and prediction)
- RALSD (Radially Averaged Log Spectral Distance)
- Wasserstein Distance (summer precipitation distribution)

Maximum Temperature (tasmax):
- RMSE
- Bias TXX (Annual Maximum Temperature)
- Bias Mean Temperature
- Bias Summer Days
- Power Spectral Density (target and prediction)
- RALSD (Radially Averaged Log Spectral Distance)
- Wasserstein Distance (scalar and spatial)

Multivariable:
- Temperature-Precipitation Correlation Bias

## Outputs

PNG figures are written to the specified output directory:

```
pr/rmse.png
pr/bias_sdii.png
...
tasmax/rmse.png
...
correlation_bias.png
```

## Usage

```
python cordex_metrics.py <target.nc> <prediction.nc>
```

Optional arguments: --output-dir <path>
                    Directory for output PNG figures (default: metrics_plots)

## Example

```
python cordex_metrics.py \
    target.nc \
    prediction.nc \
    --output-dir metrics
```

## Notes

* The prediction dataset is averaged across the 'member' dimension before metric computation.
* Metrics returning higher-dimensional outputs are automatically reduced
  to two dimensions for visualization.
* Set DEBUG=True to evaluate only the first 10 timesteps.
"""


import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import xarray as xr

import indices
import diagnostics

DEBUG = False # Set to True to enable debugging

def save_metric_plot(metric: xr.DataArray | xr.Dataset, title: str, filename: Path) -> None:
    """Save metric as PNG."""
    plt.figure(figsize=(6, 4))

    # Convert Dataset -> DataArray
    if isinstance(metric, xr.Dataset):
        if len(metric.data_vars) == 0:
            plt.text(0.5, 0.5, "Empty Dataset", ha="center", va="center", fontsize=16)
            plt.axis("off")
        else:
            metric = next(iter(metric.data_vars.values()))

    # Plot DataArray
    if isinstance(metric, xr.DataArray):
        # Scalar
        if metric.ndim == 0:
            value = float(metric.values)
            plt.text(0.5, 0.5, f"{value:.4f}", ha="center", va="center", fontsize=20)
            plt.axis("off")

        # 1D line plot or 2D map/image
        elif metric.ndim == 1 or metric.ndim == 2:
            metric.plot()

        # Higher dimensions -> average extra dims
        else:
            dims_to_mean = metric.dims[:-2]
            metric.mean(dim=dims_to_mean).plot()
    else:
        # Plain scalar
        plt.text(0.5, 0.5, f"{float(metric):.4f}", ha="center", va="center", fontsize=20)
        plt.axis("off")

    plt.title(title)
    plt.tight_layout()
    plt.savefig(filename, dpi=200)
    plt.close()

    print(f"Saved: {filename}")


def plot_pr_metrics(target_ds: xr.Dataset, pred_ds: xr.Dataset, output_dir: Path) -> None:
    """Compute precipitation diagnostics metrics and save to plots."""

    psd_target, psd_pred = diagnostics.psd(target_ds, pred_ds, var="pr")
    metrics = {
        "rmse": lambda: diagnostics.rmse(
            target_ds, pred_ds, var="pr", dim="time"
        ),

        "bias_sdii": lambda: diagnostics.bias_index(
            target_ds, pred_ds, index_fn=indices.sdii, var="pr"
        ),

        "bias_rx1day": lambda: diagnostics.bias_index(
            target_ds, pred_ds, index_fn=indices.rx1day, var="pr"
        ),

        "bias_cwd": lambda: diagnostics.bias_index(
            target_ds, pred_ds, index_fn=indices.cwd, var="pr"
        ),

        "psd_target": lambda: psd_target,
        "psd_pred": lambda: psd_pred,
        "ralsd": lambda: diagnostics.ralsd(psd_target, psd_pred),

        "wd_pr": lambda: diagnostics.wasserstein_distance(
            target_ds, pred_ds, var="pr", season="summer"
        ),
    }

    for name, fn in metrics.items():
        save_metric_plot(fn(), title=name, filename=output_dir / f"{name}.png")


def plot_tasmax_metrics(target_ds: xr.Dataset, pred_ds: xr.Dataset, output_dir: Path) -> None:
    """Compute tasmax diagnostics metrics and save to plots."""

    psd_target, psd_pred = diagnostics.psd(target_ds, pred_ds, var="tasmax")
    metrics = {
        "rmse": lambda: diagnostics.rmse(
            target_ds, pred_ds, var="tasmax", dim="time"
        ),

        "bias_txx": lambda: diagnostics.bias_index(
            target_ds, pred_ds, index_fn=indices.txx, var="tasmax"
        ),

        "bias_mean": lambda: diagnostics.bias_index(
            target_ds, pred_ds, index_fn=indices.mean, var="tasmax"
        ),

        "bias_summer_days": lambda: diagnostics.bias_index(
            target_ds, pred_ds, index_fn=indices.su, var="tasmax"
        ),

        "psd_target": lambda: psd_target,
        "psd_pred": lambda: psd_pred,
        "ralsd": lambda: diagnostics.ralsd(psd_target, psd_pred),

        "wd_scalar": lambda: diagnostics.wasserstein_distance(
            target_ds, pred_ds, var="tasmax"
        ),

        "wd_field": lambda: diagnostics.wasserstein_distance(
            target_ds, pred_ds, var="tasmax", spatial=True
        ),
    }

    for name, fn in metrics.items():
        save_metric_plot(fn(), title=name, filename=output_dir / f"{name}.png")


def plot_correlation_bias(target_ds: xr.Dataset, pred_ds: xr.Dataset, output_dir: Path) -> None:
    """Compute correlation bias between temperature and precipitation and save to plot."""
    save_metric_plot(
        diagnostics.bias_multivariable_correlation(
            target_ds, pred_ds, var_x="tasmax", var_y="pr"
        ),
        title="Correlation Bias",
        filename=output_dir / "correlation_bias.png",
    )


def main():
    """ Compute pr & tasmax diagnostics metrics. """
    parser = argparse.ArgumentParser(description="Compute pr & tasmax diagnostics metrics.")
    parser.add_argument("target", help="Path to target NetCDF file")
    parser.add_argument("prediction", help="Path to prediction NetCDF file")
    parser.add_argument(
        "--output-dir",
        default="metrics_plots",
        help="Directory to save metric PNGs",
    )
    args = parser.parse_args()

    # Get target and prediction datasets
    target_ds = xr.open_dataset(args.target)
    pred_ds = xr.open_dataset(args.prediction).mean("member")

    # target_ds = target_ds.sel(
    #     time=~((target_ds.time.dt.month == 2) & (target_ds.time.dt.day == 29))
    # )
    if DEBUG:
        target_ds, pred_ds = target_ds.isel(time=slice(0, 10)), pred_ds.isel(time=slice(0, 10))

    # Create output folder
    output_dir = Path(args.output_dir)
    for d in ["pr", "tasmax"]:
        (output_dir / d).mkdir(parents=True, exist_ok=True)

    # Compute metrics and save to plots
    plot_pr_metrics(target_ds, pred_ds, output_dir / "pr")
    plot_tasmax_metrics(target_ds, pred_ds, output_dir / "tasmax")
    plot_correlation_bias(target_ds, pred_ds, output_dir)

    print(f"\nAll plots saved to: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
