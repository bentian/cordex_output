import sys
import numpy as np
import xarray as xr

GRID = ["lat", "lon", "x", "y"]
DOMAIN = {"A": "ALPS", "S": "SA", "N": "NZ"}

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
    m = model.rstrip("o")
    return MEAN[m][var], SCALE[m][var]

def replace_grid(dst: xr.Dataset, tpl: xr.Dataset) -> xr.Dataset:
    dst = dst.drop_vars(GRID, errors="ignore").assign({v: tpl[v] for v in GRID if v in tpl})
    for v in GRID:
        if v in dst and v in tpl:
            dst[v].attrs = dict(tpl[v].attrs)
    return dst.set_coords([v for v in GRID if v in dst])

def make_var(src: xr.DataArray, name: str,
             tpl_var: xr.DataArray, root: xr.Dataset,
             mean: float, scale: float) -> xr.DataArray:
    da = (src * scale + mean).astype(np.float32).rename(name)
    da.attrs = dict(tpl_var.attrs)

    lat, lon = root.get("lat"), root.get("lon")
    if lat is not None and lon is not None:
        # assign only when compatible (2D y/x or 1D mapped onto y/x)
        if set(lat.dims) <= set(da.dims) and set(lon.dims) <= set(da.dims):
            da = da.assign_coords(lat=lat, lon=lon)
        elif lat.ndim == lon.ndim == 1 and "y" in da.dims and "x" in da.dims:
            lat2 = lat.rename({lat.dims[0]: "y"}) if lat.size == da.sizes["y"] else lat
            lon2 = lon.rename({lon.dims[0]: "x"}) if lon.size == da.sizes["x"] else lon
            if set(lat2.dims) <= set(da.dims) and set(lon2.dims) <= set(da.dims):
                da = da.assign_coords(lat=lat2, lon=lon2)

    return da

def convert(model: str, src_nc: str, out_nc: str,
            pr_name="precipitation",
            tas_name="max_surface_temperature") -> None:
    dom = DOMAIN[model[0]]
    tpl_pr_nc, tpl_ta_nc = f"./templates/pr_{dom}.nc", f"./templates/tasmax_{dom}.nc"

    with xr.open_dataset(tpl_pr_nc) as tpl_pr, \
         xr.open_dataset(tpl_ta_nc) as tpl_ta, \
         xr.open_dataset(src_nc, group="/") as root, \
         xr.open_dataset(src_nc, group="prediction") as pred:

        # --- Build new root (grid/time standardized to template) ---
        out_root = replace_grid(root.copy(deep=False), tpl_pr)
        out_root = replace_grid(out_root, tpl_ta)

        # --- Build new prediction group dataset (preserve first 5 ensembles, add/rename vars) ---
        out_pred = (
            pred.isel(ensemble=slice(0, 5))
            .copy(deep=False)
            .rename({"ensemble": "member"})
        )

        for var, src_name, tpl in [
            ("pr", pr_name, tpl_pr["pr"]),
            ("tasmax", tas_name, tpl_ta["tasmax"]),
        ]:
            out_pred[var] = make_var(
                out_pred[src_name], var, tpl, out_root, *mean_n_scale(model, var)
            )

        out_pred = out_pred.drop_vars([pr_name, tas_name])

        # --- Write output ---
        out_pred.to_netcdf(out_nc, mode="w")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python convert_nc.py <model> <src.nc> <out.nc>")
        sys.exit(1)

    convert(sys.argv[1], sys.argv[2], sys.argv[3])
