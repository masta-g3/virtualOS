#!/bin/bash
# Deploy to Hetzner server

set -e

echo "Pushing to origin..."
git push origin aisdk_port:main

echo "Pulling on server..."
ssh hetzner "cd ~/pyagents && git pull"

echo "Syncing dependencies..."
ssh hetzner "cd ~/pyagents && uv sync"

echo "Restarting service..."
ssh hetzner "sudo systemctl restart pyagents_console"

echo "Verifying..."
sleep 3
STATUS=$(ssh hetzner "curl -s -o /dev/null -w '%{http_code}' http://localhost:8889/")
if [ "$STATUS" = "200" ]; then
    echo "Deploy successful: https://console.llmpedia.ai"
else
    echo "Deploy failed - status: $STATUS"
    exit 1
fi
