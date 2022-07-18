#!/bin/bash

for i in {1..10}
do
    python3 ../server.py --port $(($i + 8000)) &
    PORT=$(($i + 8000)) python3 ../viewer.py --scale 2 &
done

sleep 1

for i in {1..10}
do
    PORT=$(($i + 8000)) NAME="FMP" python3 ../student.py &
done