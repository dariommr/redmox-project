"""
    Module providing common functions for Proxmox API
"""

#!/usr/bin/env python3
from proxmoxer import ProxmoxAPI, ResourceException

class Proxmox:
    """
        Class to manage Proxmox API
    """
    def __init__(self, host, user, password, port=8006):
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self.api = ProxmoxAPI(host, user=user, password=password, port=port, verify_ssl=False)
        self.name = "Proxmox VE "+self.api.version.get().get('version', 'Unknown')

    def list_isos(self):
        nodes = self.api.nodes.get()
        for node in nodes:
            stgs = self.api.nodes(node["node"]).storage.get()
            isos = []
            for stg in stgs:
                content = self.api.nodes(node["node"]).storage(stg["storage"]).content.get(content="iso")
                for iso in content:
                    iso_arr = iso["volid"].split(":")
                    path = f'{node["node"]}/{iso_arr[0]}/{iso_arr[1]}'
                    isos.append(path)
        return isos

    def list_isos_vm(self, vmid):
        vms = self.api.cluster.resources.get(type='vm')
        vmstatus = ""
        for vm in vms:
            if 'vmid' in vm and str(vm['vmid']) == vmid:
                vmstatus = vm
                break
        if vmstatus == "":
            return {
                "error": True,
                "message": "No VM found"
            }
        isos = []
        for stg in self.api.nodes(vmstatus["node"]).storage.get():
            for iso in self.api.nodes(vmstatus["node"]).storage(stg["storage"]).content.get(content="iso"):
                iso_arr = iso["volid"].split(":")
                path = f'{vmstatus["node"]}/{iso_arr[0]}/{iso_arr[1]}'
                isos.append(path)
        
        return isos

    def get_vms_id(self):
        """
            Function to get the list of VMs
        """
        vms = self.api.cluster.resources.get(type='vm')
        vms_id = []
        for vm in vms:
            if 'vmid' in vm:
                vms_id.append(vm['vmid'])
        return vms_id
    
    def get_vm_info(self, vmid):
        """
            Function to get the information of a VM
        """
        vms = self.api.cluster.resources.get(type='vm')
        vmstatus = ""
        for vm in vms:
            if 'vmid' in vm and str(vm['vmid']) == vmid:
                vmstatus = vm
                break
        if vmstatus == "":
            return {
                "error": True,
                "message": "No VM found"
            }
        vmconfig = self.api.nodes(vmstatus['node']).qemu(vmid).config.get()
        json_out = {
            "id": vmstatus['vmid'],
            "vmgenid": vmconfig.get('vmgenid', ''),
            "name": vmstatus.get('name', 'Unknown'),
            "status": vmstatus.get('status', 'Unknown'),
            "node": vmstatus.get('node', 'Unknown'),
            "type": vmstatus.get('type', 'Unknown'),
            "tags": vmstatus.get('tags', []),
            "uptime": vmstatus.get('uptime', 0),
            "template": vmstatus.get('template', 0),
            "digest": vmconfig.get('digest', ''),
            "media": vmconfig.get('ide2', ''),
            "boot": {
                "order": vmconfig['boot'].replace('order=', '').split(';') if 'boot' in vmconfig else [],
            },
            "ostype": vmconfig.get('ostype', 'Unknown'),
            "cpu": {
                "usage": {
                    "current": vmstatus.get('cpu', 0),
                    "total": vmstatus.get('maxcpu', 0)
                },
                "cores": vmconfig.get('cores', 1),
                "type": vmconfig.get('cpu', 'Unknown'),
                "sockets": vmconfig.get('sockets', 1)
            },
            "memory": {
                "usage": {
                    "current": vmstatus.get('mem', 0),
                    "total": vmstatus.get('maxmem', 0)
                },
                "assigned_mb": vmconfig.get('memory', 0),
                "numa": vmconfig.get('numa', 0)
            },
            "disk": {
                "usage": {
                    "current": vmstatus.get('disk', 0),
                    "read": vmstatus.get('diskread', 0),
                    "write": vmstatus.get('diskwrite', 0),
                    "total": vmstatus.get('maxdisk', 0)
                },
                "list": []
            },
            "network": {
                "usage": {
                    "in": vmstatus.get('netin', 0),
                    "out": vmstatus.get('netout', 0)
                }
            }
        }
        for key, value in vmconfig.items():
            if isinstance(value, str) and "iso/" in value:
                json_out["cdrom"] = { "mount": key }
                arr_value = value.split(',')
                iso_data = arr_value[0].split(':')
                json_out["cdrom"]["datastore"] = iso_data[0]
                json_out["cdrom"]["iso"] = iso_data[1].replace('iso/', '')
                for item in arr_value:
                    if "=" in item:
                        arr_item = item.split('=')
                        json_out["cdrom"][arr_item[0]] = arr_item[1]
            if key == "meta":
                json_out["meta"] = {}
                for item in value.split(','):
                    if "=" in item:
                        arr_item = item.split('=')
                        json_out["meta"][arr_item[0]] = arr_item[1]
            if key.startswith("net"):
                json_out["network"]["interfaces"] = []
                arr_value = value.split(',')
                interface = { "name": key }
                for item in arr_value:
                    if "=" in item:
                        arr_item = item.split('=')
                        interface[arr_item[0]] = arr_item[1]
                json_out["network"]["interfaces"].append(interface)
            if isinstance(value, str) and "iothread" in value:
                disk = { 
                    "device": key,
                    "status": "mounted"
                }
                arr_value = value.split(',')
                disk["datastore"] = arr_value[0].split(':')[0]
                disk["name"] = arr_value[0].split(':')[1]
                for item in arr_value:
                    if "=" in item:
                        arr_item = item.split('=')
                        disk[arr_item[0]] = arr_item[1]
                json_out["disk"]["list"].append(disk)
            if "bios" in key:
                json_out["bios"] = { "name": key }
                arr_value = value.split(',')
                for item in arr_value:
                    if "=" in item:
                        arr_item = item.split('=')
                        json_out["bios"][arr_item[0]] = arr_item[1]
            if "unused" in key:
                disk = { 
                    "device": key,
                    "status": "unused"
                }
                arr_value = value.split(',')
                disk["datastore"] = arr_value[0].split(':')[0]
                disk["name"] = arr_value[0].split(':')[1]
                json_out["disk"]["list"].append(disk)

        return json_out

    def get_guest_info(self, vmid):
        try:
            vms = self.api.cluster.resources.get(type='vm')
            for vm in vms:
                if 'vmid' in vm and str(vm['vmid']) == vmid:
                    vmstatus = vm
                    break
            result = self.api.nodes(vmstatus["node"]).qemu(vmid).agent.get("get-osinfo")
            vmosinfo = {
                "pretty-name": result["result"].get('pretty-name', 'Unknown'),
                "version": result["result"].get('version-id', 'Unknown'),
                "kernel-version": result["result"].get('kernel-version', 'Unknown'),
                "machine": result["result"].get('machine', 'Unknown'),
                "error": False
            }
        except ResourceException as e:
            vmosinfo = {
                "pretty-name": e.content,
                "error": True
            }
        json_out = {
            "osinfo": vmosinfo
        }

        return json_out
    
    def run_poweron(self, vmid):
        try:
            vms = self.api.cluster.resources.get(type='vm')
            for vm in vms:
                if 'vmid' in vm and str(vm['vmid']) == vmid:
                    vmstatus = vm
                    break
            result = self.api.nodes(vmstatus["node"]).qemu(vmid).status.start.post()
            arr_res = result.split(":")
            json_out = { 
                arr_res[0]: {
                    "node": arr_res[1],
                    "pid_hex": arr_res[2],
                    "pstart_hex": arr_res[3],
                    "start_hex": arr_res[4],
                    "type": arr_res[5],
                    "id": arr_res[6],
                    "user": arr_res[7],
                }
            }
        except ResourceException as e:
            json_out = {
                "message": e.content,
                "error": True
            }
        
        return json_out

    def run_poweroff(self, vmid):
        try:
            vms = self.api.cluster.resources.get(type='vm')
            for vm in vms:
                if 'vmid' in vm and str(vm['vmid']) == vmid:
                    vmstatus = vm
                    break
            result = self.api.nodes(vmstatus["node"]).qemu(vmid).status.stop.post(skiplock=1)
            arr_res = result.split(":")
            json_out = { 
                arr_res[0]: {
                    "node": arr_res[1],
                    "pid_hex": arr_res[2],
                    "pstart_hex": arr_res[3],
                    "start_hex": arr_res[4],
                    "type": arr_res[5],
                    "id": arr_res[6],
                    "user": arr_res[7],
                }
            }
        except ResourceException as e:
            json_out = {
                "message": e.content,
                "error": True
            }
        
        return json_out
    
    def run_shutdown(self, vmid):
        try:
            vms = self.api.cluster.resources.get(type='vm')
            for vm in vms:
                if 'vmid' in vm and str(vm['vmid']) == vmid:
                    vmstatus = vm
                    break
            result = self.api.nodes(vmstatus["node"]).qemu(vmid).status.shutdown.post(
                forceStop=1,
                skiplock=1
            )
            print(result)
            arr_res = result.split(":")
            json_out = { 
                arr_res[0]: {
                    "node": arr_res[1],
                    "pid_hex": arr_res[2],
                    "pstart_hex": arr_res[3],
                    "start_hex": arr_res[4],
                    "type": arr_res[5],
                    "id": arr_res[6],
                    "user": arr_res[7],
                }
            }
        except ResourceException as e:
            json_out = {
                "message": e.content,
                "error": True
            }
        
        return json_out

    def vm_status(self, vmid):
        try:
            vms = self.api.cluster.resources.get(type='vm')
            for vm in vms:
                if 'vmid' in vm and str(vm['vmid']) == vmid:
                    vmstatus = vm
                    break
            result = self.api.nodes(vmstatus["node"]).qemu(vmid).status.current.get()
            json_out = result
        except ResourceException as e:
            json_out = {
                "message": e.content,
                "error": True
            }
        
        return json_out
        
    def boot_order(self, vmid, order):
        try:
            vms = self.api.cluster.resources.get(type='vm')
            for vm in vms:
                if 'vmid' in vm and str(vm['vmid']) == vmid:
                    vmstatus = vm
                    break
            str_order = ";".join(order)
            result = self.api.nodes(vmstatus["node"]).qemu(vmid).config.set(boot=f'order={str_order}')
            json_out = {
                "message": f"Boot order changed: {str_order}\n [i] You need to reboot from PVE or API to apply changes"
            }
        except ResourceException as e:
            json_out = {
                "message": e.content,
                "error": True
            }

        return json_out
    
    def eject_iso(self, vmid):
        try:
            vms = self.api.cluster.resources.get(type='vm')
            vmstatus = ""
            for vm in vms:
                if 'vmid' in vm and str(vm['vmid']) == vmid:
                    vmstatus = vm
                    break
            if vmstatus == "":
                return {
                    "error": True,
                    "message": "No VM found"
                }
            result = self.api.nodes(vmstatus["node"]).qemu(vmid).config.set(cdrom='none')
            json_out = {
                "message": result
            }
        except ResourceException as e:
            json_out = {
                "message": e.content,
                "error": True
            }

        return json_out

    def mount_iso(self, vmid, iso):
        vms = self.api.cluster.resources.get(type='vm')
        vmstatus = ""
        for vm in vms:
            if 'vmid' in vm and str(vm['vmid']) == vmid:
                vmstatus = vm
                break
        if vmstatus == "":
            return {
                "error": True,
                "message": "No VM found"
            }
        iso_path = ""
        for stg in self.api.nodes(vmstatus["node"]).storage.get():
            for content in self.api.nodes(vmstatus["node"]).storage(stg["storage"]).content.get(content="iso"):
                if iso in content["volid"]:
                    iso_path = content["volid"]
                    break
        if iso_path == "":
            return {
                "error": True,
                "message": "No ISO found"
            }
        result = self.api.nodes(vmstatus["node"]).qemu(vmid).config.set(cdrom=iso_path)
        json_out = {
                "message": result
            }
        
        return json_out
