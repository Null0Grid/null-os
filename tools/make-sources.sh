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
# One batched apt-cache call (per-package calls take ~25 min for ~1600)
awk 'NF>=2 {n=$1; sub(/:.*/, "", n); print n "=" $2}' "$PKG" > "$OUT/.want"
xargs -a "$OUT/.want" -n 200 apt-cache show --no-all-versions 2>/dev/null \
  | awk -v RS= -F'\n' '{
      p=""; v=""; s=""; sv="";
      for (i = 1; i <= NF; i++) {
        if ($i ~ /^Package: /) p = substr($i, 10)
        else if ($i ~ /^Version: /) v = substr($i, 10)
        else if ($i ~ /^Source: /) { split(substr($i, 9), a, " "); s = a[1]; sv = a[2]; gsub(/[()]/, "", sv) }
      }
      if (p != "") { if (s == "") s = p; if (sv == "") sv = v; print p "\t" v "\t" s "\t" sv }
    }' > "$OUT/.found"
# binaries apt didn't know (not from Debian) get "-"
awk 'NF>=2 {n=$1; sub(/:.*/, "", n); print n "\t" $2}' "$PKG" \
  | awk -F'\t' 'NR==FNR {f[$1 "\t" $2] = $3 "\t" $4; next}
                 {k = $1 "\t" $2; print k "\t" ((k in f) ? f[k] : "-\t-")}' "$OUT/.found" - >> "$TSV"
rm -f "$OUT/.want" "$OUT/.found"

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
