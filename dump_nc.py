from __future__ import annotations

from pathlib import Path
from typing import Union
from netCDF4 import Dataset


def _indent(level: int) -> str:
    return "  " * level


def _print_attrs(obj, level: int) -> None:
    for k in obj.ncattrs():
        print(f"{_indent(level)}- {k}: {getattr(obj, k)}")


def _print_dims(group: Dataset, level: int) -> None:
    if not group.dimensions:
        return
    print(f"{_indent(level)}Dimensions:")
    for name, dim in group.dimensions.items():
        size = len(dim) if not dim.isunlimited() else "UNLIMITED"
        print(f"{_indent(level+1)}- {name}: {size}")


def _print_vars(group: Dataset, level: int) -> None:
    if not group.variables:
        return
    print(f"{_indent(level)}Variables:")
    for name, var in group.variables.items():
        print(f"{_indent(level+1)}- {name}")
        print(f"{_indent(level+2)}dims: {var.dimensions}")
        print(f"{_indent(level+2)}shape: {var.shape}")
        print(f"{_indent(level+2)}dtype: {var.dtype}")
        if var.ncattrs():
            print(f"{_indent(level+2)}attrs:")
            _print_attrs(var, level + 3)


def _print_group(group: Dataset, level: int = 0, name: str = "/") -> None:
    print(f"{_indent(level)}Group: {name}")

    if group.ncattrs():
        print(f"{_indent(level+1)}Attributes:")
        _print_attrs(group, level + 2)

    _print_dims(group, level + 1)
    _print_vars(group, level + 1)

    for sub_name, sub_group in group.groups.items():
        print()
        _print_group(sub_group, level + 1, sub_name)


def print_netcdf_schema(nc_path: Union[str, Path]) -> None:
    """
    Print NetCDF schema including all groups, dimensions, variables,
    dtypes, shapes, and attributes.
    """
    nc_path = Path(nc_path)

    print(f"\n=== NetCDF schema: {nc_path} ===\n")

    with Dataset(nc_path, mode="r") as root:
        _print_group(root)

    print("\n=== End of schema ===\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Print NetCDF schema including all groups."
    )
    parser.add_argument("nc", help="Input NetCDF file")
    args = parser.parse_args()

    print_netcdf_schema(args.nc)
