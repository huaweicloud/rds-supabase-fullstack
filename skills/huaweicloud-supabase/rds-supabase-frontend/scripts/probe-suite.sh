#!/usr/bin/env bash
# GET evidence only; HTTP success does not prove content/browser acceptance.
set -uo pipefail
umask 077
if [ "$#" -lt 2 ]; then
  echo 'Usage: probe-suite.sh NEW_PRIVATE_OUTPUT_DIR URL...' >&2
  exit 2
fi
out=$1
shift
# Refuse existing directories so evidence is never overwritten.
mkdir -m 700 -- "$out" || exit 2
pids=()
i=0
for url in "$@"; do
  case "$url" in http://*|https://*) ;; *) echo 'Only HTTP(S) URLs are supported' >&2; exit 2;; esac
done
for url in "$@"; do
  i=$((i + 1))
  (
    rc=0
    curl --silent --show-error --location --max-redirs 5 \
      --proto '=http,https' --proto-redir '=http,https' \
      --connect-timeout 5 --max-time "${PROBE_MAX_TIME:-5}" \
      --dump-header "$out/$i.headers" --output "$out/$i.body" \
      --write-out '%{http_code}\t%{url_effective}\n' \
      -- "$url" > "$out/$i.result" 2> "$out/$i.error" || rc=$?
    printf '%s\n' "$rc" > "$out/$i.exit"
  ) &
  pids+=("$!")
  # Bounded batches, compatible with macOS Bash 3.2.
  if [ "${#pids[@]}" -eq 8 ]; then
    for pid in "${pids[@]}"; do wait "$pid"; done
    pids=()
  fi
done
for pid in "${pids[@]}"; do wait "$pid"; done
printf 'id\tcurl_exit\tstatus\tfinal_url\n' > "$out/summary.tsv"
failed=0
for ((n=1;n<=i;n++)); do
  rc=$(cat "$out/$n.exit")
  status=$(cut -f1 "$out/$n.result")
  printf '%s\t%s\t' "$n" "$rc" >> "$out/summary.tsv"
  cat "$out/$n.result" >> "$out/summary.tsv"
  if [ "$rc" != 0 ] || [[ ! "$status" =~ ^2[0-9][0-9]$ ]]; then failed=1; fi
done
# URLs and raw headers may contain secrets; do not print them to chat logs.
printf 'GET evidence saved: %s requests; inspect private summary.tsv\n' "$i"
exit "$failed"
