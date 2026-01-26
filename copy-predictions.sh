#!/usr/bin/env bash
set -euo pipefail

# -------------------------
# ARGUMENTS
# -------------------------
if [[ $# -ne 3 ]]; then
  echo "Usage: $0 <DOMAIN:{ALPS|NZ|SA}> <SRC_TOP_DIR> <DST_TOP_DIR>"
  exit 1
fi

DOMAIN="$1"
SRC_TOP_DIR="$2"
DST_TOP_DIR="$3"

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
    # MODELS=(A2 A2o)
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

DST_DOMAIN_DIR="${DOMAIN}_domain"
DST_DOMAIN_DIR_OROG="${DOMAIN}_domain_OROG"

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
  "T1|predictions/historical/perfect|$TRAINING_GCM|1981-2000"
  "T2|predictions/mid_century/perfect|$TRAINING_GCM|2041-2060"
  "T3|predictions/end_century/perfect|$TRAINING_GCM|2080-2099"
  # "T4|predictions/historical/perfect|$OUT_OF_SAMPLE_GCM|1981-2000"
  "T5|predictions/mid_century/perfect|$OUT_OF_SAMPLE_GCM|2041-2060"
  "T6|predictions/end_century/perfect|$OUT_OF_SAMPLE_GCM|2080-2099"

  "T7|predictions/historical/imperfect|$TRAINING_GCM|1981-2000"
  "T8|predictions/mid_century/imperfect|$TRAINING_GCM|2041-2060"
  "T9|predictions/end_century/imperfect|$TRAINING_GCM|2080-2099"
  # "T10|predictions/historical/imperfect|$OUT_OF_SAMPLE_GCM|1981-2000"
  "T11|predictions/mid_century/imperfect|$OUT_OF_SAMPLE_GCM|2041-2060"
  # "T12|predictions/end_century/imperfect|$OUT_OF_SAMPLE_GCM|2080-2099"
)

# -------------------------
# MAIN LOOP
# -------------------------
for model in "${MODELS[@]}"; do
  IN_MODEL_DIR="${SRC_TOP_DIR%/}/$model"
  OUT_MODEL_DIR="${DST_TOP_DIR%/}/$(model_subdir "$model")"

  for entry in "${MAPPINGS[@]}"; do
    IFS="|" read -r TID OUT_SUBDIR GCM PERIOD <<< "$entry"

    SRC_PRED_PATH="${IN_MODEL_DIR}/${TID}/${SRC_PRED}"
    DST_DIR="${OUT_MODEL_DIR}/${OUT_SUBDIR}"
    DST_PRED="Predictions_pr_tasmax_${GCM}_${PERIOD}.nc"

    mkdir -p "$DST_DIR"

    if [[ -f "$SRC_PRED_PATH" ]]; then
      python convert_nc.py "$DOMAIN" "$SRC_PRED_PATH" "$DST_DIR/$DST_PRED"
      echo "[OK] ($DOMAIN/$model/$TID) → $DST_DIR/$DST_PRED"
    else
      echo "[SKIP] ($DOMAIN/$model/$TID) Missing: $SRC_PRED_PATH"
    fi
  done
done

