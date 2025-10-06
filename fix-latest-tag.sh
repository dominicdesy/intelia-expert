#!/bin/bash
# Quick fix: Tag the current 'main' image as 'latest'

echo "=== FIX: Tagging 'main' as 'latest' in registry ==="

# Authenticate to DigitalOcean registry
doctl auth init -t $DOCR_ACCESS_TOKEN

# For each repository, tag 'main' as 'latest'
REGISTRY_NAME="intelia-registry"
REPOS=("intelia-frontend" "intelia-backend" "intelia-llm" "intelia-rag")

for REPO in "${REPOS[@]}"; do
  echo ""
  echo "Processing: $REPO"

  # Pull the 'main' tag
  docker pull registry.digitalocean.com/$REGISTRY_NAME/$REPO:main

  # Tag it as 'latest'
  docker tag registry.digitalocean.com/$REGISTRY_NAME/$REPO:main \
             registry.digitalocean.com/$REGISTRY_NAME/$REPO:latest

  # Push 'latest' tag
  docker push registry.digitalocean.com/$REGISTRY_NAME/$REPO:latest

  echo "✅ Tagged $REPO:main as latest"
done

echo ""
echo "=== All repositories now have 'latest' tag ==="
echo "You can now trigger deployment from App Platform"
