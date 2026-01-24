#!/usr/bin/env bash
set -euo pipefail

# -------------------------
# CONFIG
# -------------------------
TRAINING_GCM="CNRM-CM5"
OUT_OF_SAMPLE_GCM="MPI-ESM-LR"

SRC_PRED="output_0_all.nc"
SRC_CFG="hydra_generate/config.yaml"

# -------------------------
# ARGUMENTS
# -------------------------
if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <input_dir> <output_dir>"
  exit 1
fi

IN_DIR="$1"
OUT_DIR="$2"

# Copy training metadata
# mkdir -p "$OUT_DIR/training"
# cp -r "$IN_DIR"/hydra_train/config.yaml "$IN_DIR"/tensorboard_* "$OUT_DIR/training/"

# -------------------------
# MAPPINGS
# format:
# TID | out_subdir | gcm | period
# -------------------------
MAPPINGS=(
  "T1|predictions/historical/perfect|$TRAINING_GCM|1981-2000"
  "T2|predictions/mid_century/perfect|$TRAINING_GCM|2041-2060"
  "T3|predictions/end_century/perfect|$TRAINING_GCM|2080-2099"
  "T4|predictions/historical/perfect|$OUT_OF_SAMPLE_GCM|1981-2000"
  "T5|predictions/mid_century/perfect|$OUT_OF_SAMPLE_GCM|2041-2060"
  "T6|predictions/end_century/perfect|$OUT_OF_SAMPLE_GCM|2080-2099"

  "T7|predictions/historical/imperfect|$TRAINING_GCM|1981-2000"
  "T8|predictions/mid_century/imperfect|$TRAINING_GCM|2041-2060"
  "T9|predictions/end_century/imperfect|$TRAINING_GCM|2080-2099"
  "T10|predictions/historical/imperfect|$OUT_OF_SAMPLE_GCM|1981-2000"
  "T11|predictions/mid_century/imperfect|$OUT_OF_SAMPLE_GCM|2041-2060"
  "T12|predictions/end_century/imperfect|$OUT_OF_SAMPLE_GCM|2080-2099"
)

# -------------------------
# COPY LOOP
# -------------------------
for entry in "${MAPPINGS[@]}"; do
  IFS="|" read -r TID OUT_SUBDIR GCM PERIOD <<< "$entry"

  SRC_PRED_PATH="${IN_DIR}/${TID}/${SRC_PRED}"
  SRC_CFG_PATH="${IN_DIR}/${TID}/${SRC_CFG}"

  DST_DIR="${OUT_DIR}/${OUT_SUBDIR}"
  DST_PRED="Predictions_pr_tasmax_${GCM}_${PERIOD}.nc"
  DST_CFG="config_${GCM}.yaml"

  mkdir -p "$DST_DIR"

  # prediction file
  if [ -f "$SRC_PRED_PATH" ]; then
    cp -p "$SRC_PRED_PATH" "$DST_DIR/$DST_PRED"
    echo "[OK] $SRC_PRED_PATH → $DST_DIR/$DST_PRED"
  else
    echo "[SKIP] Missing prediction: $SRC_PRED_PATH"
  fi

  # hydra config
  # if [ -f "$SRC_CFG_PATH" ]; then
  #  cp -p "$SRC_CFG_PATH" "$DST_DIR/$DST_CFG"
  #  echo "[OK] $SRC_CFG_PATH → $DST_DIR/$DST_CFG"
  # else
  #  echo "[SKIP] Missing config: $SRC_CFG_PATH"
  # fi
done

