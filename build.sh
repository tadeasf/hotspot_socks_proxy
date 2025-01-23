#!/bin/bash

# Exit on any error
set -e

echo "Starting build process..."

# Bump version in pyproject.toml
echo "Current version:"
grep "version = " pyproject.toml
echo "Enter new version (leave empty to skip):"
read new_version

if [ ! -z "$new_version" ]; then
    # Use sed to replace the version line in pyproject.toml
    sed -i '' "s/version = \".*\"/version = \"$new_version\"/" pyproject.toml
    echo "Version bumped to $new_version"
fi

# Deactivate virtual environment if active
if [[ -n "${VIRTUAL_ENV}" ]]; then
    echo "Deactivating virtual environment..."
    deactivate || true  # Continue even if deactivate fails
fi

# Clean up existing build artifacts with sudo
echo "Cleaning up build artifacts..."
sudo rm -rf .pdm-build .venv dist requirements-dev.lock requirements.lock || {
    echo "Failed to remove build artifacts. Please check permissions."
    exit 1
}

# Run sequential commands with error checking
commands=("rm -rf dist" "rye sync" "rye build")

for cmd in "${commands[@]}"; do
    echo "Running $cmd..."
    $cmd || { echo "$cmd failed"; exit 1; }
done

# Install package
echo "Installing package..."
pip install . || { echo "Installation failed"; exit 1; }

# Show package info
echo "Package information:"
pip show hotspot-socks-proxy || { echo "Failed to show package info"; exit 1; }

# Run rye publish directly
echo "Publishing to PyPI..."
rye publish --yes || { echo "Publishing failed"; exit 1; }

echo "Build process completed successfully"