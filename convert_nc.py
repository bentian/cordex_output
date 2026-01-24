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


def _make_var(src, name, tpl, root):
    da = src.astype(np.float32).rename(name)
    da.attrs = dict(tpl.attrs)
    if "lat" in root and "lon" in root:
        da = da.assign_coords(lat=root["lat"], lon=root["lon"])
    return da


def convert_predictions_keep_ensemble(
    src_nc: str,
    tpl_pr_nc: str,
    tpl_tasmax_nc: str,
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
      Also overwrite root time/lat/lon/x/y to match template variables + attrs.

    Keeps ALL other groups/vars (e.g., /input, other /prediction vars if any).
    """

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

        pr_ens = _make_var(out_pred[src_pr_name], "pr", tpl_pr["pr"], out_root)
        ta_ens = _make_var(out_pred[src_tasmax_name], "tasmax", tpl_ta["tasmax"], out_root)
        out_pred.update({"pr": pr_ens, "tasmax": ta_ens})

        out_pred = out_pred.drop_vars([src_pr_name, src_tasmax_name])

        # --- Write output, preserving groups ---
        # 1) write root
        # out_root.to_netcdf(out_nc, mode="w")

        # 2) write prediction group
        # out_pred.to_netcdf(out_nc, mode="a", group=src_pred_group)
        out_pred.to_netcdf(out_nc, mode="w")

        # 3) write input group unchanged
        # src_inp.to_netcdf(out_nc, mode="a", group="input")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python convert_nc.py <domain> <src_file.nc> <dst_file.nc>")
        sys.exit(1)

    domain = sys.argv[1]
    src_nc = sys.argv[2]
    out_nc = sys.argv[3]

    convert_predictions_keep_ensemble(
        src_nc=src_nc,
        tpl_pr_nc=f"./templates/pr_{domain}.nc",
        tpl_tasmax_nc=f"./templates/tasmax_{domain}.nc",
        out_nc=out_nc,
    )

    print(f"Wrote: {out_nc} for {domain}")
