from gi.repository import Nautilus, GObject
from typing import List
import subprocess
import json
import urllib.parse


class Device:
    def __init__(self, name:str, hostname:str):
        self.name = name
        self.hostname = hostname

class DeviceMenuItem(Nautilus.MenuItem):
    def __init__(self, hostname: str, *args, **kwargs):
        self.hostname = hostname 
        super().__init__(*args, **kwargs)        

class StatusResult:
    def __init__(self):
        self.online: List[Device] = []
        self.offline: List[Device] = []

def get_tailscale_status() -> StatusResult:
    try:
        output = subprocess.check_output(["tailscale status --self=false --json"], shell=True)
    except subprocess.CalledProcessError as e:
        print(e)
        return
    
    output = json.loads(output)
    status = StatusResult()

    for node_id, node in output["Peer"].items():
        device = Device(name=node["HostName"], hostname=node["DNSName"])
        if node["Online"] == True:
            status.online.append(device)
        elif node["Online"] == False:
            status.offline.append(device)
    return status


class SendToTailscaleMenuProvider(GObject.GObject, Nautilus.MenuProvider):
    def __init__(self):
        super().__init__()
        self.status = get_tailscale_status()

    def submenu_activate_cb(
        self,
        menu: DeviceMenuItem,
        files:[Nautilus.FileInfo]
    ):

        paths = []
        for f in files:
            uri = f.get_uri()
            path = uri.replace("file://", "")
            path = urllib.parse.unquote(path)
            paths.append(path)
        
        if len(paths) > 0:
            command = f"tailscale file cp {' '.join(f'"{p}"' for p in paths)} '{menu.hostname}':"
            print(command)
            print(subprocess.check_output(command, shell=True))


    def get_file_items(
        self,
        files: List[Nautilus.FileInfo],
    ) -> List[Nautilus.MenuItem]:
        
        if len(files) == 0: return
        for f in files:
            if f.is_directory(): return # in theory could zip this

        self.status = get_tailscale_status() # if this is slow then consider an alternative approach

        top_menuitem = Nautilus.MenuItem(
            name="SendToTailscaleMenuProvider::SendTo",
            label="Send to Tailscale",
            tip="Send file(s) to a Tailscale device",
            icon="",
        )

        submenu = Nautilus.Menu()

        for device in sorted(self.status.online, key=lambda x:x.name.lower()):
            device_item =  DeviceMenuItem(
                    name="SendToTailscaleMenuProvider::Item",
                    label=f"{device.name} ({device.hostname.split(".")[0]})",
                    hostname=f"{device.hostname}"
                )

            device_item.connect("activate", self.submenu_activate_cb, files)
            submenu.append_item(
               device_item
            )
        for device in sorted(self.status.offline, key=lambda x:x.name.lower()):
            device_item =  Nautilus.MenuItem(
                    name="SendToTailscaleMenuProvider::Item",
                    label=f"{device.name} ({device.hostname.split(".")[0]})",
                    sensitive=False
                )
            submenu.append_item(
               device_item
            )    

        top_menuitem.set_submenu(submenu)
        return [ top_menuitem]


