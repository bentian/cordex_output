"""
Convert CORDEX-style prediction NetCDF files into benchmark-compliant
submission files.

This script reformats prediction datasets to match the official
CORDEX ML benchmark submission structure and metadata conventions.

Features
--------
- Maps compact model identifiers (e.g. A1, S2, N1o) to benchmark domains.
- Standardizes variable names:
    precipitation            -> pr
    max_surface_temperature  -> tasmax
- Preserves only the first 5 ensemble members.
- Renames the ensemble dimension to `member`.
- Reorders dimensions to benchmark-required layout:
    ALPS -> (time, x, y, member)
    SA/NZ -> (time, lat, lon, member)
- Applies optional de-normalization using per-model mean/scale statistics.
- Copies spatial coordinates and metadata from benchmark template files.
- Reuses the target submission file time coordinate to ensure exact
  temporal alignment with benchmark formatting.

Output
------
The generated NetCDF files are compatible with the official benchmark
submission format and can be written directly into the required
submission directory structure.

Usage
-----
python convert_nc.py <model> <src.nc> <out_dir> <out.nc>

Example
-------
python convert_nc.py \
    A1 \
    predictions.nc \
    submission_files/ALPS_Domain/ESD_pseudo_reality/mid_century/perfect \
    Predictions_pr_tasmax_CNRM-CM5_2041-2060.nc
"""

from pathlib import Path
import sys
import numpy as np
import xarray as xr

DOMAIN = {"A": "ALPS", "S": "SA", "N": "NZ"}
SPATIAL_DIMS = {
    "ALPS": ("x", "y"),
    "SA": ("lat", "lon"),
    "NZ": ("lat", "lon"),
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
    """Return mean and scale for a model/variable pair.

    Args:
        model: Model identifier (e.g. "A1", "A1o", "S2").
        var: Variable name ("pr" or "tasmax").

    Returns:
        (mean, scale) tuple.
    """
    m = model.rstrip("o")
    return MEAN[m][var], SCALE[m][var]


def convert(
    model: str,
    src_nc: str,
    out_dir: str,
    out_nc: str
) -> None:
    """
    Convert CORDEX-style prediction NetCDF files into benchmark-compliant format.
    
    Args:
        model: Model identifier (e.g. "A1", "A1o", "S2").
        src_nc: Path to the source NetCDF file.
        out_dir: Directory to save the output NetCDF file.
        out_nc: Name of the output NetCDF file.
    """

    domain = DOMAIN[model[0]]
    spatial_dims = SPATIAL_DIMS[domain]
    templates = {
        "pr": xr.open_dataset(f"./templates/pr_{domain}.nc"),
        "tasmax": xr.open_dataset(f"./templates/tasmax_{domain}.nc"),
    }

    with xr.open_dataset(src_nc, group="prediction") as pred_ds, \
         xr.open_dataset(out_dir + "/" + out_nc) as input_ds:
        # Keep first 5 ensemble members only and ensure spatial dims in correct order
        pred = (
            pred_ds.isel(ensemble=slice(0, 5))
            .rename(ensemble="member")
            .transpose("time", *spatial_dims, "member")
        )

        out = xr.Dataset(coords={"time": input_ds.time})
        for var, src_var in {
            "pr": "precipitation",
            "tasmax": "max_surface_temperature",
        }.items():
            tpl = templates[var]
            mean, scale = mean_n_scale(model, var)

            # Rename the variable and denormalize it if APPLY_DENORM is True
            da = pred[src_var].astype(np.float32).rename(var)
            if APPLY_DENORM:
                da = da * scale + mean

            # Add the coordinate information from the input
            da = da.assign_coords(
                time=input_ds.time,
                **{
                    dim: tpl[dim]
                    for dim in spatial_dims
                }
            )
            da.attrs = dict(tpl[var].attrs)

            out[var] = da

        Path(out_dir).mkdir(parents=True, exist_ok=True)
        out.to_netcdf(Path(out_dir) / out_nc)


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python convert_nc.py <model> <src.nc> <out_dir> <out.nc>")
        sys.exit(1)

    convert(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
