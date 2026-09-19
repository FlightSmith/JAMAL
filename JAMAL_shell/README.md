# JAMAL

set PYTHONPATH=.
set JAMAL_ROOT=.

export PYTHONPATH=.

pytest --cov=. --cov-report=html --log-cli-level=DEBUG
