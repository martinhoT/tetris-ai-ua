#!/bin/bash

python3 ../server.py --port 6000 &
PORT=6000 python3 ../viewer.py --scale 1 &

sleep 1

PORT=6000 NAME="FMP" python3 ../student.py &