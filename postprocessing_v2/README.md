# CORDEX ML Prediction Conversion Utilities

Utilities for converting CORDEX ML model predictions into benchmark-compliant
NetCDF submission files and organizing them into the required directory structure.

The tools support:
- Multiple CORDEX domains
- Multiple models and experiments
- Ensemble predictions
- Automated batch conversion workflows

## Contents
- `convert_nc.py` – Convert raw prediction NetCDFs into benchmark format
- `copy-predictions.sh` – Batch conversion and directory organization script

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
Convert raw ML prediction NetCDF files into the __CORDEX ML-Benchmark submission format__ by:
- Keeping the first 5 ensemble members
- Renaming:
  - `ensemble → member`
  - `precipitation → pr`
  - `max_surface_temperature → tasmax`
- [Optional] Applying __per-model mean/scale de-normalization__
- Aligning time coordinates using predictor file
- Applying spatial grids and metadata from template files
- Writing benchmark-compliant NetCDF files

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
python convert_nc.py <MODEL> <SRC_NETCDF> <PREDICTOR_NETCDF> <OUT_NETCDF>
```
Example:
```
python convert_nc.py \
    A1 \
    output_0_all.nc \
    CNRM-CM5_1981-2000.nc \
    Predictions_pr_tasmax_CNRM-CM5_1981-2000.nc
```

### Output Format

__ALPS__

`(time, y, x, member)`

__SA/NZ__

`(time, lat, lon, member)`

__Variables:__
- `pr`
- `tasmax`

### Templates
The script expects domain-specific templates at:
```
./data/templates/
├── pr_ALPS.nc
├── pr_SA.nc
├── pr_NZ.nc
├── tasmax_ALPS.nc
├── tasmax_SA.nc
└── tasmax_NZ.nc
```

Templates provide:
- benchmark spatial grids
- coordinate variables
- metadata and attributes

The `./data/templates/` directory is copied from the official
[CORDEX ML-Benchmark repository](https://github.com/WCRP-CORDEX/ml-benchmark/tree/main/format_predictions/templates).

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


### Typical Workflow
1. Generate raw predictions from ML models (`output_0_all.nc`)
2. Batch convert + organize:
```
./copy-predictions.sh ALPS raw_outputs submission_files
```
3. Zip and submit to the CORDEX ML-Benchmark
