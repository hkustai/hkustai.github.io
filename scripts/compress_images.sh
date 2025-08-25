#!/usr/bin/env bash
# compress-safe-color-mac.sh
# 默认只处理 git 新增 PNG/JPEG；-l 允许“尽量保真”的有损（仅 JPEG），不做体积上限。

set -euo pipefail

IMG_DIR="${IMG_DIR:-../members/images}"
MODE="added"           # added|all
PARALLEL="auto"        # auto 或数字
LOSSY=false            # -l 开启后，对 JPEG 做温和有损（保 ICC/EXIF）

usage() {
  echo "Usage: $0 [-d DIR] [-m added|all] [-p PARALLEL] [-l]"
  echo "  -d DIR        目标目录（默认 ../members/images）"
  echo "  -m MODE       'added'(默认) 或 'all'"
  echo "  -p PARALLEL   并行度：auto(默认) 或数字"
  echo "  -l            允许有损（仅 JPEG，默认质量 90；可设 JPEG_QUALITY 覆盖）"
  exit 1
}

# 选项解析
while getopts ":d:m:p:lh" opt; do
  case "$opt" in
    d) IMG_DIR="$OPTARG" ;;
    m) MODE="$OPTARG" ;;
    p) PARALLEL="$OPTARG" ;;
    l) LOSSY=true ;;
    h) usage ;;
    :) echo "缺少参数: -$OPTARG"; usage ;;   # 比如 -d 少了目录
    \?) echo "未知参数: -$OPTARG"; usage ;;
  esac
done
shift $((OPTIND-1))

# 依赖：无损必须有 pngcrush/jpegtran；有损时额外需要 jpegoptim
need=(file pngcrush jpegtran git xargs stat)
$LOSSY && need+=(jpegoptim)
for c in "${need[@]}"; do
  command -v "$c" >/dev/null || { echo "缺少命令: $c"; exit 1; }
done

# 并行度（mac）
if [[ "$PARALLEL" == "auto" ]]; then
  PARALLEL="$(sysctl -n hw.ncpu 2>/dev/null || echo 1)"
fi
[[ "$PARALLEL" =~ ^[0-9]+$ ]] || PARALLEL=1
[ "$PARALLEL" -ge 1 ] || PARALLEL=1

# 目录
[ -d "$IMG_DIR" ] || { echo "目录不存在：$IMG_DIR"; exit 1; }

TMP_DIR="$(mktemp -d)"
LIST_TGT="$TMP_DIR/targets.zlist"
RESULTS="$TMP_DIR/results.log"

collect_added() {
  local list_all="$TMP_DIR/all.zlist"; : > "$list_all"
  git diff --cached --name-only -z --diff-filter=AM -- "$IMG_DIR" >>"$list_all" || true
  git ls-files --others -z --exclude-standard -- "$IMG_DIR"     >>"$list_all" || true
  if [[ ! -s "$list_all" ]]; then
    local cur base range
    cur="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)"
    if git rev-parse --verify -q "origin/$cur" >/dev/null; then
      base="$(git merge-base "origin/$cur" HEAD)"; range="$base..HEAD"
    else
      range="HEAD^..HEAD"
    fi
    git diff --name-only -z --diff-filter=A $range -- "$IMG_DIR" >>"$list_all" || true
  fi
  while IFS= read -r -d '' f; do
    case "$f" in
      *.png|*.PNG|*.jpg|*.JPG|*.jpeg|*.JPEG) printf '%s\0' "$f" >>"$LIST_TGT" ;;
      *) : ;;
    esac
  done < "$list_all"
}

collect_all() {
  find "$IMG_DIR" -type f \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' \) -print0 >>"$LIST_TGT"
}

if [[ "$MODE" == "all" ]]; then collect_all; else MODE="added"; collect_added; fi

COUNT=0
if [[ -s "$LIST_TGT" ]]; then
  COUNT="$(tr -cd '\0' < "$LIST_TGT" | wc -c | awk '{print $1}')"
fi
if [ "$COUNT" -eq 0 ]; then
  echo "未找到待处理图片（模式：${MODE:-added})"
  rm -rf "$TMP_DIR"; exit 0
fi

