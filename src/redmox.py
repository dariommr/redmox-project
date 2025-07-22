#!/usr/bin/env python3
import os
import yaml
from waitress import serve
from libs.apilib import RedmoxAPI
from libs.common import Clr, set_logger

if __name__ == "__main__":
    logger = set_logger("RedMox")
    configs = yaml.safe_load(open("configs.yaml", "r"))
    if os.getenv("DEBUG") not in [ "yes", "no"]:
        logger.error(f"Define Debug mode properly. Env. Variable: [{Clr.purple}DEBUG{Clr.reset}], values {Clr.green}yes/no{Clr.reset}")
        exit()
    if configs["redfish"]["mode"] not in [ "simple", "multi" ]:
        logger.error(f"Define Mode properly, values {Clr.green}simple/multi{Clr.reset}")
        exit()
    if configs["redfish"]["mode"] == "simple":
        if not configs["redfish"]["vmid"] or configs["redfish"]["vmid"] == "":
            logger.error(f"Please set the VMs associated with the manager. Env. Variable: [{Clr.purple}VMIDS{Clr.reset}]")
            exit()
    debug = True if os.getenv("DEBUG") == "yes" else False

    rdx_api = RedmoxAPI(configs, debug=debug)
    app = rdx_api.app

    print(f"{Clr.purple}#### Starting Redmox Server ####{Clr.reset}\n")
    if debug:
        print(f"{Clr.red}Debug Mode: [ENABLED]{Clr.reset}\n")
    print(f"-----------------------\n|    {Clr.cyan}PROXMOX SERVER{Clr.reset}   |\n-----------------------")
    print(f'- {Clr.green}HOST{Clr.reset}: {configs["proxmox"]["host"]}\n- {Clr.green}PORT{Clr.reset}: {configs["proxmox"]["port"]}')
    print("-----------------------\n")

    if debug:
        app.run(debug=True)
    else:
        serve(app, host=configs["redfish"]["host"], port=configs["redfish"]["port"])