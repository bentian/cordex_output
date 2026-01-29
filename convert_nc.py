import sys
import numpy as np
import xarray as xr

GRID_TIME_VARS = ["lat", "lon", "x", "y"]

def _force_replace_vars(dst: xr.Dataset, tpl: xr.Dataset, names=GRID_TIME_VARS) -> xr.Dataset:
    """
    Replace variables in dst with the same-named variables from tpl,
    avoiding xarray MergeError by dropping conflicts first and
    explicitly setting coords.
    """
    # 1) Drop any conflicting variables / coords in dst
    to_drop = [n for n in names if (n in dst.variables)]
    if to_drop:
        dst = dst.drop_vars(to_drop, errors="ignore")

    # 2) Assign from template
    assign_dict = {n: tpl[n] for n in names if n in tpl.variables}
    if assign_dict:
        dst = dst.assign(assign_dict)

    # 3) Ensure they are coords (template expects these to behave like coords)
    coord_names = [n for n in names if n in dst.variables]
    if coord_names:
        dst = dst.set_coords(coord_names)

    # 4) Copy attrs
    for n in names:
        if n in tpl.variables and n in dst.variables:
            dst[n].attrs = dict(tpl[n].attrs)

    return dst


def _make_var(src, name, tpl, root, *, mean=0.0, scale=1.0):
    # print(mean, scale)
    da = (src * scale + mean).astype(np.float32).rename(name)
    da.attrs = dict(tpl.attrs)

    # Attach lat/lon only if they match da's spatial dims
    if "lat" in root and "lon" in root:
        lat = root["lat"]
        lon = root["lon"]

        # Case ALPS: template-style 2D lat/lon on (y, x)
        if set(lat.dims).issubset(da.dims) and set(lon.dims).issubset(da.dims):
            da = da.assign_coords(lat=lat, lon=lon)

        # Case SA/NZ: 1D lat/lon on (y) and (x) (common in some grids)
        elif lat.ndim == 1 and lon.ndim == 1 and "y" in da.dims and "x" in da.dims:
            # If they are aligned to y/x, attach them to those dims
            if lat.sizes.get(lat.dims[0], None) == da.sizes["y"]:
                lat = lat.rename({lat.dims[0]: "y"})
            if lon.sizes.get(lon.dims[0], None) == da.sizes["x"]:
                lon = lon.rename({lon.dims[0]: "x"})

            if set(lat.dims).issubset(da.dims) and set(lon.dims).issubset(da.dims):
                da = da.assign_coords(lat=lat, lon=lon)
            # else: skip silently (dims still don't match)

        # else: skip silently (root lat/lon dims incompatible)

    return da


def convert_predictions_keep_ensemble(
    model: str,
    src_nc: str,
    out_nc: str,
    *,
    src_pr_name: str = "precipitation",
    src_tasmax_name: str = "max_surface_temperature"
):
    """
    Convert SOURCE prediction variables into template-style variable names/attrs,
    but KEEP ensemble dimension.

    SOURCE:
      /prediction/precipitation(ensemble,time,y,x)
      /prediction/max_surface_temperature(ensemble,time,y,x)

    OUTPUT:
      /prediction/pr(ensemble,time,y,x) and /prediction/tasmax(ensemble,time,y,x)
      with TEMPLATE attrs (except template doesn't have ensemble; we keep it).
      Also overwrite root lat/lon/x/y to match template variables + attrs.
    """
    # per-model normalization params
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

    def ms(model: str, var: str):
        ds_idx = model.rstrip("o")
        return MEAN.get(ds_idx, {}).get(var, 0.0), SCALE.get(ds_idx, {}).get(var, 1.0)

    # model -> domain
    DOMAIN_BY_PREFIX = {"A": "ALPS", "S": "SA", "N": "NZ"}
    domain = DOMAIN_BY_PREFIX[model[0]]  # model like "A1", "S3", "N2"

    tpl_pr_nc=f"./templates/pr_{domain}.nc"
    tpl_tasmax_nc=f"./templates/tasmax_{domain}.nc"

    with xr.open_dataset(tpl_pr_nc) as tpl_pr, \
        xr.open_dataset(tpl_tasmax_nc) as tpl_ta, \
        xr.open_dataset(src_nc, group="/") as src_root, \
        xr.open_dataset(src_nc, group="prediction") as src_pred:

        # --- Build new root (grid/time standardized to template) ---
        out_root = src_root.copy(deep=False)
        out_root = _force_replace_vars(out_root, tpl_pr)
        out_root = _force_replace_vars(out_root, tpl_ta)

        # --- Build new prediction group dataset (preserve everything, add/rename vars) ---
        out_pred = src_pred.copy(deep=False).rename({"ensemble": "member"})

        for var, src_name, tpl in [
            ("pr", src_pr_name, tpl_pr["pr"]),
            ("tasmax", src_tasmax_name, tpl_ta["tasmax"]),
        ]:
            m, s = ms(model, var)
            out_pred[var] = _make_var(
                out_pred[src_name], var, tpl, out_root, mean=m, scale=s
            )

        out_pred = out_pred.drop_vars([src_pr_name, src_tasmax_name])

        # --- Write output ---
        out_pred.to_netcdf(out_nc, mode="w")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python convert_nc.py <domain> <src_file.nc> <dst_file.nc>")
        sys.exit(1)

    model = sys.argv[1]
    src_nc = sys.argv[2]
    out_nc = sys.argv[3]

    convert_predictions_keep_ensemble(
        model=model,
        src_nc=src_nc,
        out_nc=out_nc,
    )

    # print(f"Wrote: {out_nc} for {domain}")
