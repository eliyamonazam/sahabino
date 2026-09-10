FROM ubuntu:24.04

WORKDIR /app

# pyshark shells out to the real tshark binary rather than parsing pcaps
# itself, so tshark has to actually be installed here, not just the pip
# package. The tshark version matters, not just its presence: 4.4.x changed
# how tcp.analysis.ack_rtt's completeness heuristic treats some SYN-ACK
# packets versus 4.2.x, which silently shifts handshake_rtt_ms on captures
# with many concurrent/retried connections (confirmed by diffing raw tshark
# output between versions on a real capture). Ubuntu 24.04 ships tshark
# 4.2.2 as its default package, which is pinned explicitly below so a
# future point release in noble-updates can't drift this again unnoticed -
# this is why the base image is Ubuntu rather than the python:3.12-slim
# (Debian) image the other services use, which only offers 4.0.x or 4.4.x,
# never 4.2.x, in either of its stable release lines.
#
# DEBIAN_FRONTEND=noninteractive avoids the interactive debconf prompt
# ("should non-superusers be able to capture packets?") that installing
# tshark asks by default; this container only ever reads already-captured
# pcap files as root, so that setuid question doesn't apply.
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tshark=4.2.2-1.1build3 \
        python3.12 \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# --break-system-packages: this container has no other use of its system
# Python, so there's no "system" to protect from pip-managed packages.
RUN python3.12 -m pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY analyzer ./analyzer

# Not "up -d": this is a batch tool meant to be run with
# `docker compose run --rm network-analyzer`, processing whatever's in
# PCAP_DIR once and exiting, not staying up as a long-running server.
CMD ["sh", "-c", "alembic upgrade head && python3.12 -m analyzer.main"]
