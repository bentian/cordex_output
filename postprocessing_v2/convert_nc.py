"""
Convert CORDEX-style prediction NetCDF files into benchmark-compliant
submission files.

This script:
- maps model identifiers (A1, S2, N1o, ...) to benchmark domains
- standardizes dimensions and coordinates
- renames prediction variables to benchmark names
- optionally de-normalizes predictions using per-model statistics
- aligns time/grid coordinates with a reference NetCDF file
- applies metadata from official template files
- writes benchmark-compatible NetCDF output

Output dimensions:
    ALPS -> (time, x, y, member)
    SA/NZ -> (time, lat, lon, member)

Usage:
    python convert_nc.py <model> <src.nc> <ref.nc> <out.nc>

Example:
    python convert_nc.py \
        A1 \
        predictions.nc \
        reference.nc \
        output.nc
"""
from pathlib import Path
import sys
import numpy as np
import xarray as xr

DOMAIN_INFO = {
    "A": ("ALPS", ("x", "y")),
    "S": ("SA", ("lat", "lon")),
    "N": ("NZ", ("lat", "lon")),
}
VAR_MAP = {
    "pr": "precipitation",
    "tasmax": "max_surface_temperature",
}

APPLY_DENORM = True
MEAN = {
    "A1": {"pr": 3.0094404220581055, "tasmax": 287.3564147949219},
    "A2": {"pr": 3.023773670196533, "tasmax": 289.5425720214844},
    "S1": {"pr": 3.1895868716998854, "tasmax": 295.9818420410156},
    "S2": {"pr": 3.197072799236965, "tasmax": 298.7344055175781},
    "N1": {"pr": 3.3502800487977384, "tasmax": 287.85821533203125},
    "N2": {"pr": 3.4224649266576477, "tasmax": 289.825439453125},
}
SCALE = {
    "A1": {"pr": 7.059685707092285, "tasmax": 8.284003257751465},
    "A2": {"pr": 7.377854824066162, "tasmax": 8.576455116271973},
    "S1": {"pr": 9.934561096786277, "tasmax": 6.739269256591797},
    "S2": {"pr": 11.157043537049379, "tasmax": 7.496180534362793},
    "N1": {"pr": 8.695985226126469, "tasmax": 3.914102077484131},
    "N2": {"pr": 9.727775223067006, "tasmax": 4.607882022857666},
}

def mean_n_scale(model: str, var: str) -> tuple[float, float]:
    """Return mean and scale for a model/variable pair."""
    m = model.rstrip("o")
    return MEAN[m][var], SCALE[m][var]


def convert(
    model: str,
    src_nc: str,
    ref_nc: str,
    out_nc: str
) -> None:
    """
    Convert CORDEX-style prediction NetCDF files into benchmark-compliant format.

    Args:
        model: Model identifier (e.g. "A1", "A1o", "S2").
        src_nc: Path to the source NetCDF file.
        ref_nc: Path to the reference NetCDF file.
        out_nc: Path to the output NetCDF file.
    """

    domain, spatial_dims = DOMAIN_INFO[model[0]]
    templates = {
        var: xr.open_dataset(f"../data/templates/{var}_{domain}.nc")
        for var in VAR_MAP
    }

    with xr.open_dataset(src_nc, group="prediction") as pred_ds, \
         xr.open_dataset(ref_nc) as ref_ds:

        # Check whether time dimension length matches
        if pred_ds.sizes["time"] != ref_ds.sizes["time"]:
            raise ValueError("Time dimension length mismatch between prediction and reference")

        # Keep first 5 ensemble members only and ensure spatial dims in correct order
        pred_ds = (
            pred_ds.isel(ensemble=slice(0, 5))
            .rename(ensemble="member")
            .transpose("time", "y", "x", "member")
        )

        out = xr.Dataset(coords={"time": ref_ds.time})
        for var, src_var in VAR_MAP.items():
            tpl = templates[var]
            src = pred_ds[src_var].astype(np.float32).rename(var)

            da = xr.DataArray(
                data=src.values,
                dims=("time", *spatial_dims, "member"),
                coords={
                    "time": ref_ds.time,
                    **{dim: tpl[dim] for dim in spatial_dims},
                    "member": src["member"],
                },
                name=var,
                attrs=dict(templates[var][var].attrs),
            )

            # Denormalize it if APPLY_DENORM is True
            if APPLY_DENORM:
                mean, scale = mean_n_scale(model, var)
                da = da * scale + mean

            out[var] = da

        Path(out_nc).parent.mkdir(parents=True, exist_ok=True)
        out.to_netcdf(out_nc)


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python convert_nc.py <model> <src.nc> <ref.nc> <out.nc>")
        sys.exit(1)

    convert(*sys.argv[1:])
