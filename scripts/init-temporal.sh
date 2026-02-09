#!/bin/sh
set -e

export TEMPORAL_ADDRESS="$(hostname -i):7233"

until temporal operator search-attribute list --namespace "default"; do
  echo "Waiting for namespace cache to refresh..."
  sleep 1
done
echo "Temporal is ready, creating search attributes..."
temporal operator search-attribute create --name="OperationUUID" --type="Keyword" --namespace="default"

echo "Search attributes created successfully!"
