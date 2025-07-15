FROM debian:stable-slim

#STOPSIGNAL SIGINT
# Install Prerequisites
RUN apt update && \
    apt install git unzip python3 python3-pip python-is-python3 -y
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt --break-system-packages

RUN mkdir /opt/redmox
ENV PATH="/opt/redmox:$PATH"

COPY entry.sh /
COPY src/ /opt/redmox
RUN chmod +x /entry.sh && \
    chmod +x /opt/redmox/redmox.py

ENTRYPOINT ["/entry.sh"]