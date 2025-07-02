#bin/bash

echo "Starting to clean benchmark results..."

rm benchmark/china/out/*.json
rm benchmark/china/resp/*.json
rm benchmark/us/out/*.json
rm benchmark/us/resp/*.json

echo "Clean done"
