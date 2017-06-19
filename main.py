import pyotp
import datetime
import os
import json
import time
from flask import Flask
from threading import Thread
from multiprocessing import Process
import urllib2
import signal, psutil

ips = {"external-ip": "", "internal-ip" : "", "vpn-ip": "", "SSID": "", "BSSID": "", "status" :""}
config = None


# -------------------------- general funtions---------------------start---
class ValidationError(Exception):
    def __init__(self, message, errors):
        super(ValidationError, self).__init__(message)
        self.errors = errors

with open(os.path.abspath("config.json")) as data_file:
    config = json.load(data_file)

def getDataFromConf(key, mandatory = True):
    value = None
    if key in config.keys(): value = config[key]
    else: value = None
    if mandatory and ( value is None or value == "" or value == [] or value == {}): raise ValidationError("cannot find a mandatory config "+ str(key), "NO_CONFIG")
    return value

def get_otp(gaurdSec):
    totp = pyotp.TOTP(getDataFromConf("secret"))
    t = totp.now()
    while not totp.verify(t, for_time=datetime.datetime.now()+ datetime.timedelta(seconds=gaurdSec)):
        time.sleep(gaurdSec)
        t = totp.now()
    return t

def kill_child_processes(parent_pid, sig=signal.SIGTERM):
    try:
      parent = psutil.Process(parent_pid)
    except psutil.NoSuchProcess:
      return
    children = parent.children(recursive=True)
    for process in children:
      process.send_signal(sig)
# -------------------------- general funtions---------------------end---

# -------------------------- functions for web---------------------start---
def view():
    app = Flask(__name__)

    @app.route("/stats")
    def stat():
        return json.dumps({"stats": monitor(), "ips": json.dumps(ips)})

    @app.route("/index")
    def index():
        with open("./web/index.html", 'rb') as f:
            return f.read()

    @app.route("/web/app.js")
    def appJs():
        with open("./web/app.js", 'rb') as f:
            return f.read()

    app.run(port=9001)

# -------------------------- functions for web---------------------start---

# -------------------------- functions for vpn---------------------start---
def monitor():
    stats = {}
    try:
        f = open('vpn.status', 'rU')
        for line in f.readlines():
            vals = line.split(",")
            if(len(vals)>1):
                stats[vals[0].replace(' ', '_')] = vals[1].rstrip()
    except Exception as e:
        print(str(e))
        print("thats all we got")
    print(stats)
    return stats

def connect():
    while(1):
        if os.path.exists("vpn.log"): os.remove("vpn.log")
        with open("up" , "w") as up:
            up.write(getDataFromConf("username")+"\n")
            up.write(getDataFromConf("password"))
            up.write(get_otp(getDataFromConf("guardSec")))

        cmd = "{} --config {} --status vpn.status 2 --auth-user-pass {}>>vpn.log".format(getDataFromConf("appLoc"),
                                                          getDataFromConf("config_file"),
                                                          "up")
        ccc = "cd {};pwd".format(getDataFromConf("appLoc"))
        p = os.system(cmd)
        print ('exited')
# -------------------------- functions for vpn---------------------start---


# -------------------------- functions for network---------------------start---
def getExternalIp():
    try:
        return True, urllib2.urlopen("https://myexternalip.com/raw").read().rstrip();
    except Exception as e:
        return False, ""

def detectNetworkChange():
    wlan = os.popen("netsh wlan show interfaces")
    lines = wlan.readlines()
    wlanStats = {}
    for line in lines:
        data = line.split(":")
        if len(data) > 1:
            key, value = data[0].rstrip().lstrip(), data[1].rstrip().lstrip()
            wlanStats[key] = value

    if "BSSID" in wlanStats.keys():
        if wlanStats["BSSID"]  != ips["BSSID"]:
            ret, ips["external-ip"] = getExternalIp()
            ips["BSSID"] = wlanStats["BSSID"]
            ips["SSID"] = wlanStats["SSID"]
            if ret: return "stop,start"
            else: return "stop"
        else: return ""
    else:
        if(ips["BSSID"] == ""): return ""
        else:
            ips["external-ip"] = ""
            ips["SSID"] = ""
            ips["BSSID"] = ""
            ips["vpn-ip"] = ""
            return "stop"

def networkMonitor():
    proc = None
    sleepInterval = 2

    def start():
        print ("start req")
        if proc is not None:
            kill_child_processes(proc.pid)
            proc.terminate()
        sleepInterval = 2
        p = Process(target=connect)
        p.start()
        return p

    def stop():
        print ("stop req")
        if proc != None:
            kill_child_processes(proc.pid)
            proc.terminate()
        sleepInterval = 5
        return None

    while(True):
        print "new"
        status = detectNetworkChange()
        for s in status.split(","):
            if s == "start": proc = start()
            if s == "stop": proc = stop()
        time.sleep(sleepInterval)
# -------------------------- functions for network---------------------end---

if __name__ == '__main__':
    Thread(target=networkMonitor).start()
    Thread(target=view).start()

