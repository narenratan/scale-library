#!/bin/bash
set -eux
DATE=$(date +"%Y%m%d")
DIR=scale-library-$DATE
rm -rf "$DIR"
mkdir "$DIR"
cp -r scales "$DIR"
cp README.md "$DIR"
cp scale-index.csv "$DIR"
zip -qmr "$DIR".zip "$DIR"
