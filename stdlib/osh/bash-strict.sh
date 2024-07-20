# Bash strict mode, updated for 2024

set -o nounset
set -o pipefail
set -o errexit
shopt -s inherit_errexit
shopt -s strict:all 2>/dev/null || true  # dogfood for OSH

