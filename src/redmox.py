#!/usr/bin/env python3
import os
from waitress import serve
from libs.apilib import RedmoxAPI
from libs.common import Clr

def get_configs():
    """
    Function to get the configuration from the environment variables
    """
    configs_out = {
        "proxmox_host": os.getenv("PMOX_ADDR"),
        "proxmox_port": os.getenv("PMOX_PORT"),
        "log_debug": os.getenv("DEBUG")
    }
    
    return configs_out

if __name__ == "__main__":
    configs = get_configs()
    rdx_api = RedmoxAPI(configs)
    app = rdx_api.app

    print(f"{Clr.purple}#### Starting Redmox Server ####{Clr.reset}\n")
    if configs["log_debug"] != "" and configs["log_debug"].lower() == "yes":
        print(f"{Clr.red}Debug Mode: [ENABLED]{Clr.reset}\n")
    print(f"-----------------------\n|    {Clr.cyan}PROXMOX SERVER{Clr.reset}   |\n-----------------------")
    print(f'- {Clr.green}HOST{Clr.reset}: {configs["proxmox_host"]}\n- {Clr.green}PORT{Clr.reset}: {configs["proxmox_port"]}')
    print("-----------------------\n")
    #app.run(debug=True)
    serve(app, host="0.0.0.0", port=5000)