#!/bin/sh
set -e -x
base="$PWD"
name="osmo-pcu"
. "$(dirname "$0")/jenkins-build-common.sh"

build_repo libosmocore --disable-pcsc --disable-doxygen
build_repo osmo-pcu

create_bin_tgz
