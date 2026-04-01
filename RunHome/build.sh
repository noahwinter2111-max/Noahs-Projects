#!/bin/bash
set -e
mkdir -p out
javac -d out src/*.java
echo "Build OK — run with:  java -cp out Main"
