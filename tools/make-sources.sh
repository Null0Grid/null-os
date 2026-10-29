#!/bin/bash
# Source-code listing for a Null OS release (GPL and friends): which Debian
# source package, at which exact version, built each binary on the ISO.
#
#   make-sources.sh <filesystem.packages> <version> <outdir>
#
# Run on Debian 13 (it asks apt which source each binary came from). Writes
# nullos-<version>-sources.tsv and nullos-<version>-SOURCES.md.
set -euo pipefail
PKG=$1 VER=$2 OUT=$3
mkdir -p "$OUT"
TSV="$OUT/nullos-$VER-sources.tsv"
MD="$OUT/nullos-$VER-SOURCES.md"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null

printf 'binary\tversion\tsource\tsource_version\n' > "$TSV"
while read -r name ver _; do
  [ -n "${name:-}" ] || continue
  name=${name%%:*}
  info=$(apt-cache show --no-all-versions "$name=$ver" 2>/dev/null || true)
  if [ -z "$info" ]; then
    printf '%s\t%s\t%s\t%s\n' "$name" "$ver" "-" "-" >> "$TSV"   # not from Debian
    continue
  fi
  src=$(printf '%s\n' "$info" | awk '/^Source:/{print $2; exit}')
  sver=$(printf '%s\n' "$info" | awk '/^Source:/{gsub(/[()]/,"",$3); print $3; exit}')
  [ -n "$src" ] || src=$name
  [ -n "$sver" ] || sver=$ver
  printf '%s\t%s\t%s\t%s\n' "$name" "$ver" "$src" "$sver" >> "$TSV"
done < "$PKG"

nbin=$(($(wc -l < "$TSV") - 1))
nsrc=$(tail -n +2 "$TSV" | awk -F'\t' '$3!="-"{print $3"\t"$4}' | sort -u | wc -l)
other=$(tail -n +2 "$TSV" | awk -F'\t' '$3=="-"{print $1" "$2}')
{
  echo "# Null OS $VER: source code"
  echo
  echo "Null OS is Debian 13 (trixie) packages plus the Null OS build configuration. Everything on the ISO can be rebuilt from these sources."
  echo
  echo "## Null OS itself"
  echo "Build scripts, package lists, hooks, branding, the installer screens and Null OS Extras: https://github.com/Null0Grid/null-os/tree/$VER"
  echo
  echo "## Debian packages ($nbin binaries from $nsrc source packages)"
  echo "\`nullos-$VER-sources.tsv\` lists every binary package on the ISO with the exact Debian source package and version it was built from. Get any of them with:"
  echo
  echo "- \`apt-get source <source>=<version>\` on Debian 13 (with deb-src lines enabled), or"
  echo "- https://snapshot.debian.org/package/<source>/<version>/ (Debian keeps every version)"
  echo
  if [ -n "$other" ]; then
    echo "## Not from Debian"
    echo "These come from their own projects; their source is in the linked repositories:"
    echo
    printf '%s\n' "$other" | sed 's/^/- /'
    echo
    echo "(Null Grid browser: https://github.com/Null0Grid/node-grid · Null File: https://github.com/Null0Grid/null-file)"
    echo
  fi
  echo "## Written offer"
  echo "For three years after this release, anyone can ask for the complete corresponding source code of the GPL software in Null OS $VER, on a medium for no more than the cost of making and shipping it: support@nullgrid.dev."
} > "$MD"
echo "wrote $TSV ($nbin binaries, $nsrc sources) and $MD"
