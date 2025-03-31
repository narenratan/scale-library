#!/bin/bash
set -eux
HASH=$(git rev-parse HEAD)
DATE=$(date +"%Y%m%d")
DIR=scale-library-$DATE-${HASH:0:8}
rm -rf "$DIR"
mkdir "$DIR"
cp -r scales "$DIR"
cp README.md "$DIR"
cp scale-index.csv "$DIR"
zip -qmr "$DIR".zip "$DIR"
