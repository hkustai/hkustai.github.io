#!/bin/bash

# 图片目录
IMG_DIR="../members/images"

shopt -s nullglob
files=("$IMG_DIR"/*.{png,PNG,jpg,JPG,jpeg,JPEG})
total=${#files[@]}
count=0

for f in "${files[@]}"; do
  count=$((count + 1))
  ext="${f##*.}"
  filename="$(basename "$f")"
  tmpfile="$(mktemp)"

  echo "[$count/$total] 压缩 $filename ..."

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
done

echo "✅ 全部完成！原文件已被优化版本替换"