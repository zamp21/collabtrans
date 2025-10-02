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
want_balance=false
if [[ "${1:-}" == "--lite" ]]; then
  want_full=false
  want_balance=false
elif [[ "${1:-}" == "--full" ]]; then
  want_lite=false
  want_balance=false
elif [[ "${1:-}" == "--balance" ]]; then
  want_lite=false
  want_full=false
  want_balance=true
fi

ensure_venv() {
  if [[ ! -d .venv ]]; then
    python3 -m venv .venv
  fi
  # shellcheck disable=SC1091
  source .venv/bin/activate
  python -m pip install --upgrade pip >/dev/null
  # Pin numpy to 1.26.4 (compatible with Python 3.12, stable with PyInstaller)
  echo "[env] Installing numpy==1.26.4 for stable PyInstaller builds (Py3.12 compatible)"
  python -m pip install --force-reinstall 'numpy==1.26.4' >/dev/null
  # Install project and PyInstaller after numpy is pinned
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
  mkdir -p "${pkg_root}/DEBIAN" "${pkg_root}/opt/collabtrans" "${pkg_root}/usr/bin" "${pkg_root}/etc/default" "${pkg_root}/etc/collabtrans" "${pkg_root}/lib/systemd/system"

  install -m755 "${appbin}" "${pkg_root}/opt/collabtrans/"
  
  # 安装配置文件到 /etc/collabtrans
  install -m644 "${ROOT_DIR}/global_config.json" "${pkg_root}/etc/collabtrans/"
  install -m644 "${ROOT_DIR}/local_secrets.json.template" "${pkg_root}/etc/collabtrans/"
  if [[ -f "${ROOT_DIR}/local_config.json.template" ]]; then
    install -m644 "${ROOT_DIR}/local_config.json.template" "${pkg_root}/etc/collabtrans/"
  fi
  if [[ -f "${ROOT_DIR}/local_config.json" ]]; then
    install -m640 "${ROOT_DIR}/local_config.json" "${pkg_root}/etc/collabtrans/"
  fi
  # app_config.json 及模板
  if [[ -f "${ROOT_DIR}/app_config.json.template" ]]; then
    install -m644 "${ROOT_DIR}/app_config.json.template" "${pkg_root}/etc/collabtrans/"
  fi
  if [[ -f "${ROOT_DIR}/app_config.json" ]]; then
    install -m640 "${ROOT_DIR}/app_config.json" "${pkg_root}/etc/collabtrans/"
  fi
  # app_config.json 及模板
  if [[ -f "${ROOT_DIR}/app_config.json.template" ]]; then
    install -m644 "${ROOT_DIR}/app_config.json.template" "${pkg_root}/etc/collabtrans/"
  fi
  if [[ -f "${ROOT_DIR}/app_config.json" ]]; then
    install -m640 "${ROOT_DIR}/app_config.json" "${pkg_root}/etc/collabtrans/"
  fi

  cat > "${pkg_root}/DEBIAN/control" <<EOF
Package: collabtrans-lite
Version: ${ver}
Section: utils
Priority: optional
Architecture: amd64
Maintainer: CollabTrans <noreply@example.com>
Description: CollabTrans document translation service - lite
 This package installs the CollabTrans server under /opt/collabtrans and a runner script at /usr/bin/collabtrans.
Depends: systemd
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

  # 添加postinst脚本
  cat > "${pkg_root}/DEBIAN/postinst" <<'EOF'
#!/bin/bash
set -e

# 重新加载systemd配置
if command -v systemctl >/dev/null 2>&1; then
    systemctl daemon-reload
    echo "systemd configuration reloaded"
fi

# 创建www-data用户和组（如果不存在）
if ! id www-data >/dev/null 2>&1; then
    useradd --system --no-create-home --shell /bin/false www-data || true
fi

# 创建协作组并授予权限
if ! getent group collabtrans >/dev/null 2>&1; then
    groupadd collabtrans || true
fi
usermod -aG collabtrans www-data || true

# 配置文件权限与属组
CFG_DIR="/etc/collabtrans"
install -d -m 755 "$CFG_DIR"
chgrp collabtrans "$CFG_DIR" || true
chmod 2755 "$CFG_DIR" || true  # 目录setgid，便于继承组

# 关键配置文件：全局配置与模板
if [[ -f "$CFG_DIR/global_config.json" ]]; then
  chown root:collabtrans "$CFG_DIR/global_config.json" || true
  chmod 660 "$CFG_DIR/global_config.json" || true
fi
if [[ -f "$CFG_DIR/local_secrets.json.template" ]]; then
  chown root:collabtrans "$CFG_DIR/local_secrets.json.template" || true
  chmod 640 "$CFG_DIR/local_secrets.json.template" || true
fi
if [[ -f "$CFG_DIR/local_secrets.json" ]]; then
  chown root:collabtrans "$CFG_DIR/local_secrets.json" || true
  chmod 660 "$CFG_DIR/local_secrets.json" || true
fi
if [[ -f "$CFG_DIR/local_config.json" ]]; then
  chown root:collabtrans "$CFG_DIR/local_config.json" || true
  chmod 660 "$CFG_DIR/local_config.json" || true
fi
# app_config.json 权限
if [[ -f "$CFG_DIR/app_config.json" ]]; then
  chown root:collabtrans "$CFG_DIR/app_config.json" || true
  chmod 660 "$CFG_DIR/app_config.json" || true
fi
# app_config.json 权限
if [[ -f "$CFG_DIR/app_config.json" ]]; then
  chown root:collabtrans "$CFG_DIR/app_config.json" || true
  chmod 660 "$CFG_DIR/app_config.json" || true
fi

echo "CollabTrans service installed successfully"
echo "To start the service: sudo systemctl start collabtrans"
echo "To enable auto-start: sudo systemctl enable collabtrans"

# 初始化 /etc/collabtrans/local_config.json（如缺失且有模板）
CFG_DIR="/etc/collabtrans"
if [[ ! -f "$CFG_DIR/local_config.json" && -f "$CFG_DIR/local_config.json.template" ]]; then
  cp -f "$CFG_DIR/local_config.json.template" "$CFG_DIR/local_config.json"
  chmod 660 "$CFG_DIR/local_config.json" || true
  echo "Created /etc/collabtrans/local_config.json from template"
fi
# 初始化 /etc/collabtrans/app_config.json（如缺失且有模板）
if [[ ! -f "$CFG_DIR/app_config.json" && -f "$CFG_DIR/app_config.json.template" ]]; then
  cp -f "$CFG_DIR/app_config.json.template" "$CFG_DIR/app_config.json"
  chmod 660 "$CFG_DIR/app_config.json" || true
  echo "Created /etc/collabtrans/app_config.json from template"
fi
# 初始化 /etc/collabtrans/app_config.json（如缺失且有模板）
if [[ ! -f "$CFG_DIR/app_config.json" && -f "$CFG_DIR/app_config.json.template" ]]; then
  cp -f "$CFG_DIR/app_config.json.template" "$CFG_DIR/app_config.json"
  chmod 660 "$CFG_DIR/app_config.json" || true
  echo "Created /etc/collabtrans/app_config.json from template"
fi

# 创建运行期数据目录并授权（用户配置、缓存等）
RUNTIME_DIR="/var/lib/collabtrans"
install -d -m 750 "$RUNTIME_DIR" || true
chown -R www-data:collabtrans "$RUNTIME_DIR" || true
install -d -m 750 "$RUNTIME_DIR/user_profiles" || true
chown -R www-data:collabtrans "$RUNTIME_DIR/user_profiles" || true
install -d -m 750 "$RUNTIME_DIR/prompts" || true
chown -R www-data:collabtrans "$RUNTIME_DIR/prompts" || true
install -d -m 750 "$RUNTIME_DIR/glossaries" || true
chown -R www-data:collabtrans "$RUNTIME_DIR/glossaries" || true

# 建立默认写路径的符号链接，指向可写目录
install -d -m 755 /opt/collabtrans || true
if [[ ! -L "/opt/collabtrans/user_profiles" ]]; then
  ln -sfn "$RUNTIME_DIR/user_profiles" "/opt/collabtrans/user_profiles" || true
fi
if [[ ! -L "/opt/collabtrans/prompts" ]]; then
  ln -sfn "$RUNTIME_DIR/prompts" "/opt/collabtrans/prompts" || true
fi
if [[ ! -L "/opt/collabtrans/glossaries" ]]; then
  ln -sfn "$RUNTIME_DIR/glossaries" "/opt/collabtrans/glossaries" || true
fi
EOF
  chmod 755 "${pkg_root}/DEBIAN/postinst"

  # 添加prerm脚本
  cat > "${pkg_root}/DEBIAN/prerm" <<'EOF'
#!/bin/bash
set -e

# 停止服务
if command -v systemctl >/dev/null 2>&1; then
    systemctl stop collabtrans || true
    systemctl disable collabtrans || true
fi
EOF
  chmod 755 "${pkg_root}/DEBIAN/prerm"

  # 添加postrm脚本
  cat > "${pkg_root}/DEBIAN/postrm" <<'EOF'
#!/bin/bash
set -e

# 重新加载systemd配置
if command -v systemctl >/dev/null 2>&1; then
    systemctl daemon-reload
fi
EOF
  chmod 755 "${pkg_root}/DEBIAN/postrm"

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
  mkdir -p "${pkg_root}/DEBIAN" "${pkg_root}/opt/collabtrans" "${pkg_root}/usr/bin" "${pkg_root}/etc/default" "${pkg_root}/etc/collabtrans" "${pkg_root}/lib/systemd/system"

  install -m755 "${appbin}" "${pkg_root}/opt/collabtrans/"
  
  # 安装配置文件到 /etc/collabtrans
  install -m644 "${ROOT_DIR}/global_config.json" "${pkg_root}/etc/collabtrans/"
  install -m644 "${ROOT_DIR}/local_secrets.json.template" "${pkg_root}/etc/collabtrans/"
  if [[ -f "${ROOT_DIR}/local_config.json.template" ]]; then
    install -m644 "${ROOT_DIR}/local_config.json.template" "${pkg_root}/etc/collabtrans/"
  fi
  if [[ -f "${ROOT_DIR}/local_config.json" ]]; then
    install -m640 "${ROOT_DIR}/local_config.json" "${pkg_root}/etc/collabtrans/"
  fi

  cat > "${pkg_root}/DEBIAN/control" <<EOF
Package: collabtrans-full
Version: ${ver}
Section: utils
Priority: optional
Architecture: amd64
Maintainer: CollabTrans <noreply@example.com>
Description: CollabTrans document translation service - full
 This package installs the CollabTrans full server under /opt/collabtrans and a runner script at /usr/bin/collabtrans-full.
Depends: systemd
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

  # 添加postinst脚本
  cat > "${pkg_root}/DEBIAN/postinst" <<'EOF'
#!/bin/bash
set -e

# 重新加载systemd配置
if command -v systemctl >/dev/null 2>&1; then
    systemctl daemon-reload
    echo "systemd configuration reloaded"
fi

# 创建www-data用户和组（如果不存在）
if ! id www-data >/dev/null 2>&1; then
    useradd --system --no-create-home --shell /bin/false www-data || true
fi

echo "CollabTrans full service installed successfully"
echo "To start the service: sudo systemctl start collabtrans-full"
echo "To enable auto-start: sudo systemctl enable collabtrans-full"

CFG_DIR="/etc/collabtrans"
if [[ ! -f "$CFG_DIR/auth_config.json" && -f "$CFG_DIR/auth_config.json.template" ]]; then
  cp -f "$CFG_DIR/auth_config.json.template" "$CFG_DIR/auth_config.json"
  chmod 660 "$CFG_DIR/auth_config.json" || true
  echo "Created /etc/collabtrans/auth_config.json from template"
fi
EOF
  chmod 755 "${pkg_root}/DEBIAN/postinst"

  # 添加prerm脚本
  cat > "${pkg_root}/DEBIAN/prerm" <<'EOF'
#!/bin/bash
set -e

# 停止服务
if command -v systemctl >/dev/null 2>&1; then
    systemctl stop collabtrans-full || true
    systemctl disable collabtrans-full || true
fi
EOF
  chmod 755 "${pkg_root}/DEBIAN/prerm"

  # 添加postrm脚本
  cat > "${pkg_root}/DEBIAN/postrm" <<'EOF'
#!/bin/bash
set -e

# 重新加载systemd配置
if command -v systemctl >/dev/null 2>&1; then
    systemctl daemon-reload
fi
EOF
  chmod 755 "${pkg_root}/DEBIAN/postrm"

  dpkg-deb --build "${pkg_root}"
  echo "[full] Built: ${pkg_root}.deb"
}

