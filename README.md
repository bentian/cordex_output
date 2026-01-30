# CORDEX ML Prediction Conversion Utilities

This repository contains utilities for __post-processing CORDEX ML model predictions__ into a
__benchmark-compliant NetCDF format__, organizing them into the required directory structure,
and inspecting NetCDF schemas for validation and debugging.

The tools are designed to support __multiple domains, models, experiments, and ensemble members__,
and to integrate smoothly with automated submission workflows.

## Contents
- `convert_nc.py` – Convert raw prediction NetCDFs into benchmark format
- `copy-predictions.sh` – Batch conversion and directory organization script
- `dump_nc.py` – Inspect and print NetCDF schema (groups, variables, attributes)

## Requirements

- Python ≥ 3.9
- `numpy`
- `xarray`
- `netCDF4`
- Bash (for `copy-predictions.sh`)

Example installation:
```
pip install numpy xarray netCDF4
```

## `convert_nc.py`

### Purpose
Convert raw ML prediction NetCDF files into the __C__ORDEX ML-Benchmark submission format__ by:
- Selecting the first 5 ensemble members
- Renaming `ensemble → member`
- Renaming variables:
  - `precipitation → pr`
  - `max_surface_temperature → tasmax`
- Applying __per-model mean/scale normalization__
- Harmonizing spatial grids (`lat`, `lon`, `x`, `y`) using template NetCDFs
- Preserving metadata and attributes from templates

### Supported Models
| Domain | [Models](https://docs.google.com/spreadsheets/d/1Pkn9ysUWq7sR7xB51Vdf5cAhwpaYeR0sjZHiz6NqKzQ/edit?gid=1634578103#gid=1634578103) |
| :--- | :--- |
| ALPS | A1, A1o, A2, A2o |
| SA | S1, S1o, S2, S2o |
| NZ | N1, N1o, N2, N2o |

Models with an `o` suffix (e.g. `A1o`) share the same normalization parameters
as their base model (`A1`).

### Usage
```
python convert_nc.py <MODEL> <SRC_NETCDF> <OUT_NETCDF>
```
Example:
```
python convert_nc.py A1 output_0_all.nc Predictions_pr_tasmax_CNRM-CM5_1981-2000.nc
```

### Templates
The script expects domain-specific templates at:
```
./templates/
├── pr_ALPS.nc
├── pr_SA.nc
├── pr_NZ.nc
├── tasmax_ALPS.nc
├── tasmax_SA.nc
└── tasmax_NZ.nc
```

The `templates/` directory is s a local copy of the official templates provided in the
[CORDEX ML-Benchmark submission guidelines](https://github.com/WCRP-CORDEX/ml-benchmark/tree/main/format_predictions/templates).

## `copy-predictions.sh`

### Purpose
Automate __batch conversion and organization of prediction files__ across:
- Domains (ALPS / SA / NZ)
- Models (A1, A1o, A2, …)
- Experiments:
  - `ESD_pseudo_reality`
  - `Emulator_hist_future`
- GCMs (training and out-of-sample)
- Time periods (historical, mid-century, end-century)
- Perfect vs imperfect boundary conditions
- Orography vs no-orography setups

Internally, the script:
- Calls `convert_nc.py` for each prediction
- Renames outputs to benchmark-compliant filenames
- Places them into the required directory hierarchy

### Usage
```
./copy-predictions.sh <DOMAIN> <SRC_TOP_DIR> <DST_TOP_DIR>
```
Example:
```
./copy-predictions.sh ALPS /path/to/raw_outputs /path/to/submission_files
```

### Notes
- Expects raw predictions named `output_0_all.nc`
- Automatically skips missing inputs
- Prints `[OK]` or `[SKIP]` status per file

## `dump_nc.py`

### Purpose
Print a human-readable schema of a NetCDF file, including:
- Groups (recursive)
- Dimensions (with sizes and UNLIMITED flags)
- Variables (dims, shape, dtype)
- Attributes (dataset and variable level)
Useful for:
- Debugging metadata issues
- Verifying submission compliance
- Comparing converted files to templates

### Usage
```
python dump_nc.py <NETCDF_FILE>
```
Example:
```
python dump_nc.py Predictions_pr_tasmax_CNRM-CM5_1981-2000.nc
```
Example output:
```
=== NetCDF schema: Predictions_pr_tasmax_CNRM-CM5_1981-2000.nc ===

Group: /
  Dimensions:
    - time: UNLIMITED
    - member: 5
    - y: 128
    - x: 128
  Variables:
    - pr
      dims: ('member', 'time', 'y', 'x')
      shape: (5, 7305, 128, 128)
      dtype: float32
      attrs:
        - units: kg m-2 s-1
...
=== End of schema ===
```

### Typical Workflow
1. Generate raw predictions from ML models (`output_0_all.nc`)
2. Batch convert + organize:
```
./copy-predictions.sh ALPS raw_outputs submission_files
```
3. Inspect outputs:
```
python dump_nc.py submission_files/ALPS_Domain/...
```
4. Zip and submit to the CORDEX ML-Benchmark
