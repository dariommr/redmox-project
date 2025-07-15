# REDMOX Project
Redmox project is a Redfish emulator with some basic endpoints needed by WindRiver Conductor.
It is designed to connect to Proxmox Virtual Environments through the PVE API Endpoints

## Requiremens
Run on Docker or on a virtual maching with the following Environment Variables:

```bash
PMOX_ADDR=192.168.0.10
PMOX_PORT=8006
DEBUG=yes                     #Optional
```