make_deb_balance() {
  local ver="$1"
  local out_dir="${ROOT_DIR}/build/deb"
  local pkg_root="${out_dir}/collabtrans-balance_${ver}_amd64"
  local appbin="${ROOT_DIR}/dist/CollabTrans-balance-${ver}-linux"

  if [[ ! -f "${appbin}" ]]; then
    echo "[balance] binary not found: ${appbin}"
    return 1
  fi

  rm -rf "${pkg_root}"
  mkdir -p "${pkg_root}/DEBIAN" "${pkg_root}/opt/collabtrans" "${pkg_root}/usr/bin" "${pkg_root}/etc/default" "${pkg_root}/etc/collabtrans" "${pkg_root}/lib/systemd/system"

  install -m755 "${appbin}" "${pkg_root}/opt/collabtrans/"
  
  # 安装配置文件到 /etc/collabtrans
  install -m644 "${ROOT_DIR}/global_config.json" "${pkg_root}/etc/collabtrans/"
  install -m644 "${ROOT_DIR}/local_secrets.json.template" "${pkg_root}/etc/collabtrans/"
  if [[ -f "${ROOT_DIR}/auth_config.json.template" ]]; then
    install -m644 "${ROOT_DIR}/auth_config.json.template" "${pkg_root}/etc/collabtrans/"
  fi
  if [[ -f "${ROOT_DIR}/auth_config.json" ]]; then
    install -m640 "${ROOT_DIR}/auth_config.json" "${pkg_root}/etc/collabtrans/"
  fi

  cat > "${pkg_root}/DEBIAN/control" <<EOF
Package: collabtrans-balance
Version: ${ver}
Section: utils
Priority: optional
Architecture: amd64
Maintainer: CollabTrans <noreply@example.com>
Description: CollabTrans document translation service - balance
 This package installs the CollabTrans balance server under /opt/collabtrans and a runner script at /usr/bin/collabtrans-balance.
 Includes docling and MinerU support but excludes heavy dependencies like torch and transformers.
Depends: systemd
EOF

  cat > "${pkg_root}/etc/default/collabtrans-balance" <<'EOF'
# Default options for CollabTrans BALANCE service
COLLABTRANS_PORT=8010
COLLABTRANS_WORKDIR=/opt/collabtrans
EOF

  cat > "${pkg_root}/usr/bin/collabtrans-balance" <<'EOF'
#!/usr/bin/env bash
set -e
PORT=${COLLABTRANS_PORT:-8010}
WORKDIR=${COLLABTRANS_WORKDIR:-/opt/collabtrans}
export DOCUTRANSLATE_PORT="$PORT"
cd "$WORKDIR"
exec "$WORKDIR"/CollabTrans-balance-*-linux "$@"
EOF
  chmod 755 "${pkg_root}/usr/bin/collabtrans-balance"

  cat > "${pkg_root}/lib/systemd/system/collabtrans-balance.service" <<'EOF'
[Unit]
Description=CollabTrans Document Translation Service (balance)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=/etc/default/collabtrans-balance
ExecStart=/usr/bin/collabtrans-balance
Restart=on-failure
User=www-data
Group=www-data
WorkingDirectory=/opt/collabtrans

[Install]
WantedBy=multi-user.target
EOF
  chmod 644 "${pkg_root}/lib/systemd/system/collabtrans-balance.service"

  # 添加postinst脚本
  cat > "${pkg_root}/DEBIAN/postinst" <<'EOF'
#!/bin/bash
set -e

# 重新加载systemd配置
if command -v systemctl >/dev/null 2>&1; then
    systemctl daemon-reload
    echo "systemd configuration reloaded"
fi

# 创建www-data用户和组（如果不存在）
if ! id www-data >/dev/null 2>&1; then
    useradd --system --no-create-home --shell /bin/false www-data || true
fi

# 创建协作组并授予权限
if ! getent group collabtrans >/dev/null 2>&1; then
    groupadd collabtrans || true
fi
usermod -aG collabtrans www-data || true

# 配置文件权限与属组
CFG_DIR="/etc/collabtrans"
install -d -m 755 "$CFG_DIR"
chgrp collabtrans "$CFG_DIR" || true
chmod 2755 "$CFG_DIR" || true  # 目录setgid，便于继承组

# 关键配置文件：全局配置与模板
if [[ -f "$CFG_DIR/global_config.json" ]]; then
  chown root:collabtrans "$CFG_DIR/global_config.json" || true
  chmod 660 "$CFG_DIR/global_config.json" || true
fi
if [[ -f "$CFG_DIR/local_secrets.json.template" ]]; then
  chown root:collabtrans "$CFG_DIR/local_secrets.json.template" || true
  chmod 640 "$CFG_DIR/local_secrets.json.template" || true
fi
if [[ -f "$CFG_DIR/local_secrets.json" ]]; then
  chown root:collabtrans "$CFG_DIR/local_secrets.json" || true
  chmod 660 "$CFG_DIR/local_secrets.json" || true
fi
if [[ -f "$CFG_DIR/local_config.json" ]]; then
  chown root:collabtrans "$CFG_DIR/local_config.json" || true
  chmod 660 "$CFG_DIR/local_config.json" || true
fi

echo "CollabTrans balance service installed successfully"
echo "To start the service: sudo systemctl start collabtrans-balance"
echo "To enable auto-start: sudo systemctl enable collabtrans-balance"

# 初始化 /etc/collabtrans/local_config.json（如缺失且有模板）
CFG_DIR="/etc/collabtrans"
if [[ ! -f "$CFG_DIR/local_config.json" && -f "$CFG_DIR/local_config.json.template" ]]; then
  cp -f "$CFG_DIR/local_config.json.template" "$CFG_DIR/local_config.json"
  chmod 660 "$CFG_DIR/local_config.json" || true
  echo "Created /etc/collabtrans/local_config.json from template"
fi

# 创建运行期数据目录并授权（用户配置、缓存等）
RUNTIME_DIR="/var/lib/collabtrans"
install -d -m 750 "$RUNTIME_DIR" || true
chown -R www-data:collabtrans "$RUNTIME_DIR" || true
install -d -m 750 "$RUNTIME_DIR/user_profiles" || true
chown -R www-data:collabtrans "$RUNTIME_DIR/user_profiles" || true
install -d -m 750 "$RUNTIME_DIR/prompts" || true
chown -R www-data:collabtrans "$RUNTIME_DIR/prompts" || true
install -d -m 750 "$RUNTIME_DIR/glossaries" || true
chown -R www-data:collabtrans "$RUNTIME_DIR/glossaries" || true

# 建立默认写路径的符号链接，指向可写目录
install -d -m 755 /opt/collabtrans || true
if [[ ! -L "/opt/collabtrans/user_profiles" ]]; then
  ln -sfn "$RUNTIME_DIR/user_profiles" "/opt/collabtrans/user_profiles" || true
fi
if [[ ! -L "/opt/collabtrans/prompts" ]]; then
  ln -sfn "$RUNTIME_DIR/prompts" "/opt/collabtrans/prompts" || true
fi
if [[ ! -L "/opt/collabtrans/glossaries" ]]; then
  ln -sfn "$RUNTIME_DIR/glossaries" "/opt/collabtrans/glossaries" || true
fi
EOF
  chmod 755 "${pkg_root}/DEBIAN/postinst"

  # 添加prerm脚本
  cat > "${pkg_root}/DEBIAN/prerm" <<'EOF'
#!/bin/bash
set -e

# 停止服务
if command -v systemctl >/dev/null 2>&1; then
    systemctl stop collabtrans-balance || true
    systemctl disable collabtrans-balance || true
fi
EOF
  chmod 755 "${pkg_root}/DEBIAN/prerm"

  # 添加postrm脚本
  cat > "${pkg_root}/DEBIAN/postrm" <<'EOF'
#!/bin/bash
set -e

# 重新加载systemd配置
if command -v systemctl >/dev/null 2>&1; then
    systemctl daemon-reload
fi
EOF
  chmod 755 "${pkg_root}/DEBIAN/postrm"

  dpkg-deb --build "${pkg_root}"
  echo "[balance] Built: ${pkg_root}.deb"
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

  if $want_balance; then
    build_pyinstaller "balance.spec"
    make_deb_balance "$ver"
  fi
}

main "$@"


