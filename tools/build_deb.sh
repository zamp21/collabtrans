#!/usr/bin/env bash
set -euo pipefail

# Build CollabTrans .deb packages (lite/full) on Linux
# Usage:
#   tools/build_deb.sh            # build both
#   tools/build_deb.sh --lite     # build lite only
#   tools/build_deb.sh --full     # build full only

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This script supports Linux only."
  exit 1
fi

want_lite=true
want_full=true
if [[ "${1:-}" == "--lite" ]]; then
  want_full=false
elif [[ "${1:-}" == "--full" ]]; then
  want_lite=false
fi

ensure_venv() {
  if [[ ! -d .venv ]]; then
    python3 -m venv .venv
  fi
  # shellcheck disable=SC1091
  source .venv/bin/activate
  python -m pip install --upgrade pip >/dev/null
  python -m pip install . pyinstaller >/dev/null
}

get_version() {
  python - <<'PY'
import collabtrans
print(collabtrans.__version__)
PY
}

build_pyinstaller() {
  local spec_file="$1"
  echo "[build] pyinstaller -y ${spec_file}"
  pyinstaller -y "${spec_file}"
}

make_deb_lite() {
  local ver="$1"
  local out_dir="${ROOT_DIR}/build/deb"
  local pkg_root="${out_dir}/collabtrans_${ver}_amd64"
  local appbin="${ROOT_DIR}/dist/CollabTrans-${ver}-linux"

  if [[ ! -f "${appbin}" ]]; then
    echo "[lite] binary not found: ${appbin}"
    return 1
  fi

  rm -rf "${pkg_root}"
  mkdir -p "${pkg_root}/DEBIAN" "${pkg_root}/opt/collabtrans" "${pkg_root}/usr/bin" "${pkg_root}/etc/default" "${pkg_root}/lib/systemd/system"

  install -m755 "${appbin}" "${pkg_root}/opt/collabtrans/"

  cat > "${pkg_root}/DEBIAN/control" <<EOF
Package: collabtrans
Version: ${ver}
Section: utils
Priority: optional
Architecture: amd64
Maintainer: CollabTrans <noreply@example.com>
Description: CollabTrans document translation service - lite
 This package installs the CollabTrans server under /opt/collabtrans and a runner script at /usr/bin/collabtrans.
EOF

  cat > "${pkg_root}/etc/default/collabtrans" <<'EOF'
# Default options for CollabTrans service
COLLABTRANS_PORT=8010
COLLABTRANS_WORKDIR=/opt/collabtrans
EOF

  cat > "${pkg_root}/usr/bin/collabtrans" <<'EOF'
#!/usr/bin/env bash
set -e
PORT=${COLLABTRANS_PORT:-8010}
WORKDIR=${COLLABTRANS_WORKDIR:-/opt/collabtrans}
export DOCUTRANSLATE_PORT="$PORT"
cd "$WORKDIR"
exec "$WORKDIR"/CollabTrans-*-linux "$@"
EOF
  chmod 755 "${pkg_root}/usr/bin/collabtrans"

  cat > "${pkg_root}/lib/systemd/system/collabtrans.service" <<'EOF'
[Unit]
Description=CollabTrans Document Translation Service (lite)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=/etc/default/collabtrans
ExecStart=/usr/bin/collabtrans
Restart=on-failure
User=www-data
Group=www-data
WorkingDirectory=/opt/collabtrans

[Install]
WantedBy=multi-user.target
EOF
  chmod 644 "${pkg_root}/lib/systemd/system/collabtrans.service"

  dpkg-deb --build "${pkg_root}"
  echo "[lite] Built: ${pkg_root}.deb"
}

make_deb_full() {
  local ver="$1"
  local out_dir="${ROOT_DIR}/build/deb"
  local pkg_root="${out_dir}/collabtrans-full_${ver}_amd64"
  local appbin="${ROOT_DIR}/dist/CollabTrans_full-${ver}-linux"

  if [[ ! -f "${appbin}" ]]; then
    echo "[full] binary not found: ${appbin}"
    return 1
  fi

  rm -rf "${pkg_root}"
  mkdir -p "${pkg_root}/DEBIAN" "${pkg_root}/opt/collabtrans" "${pkg_root}/usr/bin" "${pkg_root}/etc/default" "${pkg_root}/lib/systemd/system"

  install -m755 "${appbin}" "${pkg_root}/opt/collabtrans/"

  cat > "${pkg_root}/DEBIAN/control" <<EOF
Package: collabtrans-full
Version: ${ver}
Section: utils
Priority: optional
Architecture: amd64
Maintainer: CollabTrans <noreply@example.com>
Description: CollabTrans document translation service - full
 This package installs the CollabTrans full server under /opt/collabtrans and a runner script at /usr/bin/collabtrans-full.
EOF

  cat > "${pkg_root}/etc/default/collabtrans-full" <<'EOF'
# Default options for CollabTrans FULL service
COLLABTRANS_PORT=8010
COLLABTRANS_WORKDIR=/opt/collabtrans
EOF

  cat > "${pkg_root}/usr/bin/collabtrans-full" <<'EOF'
#!/usr/bin/env bash
set -e
PORT=${COLLABTRANS_PORT:-8010}
WORKDIR=${COLLABTRANS_WORKDIR:-/opt/collabtrans}
export DOCUTRANSLATE_PORT="$PORT"
cd "$WORKDIR"
exec "$WORKDIR"/CollabTrans_full-*-linux "$@"
EOF
  chmod 755 "${pkg_root}/usr/bin/collabtrans-full"

  cat > "${pkg_root}/lib/systemd/system/collabtrans-full.service" <<'EOF'
[Unit]
Description=CollabTrans Document Translation Service (full)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=/etc/default/collabtrans-full
ExecStart=/usr/bin/collabtrans-full
Restart=on-failure
User=www-data
Group=www-data
WorkingDirectory=/opt/collabtrans

[Install]
WantedBy=multi-user.target
EOF
  chmod 644 "${pkg_root}/lib/systemd/system/collabtrans-full.service"

  dpkg-deb --build "${pkg_root}"
  echo "[full] Built: ${pkg_root}.deb"
}

main() {
  ensure_venv
  local ver
  ver=$(get_version)

  mkdir -p build/deb

  if $want_lite; then
    build_pyinstaller "lite.spec"
    make_deb_lite "$ver"
  fi

  if $want_full; then
    build_pyinstaller "full.spec"
    make_deb_full "$ver"
  fi
}

main "$@"


