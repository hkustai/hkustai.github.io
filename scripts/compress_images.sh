#!/usr/bin/env bash
# 用 pngcrush (PNG) 和 jpegtran (JPEG) 做无损压缩

set -euo pipefail

DIR="${1:-../members/images}"          # 目标目录（可传参覆盖）
PARALLEL="${2:-auto}"                   # 并行度：auto 或数字

# 依赖检查
need=()
for c in file pngcrush jpegtran xargs stat; do command -v "$c" >/dev/null || need+=("$c"); done
if ((${#need[@]})); then
  echo "缺少依赖：${need[*]}"
  echo "Debian/Ubuntu 可安装：sudo apt-get update && sudo apt-get install -y pngcrush libjpeg-turbo-progs file"
  exit 1
fi

# 并行度
if [[ "$PARALLEL" == "auto" ]]; then
  PARALLEL="$(nproc 2>/dev/null || getconf _NPROCESSORS_ONLN 2>/dev/null || echo 1)"
fi
[[ "$PARALLEL" =~ ^[0-9]+$ ]] && [[ "$PARALLEL" -ge 1 ]] || PARALLEL=1

# 收集文件
if [[ ! -d "$DIR" ]]; then echo "目录不存在：$DIR"; exit 1; fi
mapfile -d '' FILES < <(find "$DIR" -type f \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' \) -print0)
TOTAL=${#FILES[@]}
if (( TOTAL == 0 )); then echo "没有找到 PNG/JPG 文件"; exit 0; fi

echo "目录：$DIR"
echo "发现 $TOTAL 张图片，使用 $PARALLEL 个并行任务"

TMP_DIR="$(mktemp -d)"
RESULTS="$TMP_DIR/results.log"

compress_one() {
  f="$1"
  [[ -f "$f" ]] || exit 0

  mime="$(file -b --mime-type "$f" || echo '')"
  case "$mime" in
    image/png|image/x-png|image/jpeg|image/pjpeg) ;;
    *) echo "跳过 $(basename "$f") ：真实类型 $mime（非 PNG/JPEG）"; exit 0 ;;
  esac

  tmp="$(mktemp -p "$TMP_DIR")"
  b=$(stat -c%s "$f"); bk=$(( (b + 1023) / 1024 ))

  if [[ "$mime" == image/png* ]]; then
    pngcrush -brute -q "$f" "$tmp" >/dev/null 2>&1 || { rm -f "$tmp"; exit 0; }
  else
    jpegtran -optimize -progressive -copy none "$f" > "$tmp" || { rm -f "$tmp"; exit 0; }
  fi

  # 仅当更小才覆盖
  if [[ -s "$tmp" ]] && [[ "$(stat -c%s "$tmp")" -lt "$b" ]]; then
    mv "$tmp" "$f"
  else
    rm -f "$tmp"
  fi

  a=$(stat -c%s "$f"); ak=$(( (a + 1023) / 1024 ))
  sk=$(( bk - ak ))
  denom=$(( bk > 0 ? bk : 1 ))
  pct=$(( 100 * ak / denom ))   # 新大小占原大小的百分比（越小越好）

  printf "%s|%d|%d|%d|%d\n" "$f" "$bk" "$ak" "$sk" "$pct" >> "$RESULTS"
  printf "✓ %s: %dKB → %dKB (saved %dKB, %d%%)\n" "$(basename "$f")" "$bk" "$ak" "$sk" "$pct"
}
export -f compress_one
export TMP_DIR RESULTS

# 并行执行（文件名安全，支持空格）
printf '%s\0' "${FILES[@]}" | xargs -0 -n1 -P"$PARALLEL" bash -c 'compress_one "$@"' _

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
ts=$((tb - ta)); tp=$(( tb > 0 ? (100 * ta / tb) : 0 ))
printf "%-40s %12d %12d %12d %7d%%\n" "TOTAL" "$tb" "$ta" "$ts" "$tp"
echo "workers used: $PARALLEL"

rm -rf "$TMP_DIR"