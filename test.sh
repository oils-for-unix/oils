# canonical test script; should probably be renamed
# along with references in .travis.yml
set -o nounset
set -o pipefail
set -o errexit

echo "Test shells:"
type ash bash dash mksh zsh || true

test/lint.sh travis
# Type checking with MyPy.  Problem: mypy requires Python 3, but Oil
# requires Python 2.  The Travis environment doesn't like that.
types/run.sh travis
types/oil-slice.sh travis
test/unit.sh travis
test/spec.sh travis
