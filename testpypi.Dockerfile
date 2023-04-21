FROM --platform=linux/amd64 redballoonsecurity/ofrak/core-dev-base:latest

RUN apt-get update && apt-get install -y python3-dev libffi-dev build-essential virtualenvwrapper \
    && apt-get install git-lfs -y 

RUN git clone https://github.com/redballoonsecurity/ofrak.git 
WORKDIR /ofrak/ofrak_core 
RUN make install
WORKDIR /
RUN pip install --upgrade pip \
    && python3 -m pip install --upgrade --no-deps --force-reinstall --pre -i https://test.pypi.org/simple/ ofrak-type \
    && python3 -m pip install --upgrade --no-deps --force-reinstall --pre -i https://test.pypi.org/simple/ ofrak-io \
    && python3 -m pip install --upgrade --no-deps --force-reinstall --pre -i https://test.pypi.org/simple/ ofrak \
    && python3 -m pip install --upgrade --no-deps --force-reinstall --pre -i https://test.pypi.org/simple/ ofrak-patch-maker \
    && rm -rf /usr/local/lib/python3.7/site-packages/ofrak_io_test /usr/local/lib/python3.7/site-packages/ofrak_type_test /usr/local/lib/python3.7/site-packages/ofrak_patcher_maker_test /usr/local/lib/python3.7/site-packages/ofrak_test \
    && rm -rf /ofrak/ofrak_type/ofrak_type /ofrak/ofrak_io/ofrak_io /ofrak/ofrak_patch_maker/ofrak_patch_maker /ofrak/ofrak_core/ofrak


# RUN python3 -m pytest -n auto ofrak/ofrak_type --cov=/usr/local/lib/python3.7/site-packages/ofrak_type --cov-report=term-missing --import-mode append \
#     && fun-coverage --cov-fail-under=100 \
#     && python3 -m pytest -n auto ofrak/ofrak_io --cov=/usr/local/lib/python3.7/site-packages/ofrak_io --cov-report=term-missing --import-mode append \
#     && fun-coverage --cov-fail-under=100 \
#     && python3 -m pytest -n auto ofrak/ofrak_patch_maker --cov=/usr/local/lib/python3.7/site-packages/ofrak_patch_maker --cov-report=term-missing --import-mode append \
#     && fun-coverage --cov-fail-under=100 \
#     && cd ofrak/ofrak_core \
#     && python3 -m pytest -n auto --cov=/usr/local/lib/python3.7/site-packages/ofrak --cov-report=term-missing --import-mode append \
#     && fun-coverage --cov-fail-under=100
