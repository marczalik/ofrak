FROM --platform=linux/amd64 redballoonsecurity/ofrak/testpypi-base:latest

# Download & install java and supervisor
RUN apt-get update && apt-get install -y openjdk-11-jdk supervisor

# Download & install ghidra
RUN mkdir -p /opt/rbs && \
    cd /tmp && \
    wget -c https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_10.1.2_build/ghidra_10.1.2_PUBLIC_20220125.zip --show-progress --progress=bar:force:noscroll && \
    unzip ghidra_10.1.2_PUBLIC_20220125.zip > /dev/null && \
    rm -f ghidra_10.1.2_PUBLIC_20220125.zip && \
    mv ghidra_10.1.2_PUBLIC/ /opt/rbs/ghidra_10.1.2_PUBLIC

ARG OFRAK_DIR=.
WORKDIR /
COPY $OFRAK_DIR/disassemblers/ofrak_ghidra/server.conf /opt/rbs/ghidra_10.1.2_PUBLIC/server/


# RUN python3 -m pytest -n auto ofrak/ofrak_type --cov=/usr/local/lib/python3.7/site-packages/ofrak_type --cov-report=term-missing --import-mode append \
#     && fun-coverage --cov-fail-under=100 \
#     && python3 -m pytest -n auto ofrak/ofrak_io --cov=/usr/local/lib/python3.7/site-packages/ofrak_io --cov-report=term-missing --import-mode append \
#     && fun-coverage --cov-fail-under=100 \
#     && python3 -m pytest -n auto ofrak/ofrak_patch_maker --cov=/usr/local/lib/python3.7/site-packages/ofrak_patch_maker --cov-report=term-missing --import-mode append \
#     && fun-coverage --cov-fail-under=100 \
#     && cd ofrak/ofrak_core \
#     && python3 -m pytest -n auto --cov=/usr/local/lib/python3.7/site-packages/ofrak --cov-report=term-missing --import-mode append \
#     && fun-coverage --cov-fail-under=100
