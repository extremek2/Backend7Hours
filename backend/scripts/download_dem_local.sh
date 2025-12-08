#!/bin/bash
# DEM 파일 다운로드 (로컬 개발용)
set -e

DEM_DIR="./data/dem"
DEM_FILE="$DEM_DIR/korea_dem.tif"

mkdir -p "$DEM_DIR"

# 이미 파일이 있으면 스킵
if [ -f "$DEM_FILE" ]; then
  echo "✔️  DEM already exists → $DEM_FILE"
  ls -lh "$DEM_FILE"
  exit 0
fi

echo "🌍 Downloading Korea DEM (SRTM 30m via AWS S3)..."

# GDAL 설치 확인
if ! command -v gdalwarp &> /dev/null; then
  echo "❌ GDAL not found. Please install:"
  echo ""
  echo "  macOS:   brew install gdal"
  echo "  Ubuntu:  sudo apt-get install gdal-bin"
  echo "  Windows: conda install -c conda-forge gdal"
  echo ""
  exit 1
fi

# GDAL 환경 변수 설정 (인증 없이 S3 접근)
export AWS_NO_SIGN_REQUEST=YES
export GDAL_HTTP_UNSAFESSL=YES
export CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.vrt"

# OpenTopography S3에서 SRTM 다운로드 (인증 불필요)
echo "⬇️  Downloading... (2-5분 소요)"
gdalwarp \
  -te 124 33 132 39 \
  -tr 0.000833333 0.000833333 \
  -r bilinear \
  -co COMPRESS=LZW \
  -co TILED=YES \
  /vsis3/raster/SRTM_GL1/SRTM_GL1_srtm.vrt \
  "$DEM_FILE" \
  --config AWS_NO_SIGN_REQUEST YES \
  --config AWS_S3_ENDPOINT opentopography.s3.sdsc.edu

echo ""
echo "✅ DEM downloaded: $DEM_FILE"
ls -lh "$DEM_FILE"
echo ""
echo "📊 DEM Info:"
gdalinfo "$DEM_FILE" | grep -E "Size is|Pixel Size|Upper Left|Lower Right"

echo ""
echo "✨ Done! You can now use this DEM in your local development