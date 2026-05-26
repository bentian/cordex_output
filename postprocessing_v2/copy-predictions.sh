#!/usr/bin/env bash
set -euo pipefail

# -------------------------
# ARGUMENTS
# -------------------------
if [[ $# -ne 4 ]]; then
  echo "Usage: $0 <DOMAIN:{ALPS|NZ|SA}> <SRC_TOP_DIR> <REF_TOP_DIR> <DST_TOP_DIR>"
  exit 1
fi

DOMAIN="$1"
SRC_TOP_DIR="$2"
REF_TOP_DIR="$3"
DST_TOP_DIR="$4"

# -------------------------
# DOMAIN → GCM CONFIG
# -------------------------
case "$DOMAIN" in
  ALPS)
    TRAINING_GCM="CNRM-CM5"
    OUT_OF_SAMPLE_GCM="MPI-ESM-LR"
    ;;
  SA)
    TRAINING_GCM="ACCESS-CM2"
    OUT_OF_SAMPLE_GCM="NorESM2-MM"
    ;;
  NZ)
    TRAINING_GCM="ACCESS-CM2"
    OUT_OF_SAMPLE_GCM="EC-Earth3"
    ;;
  *)
    echo "Invalid DOMAIN: $DOMAIN (must be ALPS, NZ, or SA)" >&2
    exit 1
    ;;
esac

SRC_PRED="output_0_all.nc"

# -------------------------
# DOMAIN → MODELS
# -------------------------
case "$DOMAIN" in
  ALPS)
    MODELS=(A1 A1o A2 A2o)
    ;;
  NZ)
    MODELS=(N1 N1o N2 N2o)
    ;;
  SA)
    MODELS=(S1 S1o S2 S2o)
    ;;
  *)
    echo "Invalid DOMAIN: $DOMAIN (must be ALPS, NZ, or SA)" >&2
    exit 1
    ;;
esac

DST_DOMAIN_DIR="NO_OROG/${DOMAIN}_Domain"
DST_DOMAIN_DIR_OROG="OROG/${DOMAIN}_Domain"

# -------------------------
# MODEL → DST SUBFOLDER (DST only)
# -------------------------
model_subdir() {
  case "$1" in
    *1)  echo "$DST_DOMAIN_DIR/ESD_pseudo_reality" ;;
    *1o) echo "$DST_DOMAIN_DIR_OROG/ESD_pseudo_reality" ;;
    *2)  echo "$DST_DOMAIN_DIR/Emulator_hist_future" ;;
    *2o) echo "$DST_DOMAIN_DIR_OROG/Emulator_hist_future" ;;
  esac
}

# -------------------------
# TID → OUTPUT MAPPINGS
# -------------------------
MAPPINGS=(
  "T1 historical perfect   $TRAINING_GCM      1981-2000"
  "T2 mid_century perfect  $TRAINING_GCM      2041-2060"
  "T3 end_century perfect  $TRAINING_GCM      2080-2099"
  # "T4 historical perfect $OUT_OF_SAMPLE_GCM 1981-2000"
  "T5 mid_century perfect  $OUT_OF_SAMPLE_GCM 2041-2060"
  "T6 end_century perfect  $OUT_OF_SAMPLE_GCM 2080-2099"

  "T7 historical imperfect   $TRAINING_GCM      1981-2000"
  "T8 mid_century imperfect  $TRAINING_GCM      2041-2060"
  "T9 end_century imperfect  $TRAINING_GCM      2080-2099"
  # "T10 historical imperfect $OUT_OF_SAMPLE_GCM 1981-2000"
  "T11 mid_century imperfect $OUT_OF_SAMPLE_GCM 2041-2060"
  # "T12 end_century imperfect $OUT_OF_SAMPLE_GCM 2080-2099"
)

# -------------------------
# MAIN LOOP
# -------------------------
for model in "${MODELS[@]}"; do
  in_dir="${SRC_TOP_DIR%/}/$model"
  out_dir="${DST_TOP_DIR%/}/$(model_subdir "$model")"

  for entry in "${MAPPINGS[@]}"; do
    read -r tid period condition gcm years <<< "$entry"

    ref_nc="${REF_TOP_DIR%/}/${DOMAIN}_domain/test/$period/predictors/$condition/${gcm}_${years}.nc"
    src_nc="$in_dir/$tid/$SRC_PRED"
    dst_dir="$out_dir/$period/$condition"
    dst_nc="$dst_dir/Predictions_pr_tasmax_${gcm}_${years}.nc"

    [[ -f "$ref_nc" ]] || { echo "Missing REF_NC: $ref_nc"; exit 1; }

    if [[ -f "$src_nc" ]]; then
      mkdir -p "$dst_dir"
      python convert_nc.py "$model" "$src_nc" "$ref_nc" "$dst_nc"
      echo -e "[OK] ($DOMAIN/$model/$tid) -> $dst_nc\n     w/ REF: $ref_nc"
    else
      echo "[SKIP] ($DOMAIN/$model/$tid) Missing: $src_nc"
    fi
  done
done

