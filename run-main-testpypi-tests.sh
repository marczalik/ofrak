python3 -m pytest -n auto ofrak/ofrak_type --cov=/usr/local/lib/python3.7/site-packages/ofrak_type --cov-report=term-missing --import-mode append
fun-coverage --cov-fail-under=100
python3 -m pytest -n auto ofrak/ofrak_io --cov=/usr/local/lib/python3.7/site-packages/ofrak_io --cov-report=term-missing --import-mode append
fun-coverage --cov-fail-under=100
python3 -m pytest -n auto ofrak/ofrak_patch_maker --cov=/usr/local/lib/python3.7/site-packages/ofrak_patch_maker --cov-report=term-missing --import-mode append
fun-coverage --cov-fail-under=100
cd ofrak/ofrak_core
python3 -m pytest -n auto --cov=/usr/local/lib/python3.7/site-packages/ofrak --cov-report=term-missing --import-mode append
fun-coverage --cov-fail-under=100
