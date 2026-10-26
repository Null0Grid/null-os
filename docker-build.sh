#!/bin/bash
# Build on any Linux host with Docker (Ubuntu, Fedora, Arch, WSL2...).
# --privileged is needed because live-build mounts /proc, /dev and loop devices.
set -euo pipefail
cd "$(dirname "$0")"
docker run --rm --privileged \
  -v "$PWD":/build -w /build \
  debian:trixie ./build.sh
