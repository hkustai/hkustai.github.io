#!/bin/bash

# 图片目录
IMG_DIR="../members/images"

# 临时文件夹保存中间结果
TMP_DIR=$(mktemp -d)

# 获取文件列表
shopt -s nullglob
files=("$IMG_DIR"/*.{png,PNG,jpg,JPG,jpeg,JPEG})
total=${#files[@]}

if [ $total -eq 0 ]; then
  echo "❌ 没有找到 PNG 或 JPG 文件"
  exit 1
fi

echo "📂 发现 $total 张图片，开始并行压缩 (8 进程)..."

# 并行处理函数
compress_file() {
  f="$1"
  ext="${f##*.}"
  tmpfile="$(mktemp -p "$TMP_DIR")"

  before_size=$(stat -c%s "$f")
  before_kb=$((before_size / 1024))

  case "$ext" in
    png|PNG)
      pngcrush -brute -q "$f" "$tmpfile" >/dev/null 2>&1
      ;;
    jpg|jpeg|JPG|JPEG)
      jpegtran -optimize -progressive -copy none "$f" > "$tmpfile"
      ;;
  esac

  # 替换原文件
  mv "$tmpfile" "$f"

  after_size=$(stat -c%s "$f")
  after_kb=$((after_size / 1024))

  saved=$((before_kb - after_kb))
  percent=$((100 * after_kb / before_kb))

  echo "$f|$before_kb|$after_kb|$saved|$percent" >> "$TMP_DIR/results.log"
}

export -f compress_file
export TMP_DIR

# 并行执行 (8 个进程)
printf "%s\n" "${files[@]}" | xargs -n1 -P8 bash -c 'compress_file "$@"' _

# 最终总结
echo
echo "📊 压缩结果总结:"
echo "-------------------------------------------"
printf "%-30s %10s %10s %10s %8s\n" "文件名" "原大小(KB)" "新大小(KB)" "节省(KB)" "比例"

total_before=0
total_after=0

while IFS="|" read -r f before after saved percent; do
  filename=$(basename "$f")
  printf "%-30s %10d %10d %10d %7d%%\n" "$filename" "$before" "$after" "$saved" "$percent"
  total_before=$((total_before + before))
  total_after=$((total_after + after))
done < "$TMP_DIR/results.log"

total_saved=$((total_before - total_after))
total_percent=$((100 * total_after / total_before))

echo "-------------------------------------------"
printf "%-30s %10d %10d %10d %7d%%\n" "总计" "$total_before" "$total_after" "$total_saved" "$total_percent"

# 清理
rm -rf "$TMP_DIR"
