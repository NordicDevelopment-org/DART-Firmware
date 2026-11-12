#!/usr/bin/env bash
# Build one PlatformIO env of upstream Meshtastic at the pinned tag.
# For env ndi_1w the NDI overlay and patches are applied first. Any other env (the rak4631
# control) builds upstream untouched, which proves the harness before the NDI build is trusted.
#
# Usage: ndi_1w/ci/build_variant.sh <pio env>
# Needs UPSTREAM_TAG and UPSTREAM_COMMIT in the environment (ndi_1w/ci/resolve_upstream.sh).
# Mirrors upstream's own CI: recursive submodules, setuptools<72, platformio + adafruit-nrfutil,
# APP_VERSION from bin/buildinfo.py, pio run -t mtjson.
# Outputs go to $OUT_DIR (default _out/) and the job summary.
set -euo pipefail

env_name="${1:?usage: build_variant.sh <pio env>}"
: "${UPSTREAM_TAG:?UPSTREAM_TAG not set}"
: "${UPSTREAM_COMMIT:?UPSTREAM_COMMIT not set}"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
lock="$repo_root/ndi_1w/upstream.lock"
work="${WORK_DIR:-$repo_root/_upstream}"
out="${OUT_DIR:-$repo_root/_out}"

lock_get() {
    grep -E "^$1=" "$lock" | head -1 | cut -d= -f2-
}
upstream_repo="$(lock_get UPSTREAM_REPO)"
pio_version="$(lock_get PLATFORMIO_VERSION)"
nrfutil_version="$(lock_get ADAFRUIT_NRFUTIL_VERSION)"

summary() {
    if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
        printf '%s\n' "$*" >> "$GITHUB_STEP_SUMMARY"
    fi
}

echo "::group::tools"
python3 -m pip install --upgrade pip
python3 -m pip install -U --no-build-isolation --no-cache-dir "setuptools<72"
python3 -m pip install --no-build-isolation "platformio==${pio_version}" "adafruit-nrfutil==${nrfutil_version}"
pio --version
echo "::endgroup::"

echo "::group::clone upstream ${UPSTREAM_TAG}"
rm -rf "$work" "$out"
mkdir -p "$out"
git clone --quiet --depth 1 --recurse-submodules --shallow-submodules --branch "$UPSTREAM_TAG" "$upstream_repo" "$work"
head="$(git -C "$work" rev-parse HEAD)"
if [ "$head" != "$UPSTREAM_COMMIT" ]; then
    echo "::error::tag ${UPSTREAM_TAG} checked out ${head}, expected ${UPSTREAM_COMMIT}"
    exit 1
fi
echo "$head" > "$out/upstream-commit.txt"
echo "::endgroup::"

if [ "$env_name" = "ndi_1w" ]; then
    echo "::group::NDI overlay and patches"
    python3 -I "$repo_root/ndi_1w/pin_table/gen_variant.py" --check
    cp -r "$repo_root/ndi_1w/meshtastic/overlay/variants/." "$work/variants/"
    shopt -s nullglob
    for p in "$repo_root"/ndi_1w/meshtastic/patches/*.patch; do
        echo "applying $(basename "$p")"
        if ! patch -d "$work" -p1 --forward --fuzz=2 --no-backup-if-mismatch < "$p"; then
            echo "::error::patch $(basename "$p") does not apply to ${UPSTREAM_TAG}"
            exit 1
        fi
    done
    shopt -u nullglob
    python3 -I "$repo_root/ndi_1w/ci/check_forbidden.py" --upstream "$work"
    echo "::endgroup::"
fi

cd "$work"
version="$(python3 bin/buildinfo.py long)"
export APP_VERSION="$version"
# SCONSFLAGS=-k keeps compiling after the first error, so one run shows every problem.
export SCONSFLAGS="${SCONSFLAGS:-} -k"
build_log="$out/pio-build-${env_name}.log"
echo "::group::pio run -e ${env_name} (version ${version})"
set +e
pio run --environment "$env_name" -t mtjson 2>&1 | tee "$build_log"
rc="${PIPESTATUS[0]}"
set -e
echo "::endgroup::"
if [ "$rc" -ne 0 ]; then
    echo "::group::error digest for ${env_name} (pio exit ${rc})"
    grep -n -E "error:|fatal error|undefined reference|multiple definition|\*\*\* \[" "$build_log" | head -80 || true
    echo "::endgroup::"
    exit "$rc"
fi

build_dir=".pio/build/${env_name}"
cp "$build_dir"/firmware-* "$out"/ 2>/dev/null || true
pio pkg list --environment "$env_name" > "$out/pio-packages-${env_name}.txt" 2>&1 || true
{
    echo "env=${env_name}"
    echo "upstream_tag=${UPSTREAM_TAG}"
    echo "upstream_commit=${head}"
    echo "app_version=${version}"
    echo "platformio=${pio_version}"
    echo "adafruit_nrfutil=${nrfutil_version}"
} > "$out/build-record-${env_name}.txt"

if [ -z "$(find "$out" -maxdepth 1 -name 'firmware-*.hex' -print -quit)" ]; then
    echo "::error::no firmware hex was produced for ${env_name}"
    find "$build_dir" -maxdepth 1 -type f || true
    exit 1
fi

if [ "$env_name" = "ndi_1w" ]; then
    echo "::group::symbol audit (informational for now)"
    nm_tool="$(find "$HOME/.platformio/packages" -name 'arm-none-eabi-nm' -type f 2> /dev/null | head -1)"
    elf="$(find "$build_dir" -maxdepth 1 -name 'firmware-*.elf' -print -quit)"
    if [ -n "$nm_tool" ] && [ -n "$elf" ]; then
        "$nm_tool" -C "$elf" > "$out/symbols-${env_name}.txt"
        for pat in 'LSM6DS' 'AccelerometerThread' 'BQ25896' 'XPowers' 'RAK13302'; do
            n="$(grep -c -i "$pat" "$out/symbols-${env_name}.txt" || true)"
            echo "symbols matching ${pat}: ${n}"
            if [ "${n:-0}" != "0" ]; then
                echo "::warning::${n} symbols match ${pat} in the ndi_1w ELF (review: should be 0)"
            fi
        done
    else
        echo "::warning::arm-none-eabi-nm or the ELF was not found; symbol audit skipped"
    fi
    echo "::endgroup::"
fi

summary "### ${env_name}"
summary ""
summary "- upstream: \`${UPSTREAM_TAG}\` (\`${head}\`), app version \`${version}\`"
summary "- PlatformIO ${pio_version}, adafruit-nrfutil ${nrfutil_version}"
summary '```'
summary "$(find "$out" -maxdepth 1 -name 'firmware-*' -printf '%s %f\n')"
summary '```'
echo "built ${env_name}: $(find "$out" -maxdepth 1 -type f -printf '%f ')"
