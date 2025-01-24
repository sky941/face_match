#!/bin/bash
set -e

# Update package list and install required dependencies
apt-get update
apt-get install -y cmake g++ gcc libboost-all-dev

# Other necessary commands, e.g., install Python dependencies if needed
pip install -r requirements.txt
