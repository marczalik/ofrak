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

WORKDIR /ofrak/disassemblers/ofrak_ghidra
RUN make install

ARG OFRAK_DIR=.
WORKDIR /
COPY $OFRAK_DIR/disassemblers/ofrak_ghidra/server.conf /opt/rbs/ghidra_10.1.2_PUBLIC/server/
COPY $OFRAK_DIR/run-main-testpypi-tests.sh /
