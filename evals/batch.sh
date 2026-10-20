#!/bin/sh
# batch.sh VARIANT MODEL "TASK:N ..."  -> runs in parallel, 4 at a time
set -eu
here=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
v=$1 m=$2; shift 2
for spec in "$@"; do echo "$spec"; done | xargs -P 4 -I{} sh -c 't=$(echo {} | cut -d: -f1); n=$(echo {} | cut -d: -f2); '"$here"'/run.sh '"$v"' $t $n '"$m"
