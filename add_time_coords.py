import argparse
import xarray as xr


def add_time_from_A_to_B(nc_w_time: str, nc_wo_time: str, out_path: str):
    ds_w_time = xr.open_dataset(nc_w_time)
    ds_wo_time = xr.open_dataset(nc_wo_time)

    if ds_w_time.sizes["time"] != ds_wo_time.sizes["time"]:
        raise ValueError("Time dimension length mismatch between A and B")

    ds_out = ds_wo_time.assign_coords(time=ds_w_time.time)
    ds_out.to_netcdf(out_path)

    ds_wo_time.close()
    ds_w_time.close()


def main():
    parser = argparse.ArgumentParser(
        description="Add time coordinates from dataset A to dataset B"
    )
    parser.add_argument("path_A", help="NetCDF file with time coordinate")
    parser.add_argument("path_B", help="NetCDF file without time coordinate")
    parser.add_argument("path_C", help="Output NetCDF file")

    args = parser.parse_args()
    add_time_from_A_to_B(args.path_A, args.path_B, args.path_C)


if __name__ == "__main__":
    main()
