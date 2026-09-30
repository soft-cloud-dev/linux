#!/bin/sh
set -eu

export JB_ALLOW_NODEENV=0

command -v node
command -v npm
node --version
npm --version
python --version
python -m pip --version

python tools/check_profile.py

jupyter book --version
jupyter book clean --all --execute -y
jupyter book build --html --strict --execute
if [ -f CNAME ]; then
  cp CNAME _build/html/CNAME
fi
test -s _build/html/index.html