echo "模式：$MODE"
echo "并行任务：$PARALLEL"
echo "允许有损：$LOSSY"
echo "即将处理 $COUNT 个文件 …"

compress_one() {
  f="$1"
  [[ -f "$f" ]] || exit 0

  mime="$(file -b --mime-type "$f" || echo '')"
  case "$mime" in
    image/png|image/x-png) kind="png" ;;
    image/jpeg|image/pjpeg) kind="jpg" ;;
    *) echo "跳过(类型): $(basename "$f") -> $mime"; exit 0 ;;
  esac

  bytes_of() { stat -f%z "$1"; }
  kb_of()    { local b; b="$(bytes_of "$1")"; echo $(( (b + 1023)/1024 )); }

  b0_bytes="$(bytes_of "$f")"; b0_kb="$(kb_of "$f")"

  # 先做无损，且保留颜色相关信息（JPEG: 保留 ICC/EXIF）
  tmp_lossless="$(mktemp "$TMP_DIR"/tmp.XXXXXX)"
  if [[ "$kind" == "png" ]]; then
    pngcrush -brute -q "$f" "$tmp_lossless" >/dev/null 2>&1 || true
  else
    # 关键改动：-copy all（保留 ICC/EXIF），避免颜色偏差
    jpegtran -optimize -progressive -copy all "$f" > "$tmp_lossless" || true
  fi
  if [[ -s "$tmp_lossless" ]] && [ "$(bytes_of "$tmp_lossless")" -lt "$b0_bytes" ]; then
    mv "$tmp_lossless" "$f"
    b0_bytes="$(bytes_of "$f")"; b0_kb="$(kb_of "$f")"
  else
    rm -f "$tmp_lossless"
  fi

  # 有损阶段（仅 JPEG），目标：尽量保真，不限制体积
  if [[ "$kind" == "jpg" && "$LOSSY" == "true" ]]; then
    q="${JPEG_QUALITY:-90}"  # 可通过环境变量微调
    tmp_j="$(mktemp "$TMP_DIR"/tmp.XXXXXX)"
    cp "$f" "$tmp_j"
    # 不剥离元数据；保留 ICC/EXIF；使用渐进式
    out="$(mktemp "$TMP_DIR"/tmp.XXXXXX)"
    jpegoptim --max="$q" --all-progressive --strip-none --keep-icc --keep-exif --stdout "$tmp_j" > "$out" 2>/dev/null || true
    if [[ -s "$out" ]] && [ "$(bytes_of "$out")" -lt "$(bytes_of "$f")" ]; then
      mv "$out" "$f"
    else
      rm -f "$out"
    fi
    rm -f "$tmp_j"
  fi

  a_bytes="$(bytes_of "$f")"; a_kb="$(kb_of "$f")"
  saved=$(( b0_kb - a_kb ))
  denom=$(( b0_kb > 0 ? b0_kb : 1 ))
  pct=$(( 100 * a_kb / denom ))
  printf "%s|%d|%d|%d|%d\n" "$f" "$b0_kb" "$a_kb" "$saved" "$pct" >> "$RESULTS"
  printf "✓ %s: %dKB → %dKB (saved %dKB, %d%%)\n" "$(basename "$f")" "$b0_kb" "$a_kb" "$saved" "$pct"
}
export -f compress_one
export TMP_DIR RESULTS LOSSY

# 并行执行（NUL 安全）
xargs -0 -n1 -P"$PARALLEL" bash -c 'compress_one "$@"' _ < "$LIST_TGT"

# 汇总
tb=0; ta=0
if [[ -f "$RESULTS" ]]; then
  echo
  printf "%-40s %12s %12s %12s %8s\n" "file" "before(KB)" "after(KB)" "saved(KB)" "ratio"
  while IFS="|" read -r f b a s p; do
    printf "%-40s %12d %12d %12d %7d%%\n" "$(basename "$f")" "$b" "$a" "$s" "$p"
    tb=$((tb + b)); ta=$((ta + a))
  done < "$RESULTS"
fi
ts=$((tb - ta)); den=$(( tb>0 ? tb : 1 )); tp=$(( 100 * ta / den ))
printf "%-40s %12d %12d %12d %7d%%\n" "TOTAL" "$tb" "$ta" "$ts" "$tp"

rm -rf "$TMP_DIR"