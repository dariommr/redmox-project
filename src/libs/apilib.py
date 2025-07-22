import time
import json
import random
import uuid
import logging, sys
from functools import wraps
from datetime import datetime
from flask import Flask, request, render_template, make_response
from libs.pmoxlib import Proxmox
from libs.common import CustomFormatter

global SESSIONS
SESSIONS = {}

def bmc_map():
    json_out = {}
    with open("bmc_map", "r") as f:
        arr_map = [ x.split() for x in f.readlines() ]
    for line in arr_map:
        json_out[line[0]] = line[1]
    
    return json_out

class RedmoxAPI():
    def __init__(self, configs, debug=False):
        self.configs = configs
        self.app = Flask("RedmoxAPI")
        for handler in self.app.logger.handlers[:]:
            self.app.logger.removeHandler(handler)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(CustomFormatter())
        if debug:
            self.app.logger.setLevel(logging.DEBUG)
        else:
            self.app.logger.setLevel(logging.INFO)
        self.app.logger.addHandler(handler)
        self.app.logger.propagate = False
        self.current_user = ''
        with open("bmc_map", "r") as f:
            arr_map = [ x.split() for x in f.readlines() ]
        self.bmc_map = {}
        for line in arr_map:
            self.bmc_map[line[0]] = line[1]

        # Authentication decorator
        def token_required(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                token = request.headers.get('x-auth-token')
                if not token:
                    self.app.logger.error("No valid token provided")
                    return make_response(json.dumps({"message": "A valid token is missing!"}, indent=4), 401)
                try:
                    if len(SESSIONS) == 0:
                        self.app.logger.error("No sessions are created")
                        return make_response(json.dumps({"message": "Invalid token!"}, indent=4), 401)
                    match_flag = False
                    for key in SESSIONS.keys():
                        if token == key:
                            match_flag = True
                    if match_flag:
                        if SESSIONS[token]["UserName"] != self.current_user:
                            self.pmox = Proxmox(
                                host=self.configs["proxmox"]["host"],
                                port=self.configs["proxmox"]["port"],
                                user=SESSIONS[token]["UserName"],
                                password=SESSIONS[token]["Password"]
                            )
                        self.app.logger.info("Proxmox session initiated")
                    else:
                        self.app.logger.error("No valid token provided")
                        return make_response(json.dumps({"message": "Invalid token!"}, indent=4), 401)
                except Exception as e:
                    self.app.logger.error(f"Error opening sessions: {e}")
                    return make_response(json.dumps({"message": "Invalid token!", "error": e}, indent=4), 401)
                return f(*args, **kwargs)
            return wrapper

        @self.app.before_request
        def log_request():
            message = f"{request.remote_addr} {request.method} {request.path}"
            if request.method in ['POST', 'PUT'] and self.app.logger.isEnabledFor(logging.DEBUG):
                message += f" DATA: {request.get_data(as_text=True)}"
            self.app.logger.info(message)

        @self.app.after_request
        def log_responses(response):
            if response.status_code != 200:
                self.app.logger.warning(f"=> {response.status}")
            return response

        @self.app.route("/", methods=["GET"])
        def root():
            return ''

        @self.app.route("/redfish", methods=["GET"])
        def redfish():
            json_out = {
                "v1": "/redfish/v1"
            }
            return json_out

        @self.app.route("/redfish/v1", methods=["GET"])
        @token_required
        def v1():
            try:
                rules = {}
                for rule in self.app.url_map.iter_rules():
                    if rule.endpoint not in ['static', 'redfish', 'v1']:
                        rules[rule.endpoint] = {
                            "@odata.id": rule.rule
                        }
                pre_json = render_template("root.json")
                json_out = json.loads(pre_json)
                json_out.update(rules)
                error_code = 200
            except Exception as e:
                message = f"Error getting rules: {e}"
                error_code = 500
                self.app.logger.error(message)
                json_out = {
                    "message": message
                }
            return make_response(json.dumps(json_out, indent=4), error_code)

        @self.app.route('/redfish/v1/Managers')
        @token_required
        def managers():
            return render_template('managers.json')

        @self.app.route(f'/redfish/v1/Managers/1', methods=['GET'])
        @token_required
        def manager():
            req_addr = request.url.split("/")[2].split(":")[0]
            vmid = self.bmc_map[req_addr]
            json_out = render_template(
                'manager.json',
                date_time=datetime.now().strftime('%Y-%M-%dT%H:%M:%S+00:00'),
                vmid=vmid
            )
            return json_out

        @self.app.route(f'/redfish/v1/Managers/1/VirtualMedia', methods=['GET'])
        @token_required
        def man_virtualmedias():
            try:
                self.app.logger.info("Getting the Proxmox ISO list")
                isos = self.pmox.list_isos()
                id_list = []
                for iso in isos:
                    arr_iso = iso.split("/")
                    id_list.append(arr_iso[-1])
                json_out = render_template(
                    'virtualmedias.json',
                    count=len(id_list),
                    id_list=id_list,
                    prefix="Managers/1"
                )
                error_code = 200
            except Exception as e:
                message = f"Error getting ISOs: {e}"
                error_code = 500
                self.app.logger.error(message)
                json_out = {
                    "message": message
                }
            return make_response(json_out, error_code)

        @self.app.route(f'/redfish/v1/Managers/1/VirtualMedia/<isoid>', methods=['GET'])
        @token_required
        def man_virtualmedia(isoid):
            try:
                self.app.logger.info("Getting the Proxmox ISO list")
                isos = self.pmox.list_isos()
                iso_path = ""
                for iso in isos:
                    arr_iso = iso.split("/")
                    if isoid == arr_iso[-1]:
                        iso_path = iso
                        iso_name = arr_iso[-1]
                if iso_path == "":
                    raise Exception("ISO not found in Proxox Storage")

                json_out = render_template(
                    'virtual_cd.json',
                    id=isoid,
                    image_url=iso_path,
                    name=iso_name,
                    inserted="true",
                    prefix="Managers/1"
                )
                error_code = 200
            except Exception as e:
                message = f"Error getting ISO: {e}"
                error_code = 500
                self.app.logger.error(message)
                json_out = {
                    "message": message
                }
            return make_response(json_out, error_code)

        @self.app.route('/redfish/v1/SessionService')
        def sessionservice():
            return render_template('sessionservice.json')

        @self.app.route('/redfish/v1/SessionService/Sessions', methods=['GET', 'POST'])
        def sessions():
            if request.method == 'POST':
                username = request.json.get('UserName')
                password = request.json.get('Password')
                try:
                    id = len(SESSIONS) + 1
                    token = f'{random.getrandbits(128):016x}'
                    location = f"{request.path}/{id}"
                    self.app.logger.info("New Session: Authenticating with ProxMox Server")
                    self.pmox = Proxmox(
                        host=self.configs["proxmox"]["host"],
                        port=self.configs["proxmox"]["port"],
                        user=username,
                        password=password
                    )
                    self.current_user = username
                    json_out = render_template(
                        'session.json',
                        pmox_name=self.pmox.name,
                        id=id,
                        username=username,
                        location=location,
                    )
                    session_out = { token: json.loads(json_out) }
                    session_out[token]["Password"] = password
                    SESSIONS.update(session_out)
                    header = f"HTTP/1.1 201 Created\nLocation: {location}\nX-Auth-Token: {token}\nContent-Type: application/json"
                    json_out = header +"\n\n"+ json_out
                except Exception as e:
                    self.app.logger.error(f"Unable to authenticate with ProxMox Server: {str(e)}")
                    return make_response(json.dumps({ "error": str(e) }, indent=4), 401)
            if request.method == 'GET':
                dict_out = []
                for token in SESSIONS.keys():
                    session = SESSIONS[token]
                    session["Password"] = "********"
                    dict_out.append(session)
                json_out = json.dumps(dict_out, indent=4)

            return json_out
        
        @self.app.route('/redfish/v1/SessionService/Sessions/<sessionid>', methods=['GET', 'DELETE'])
        @token_required
        def session(sessionid):
            if request.method == 'DELETE':
                self.app.logger.warning(f"Deleting Session: {sessionid}")
                for token in SESSIONS.keys():
                    if sessionid in SESSIONS[token]['Id']:
                        SESSIONS.pop(token)
                        return ''
                self.app.logger.error(f"Session: {sessionid} Not found")
                return '', 404
            for token in SESSIONS.keys():
                if sessionid in SESSIONS[token]['Id']:
                    session_out = SESSIONS[token]
                    session_out.pop("Password")
                    return session_out
            self.app.logger.error(f"Session: {sessionid} Not found")
            return '', 404

        @self.app.route('/redfish/v1/Chassis')
        @token_required
        def chassis_collection():
            return render_template('chassis_collection.json')

        @self.app.route('/redfish/v1/Chassis/1U', methods=['GET'])
        @token_required
        def chassis():
            uuid_out = uuid.UUID(int=1)
            req_addr = request.url.split("/")[2].split(":")[0]
            vmid = self.bmc_map[req_addr]
            self.app.logger.info(f"Getting information from VM: {vmid}")
            vm = self.pmox.get_vm_info(vmid)
            if "error" in vm.keys():
                return make_response(json.dumps(vm, indent=4), 404)
            if vm.get("status", "Unknown") == "running":
                power_state = "On"
            else:
                power_state = "Off"
            json_out = render_template(
                'chassis.json',
                uuid=uuid_out,
                vmid=vmid,
                power_state=power_state
            )
            return json_out

        @self.app.route('/redfish/v1/Chassis/1U/Power', methods=['GET'])
        @token_required
        def power():
            return render_template('power.json')

        @self.app.route('/redfish/v1/Chassis/1U/Thermal', methods=['GET'])
        @token_required
        def thermal():
            return render_template('thermal.json')

        @self.app.route("/redfish/v1/Systems", methods=["GET"])
        @token_required
        def Systems():
            members = []
            self.app.logger.info("Getting VMs list")
            for vmid in self.pmox.get_vms_id():
                members.append({
                    "@odata.id": f"/redfish/v1/Systems/{vmid}"
                })
            json_out = json.loads(render_template(
                "systems.json",
                members=json.dumps(members),
                count=len(members)
                )
            )
            return json.dumps(json_out, indent=4)

        @self.app.route("/redfish/v1/Systems/<id>", methods=["GET"])
        @token_required
        def System(id):
            self.app.logger.info(f"Getting information from VM: {id}")
            vm = self.pmox.get_vm_info(id)
            if vm.get("status", "Unknown") == "running":
                state = "Enabled"
                power_state = "On"
            else:
                state = "Disabled"
                power_state = "Off"
            cpus = vm.get("cpu", {})
            mem = vm.get("memory", {})
            json_out = render_template(
                "system.json",
                id=id,
                tags=",".join(vm.get("tags", [])),
                manufacturer=self.pmox.name,
                vm_name=vm.get("name", "Unknown"),
                sys_type=f'[{vm.get("type", "")}] Virtual Machine',
                vmgenid=vm.get("vmgenid", "0"),
                state=state,
                power_state=power_state,
                bootsourceoverride_enabled="None",
                bootsourceoverride_target="None",
                bootsourceoverride_mode="None",
                cpu_count=cpus["cores"] * cpus["sockets"],
                total_gb=int(mem["assigned_mb"]) / 1024
            )

            return json_out
        
        @self.app.route('/redfish/v1/Systems/<id>/Actions/ComputerSystem.Reset', methods=['POST'])
        @token_required
        def system_reset(id):
            reset_type = request.json.get('ResetType')
            if reset_type == 'On' or reset_type == 'ForceOn':
                result = self.pmox.run_poweron(id)
            if reset_type == 'ForceOff' or reset_type == 'PushPowerButton':
                result = self.pmox.run_poweroff(id)
            if reset_type == 'GracefulShutdown':
                result = self.pmox.run_shutdown(id)
            if reset_type == 'ForceRestart' or reset_type == 'GracefulRestart':
                if reset_type == 'GracefulRestart':
                    result = self.pmox.run_shutdown(id)
                else:
                    result = self.pmox.run_poweroff(id)
                qmstatus = "running"
                attempts = 0
                while qmstatus == "running" and attempts < 10:
                    attempts += 1
                    result = self.pmox.vm_status(id)
                    qmstatus = result["qmpstatus"]
                    time.sleep(3)
                if attempts == 10:
                    message = {
                        "message": "Timeout powering off the system"
                    }
                    return make_response(json.dumps(message, indent=4), 500)
                result = self.pmox.run_poweron(id)
            
            return '', 204

        @self.app.route('/redfish/v1/Systems/<id>/VirtualMedia', methods=['GET'])
        @token_required
        def vm_virtualmedias(id):
            try:
                self.app.logger.info(f"Getting list of ISOs in ProxMox: {id}")
                isos = self.pmox.list_isos_vm(id)
                id_list = []
                for iso in isos:
                    arr_iso = iso.split("/")
                    id_list.append(arr_iso[-1])
                json_out = render_template(
                    'virtualmedias.json',
                    count=len(id_list),
                    id_list=id_list,
                    prefix=f"Systems/{id}"
                )
            except Exception as e:
                self.app.logger.error(f"Unable to obtain ISOs list: {str(e)}")
                json_out = { "error": str(e) }
            return json_out

        @self.app.route('/redfish/v1/Systems/<id>/VirtualMedia/<isoid>', methods=['GET'])
        @token_required
        def vm_virtualmedia(id, isoid):
            self.app.logger.info(f"Getting ISO information for: {id}")
            isos = self.pmox.list_isos_vm(id)
            for iso in isos:
                arr_iso = iso.split("/")
                if isoid == arr_iso[-1]:
                    iso_path = iso
                    iso_name = arr_iso[-1]

            json_out = render_template(
                'virtual_cd.json',
                id=isoid,
                image_url=iso_path,
                name=iso_name,
                inserted="true",
                prefix=f"Systems/{id}"
            )
            return json_out

        @self.app.route('/redfish/v1/Systems/<id>/VirtualMedia/<isoid>/Actions/VirtualMedia.EjectMedia', methods=['POST'])
        @token_required
        def vm_ejectmedia(id, isoid):
            self.app.logger.info(f"Ejecting ISO {isoid} from VM: {id}")
            vm_info = self.pmox.get_vm_info(id)
            if not isoid in vm_info["media"]:
                self.app.logger.error(f"Media not mounted")
                return make_response(json.dumps({"message": "Media not mounted"}, indent=4), 500)
            result = self.pmox.eject_iso(id)

            return ""
        
        @self.app.route('/redfish/v1/Systems/<id>/VirtualMedia/<isoid>/Actions/VirtualMedia.InsertMedia', methods=['POST'])
        @token_required
        def vm_insertmedia(id, isoid):
            self.app.logger.info(f"Mounting ISO {isoid} on VM: {id}")
            isos = self.pmox.list_isos_vm(id)
            selected_iso = ""
            for iso in isos:
                if isoid in iso:
                    selected_iso = iso
                    break
            if selected_iso == "":
                self.app.logger.error(f"ISO {isoid} not found on the node")
                return make_response(json.dumps({"message": f"ISO {isoid} not found on the node"}, indent=4), 404)
            result = self.pmox.mount_iso(id, isoid)

            return ""

        @self.app.errorhandler(404)
        def page_not_found(e):
            message = f'[{request.method} {request.path}] Redfish endpoint not found'
            self.app.logger.error(message)
            json_out = {
                "error": message
            }
            return json_out, 404
    