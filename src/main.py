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

def cl(*logs):
    tolog = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    for log in logs:
        tolog = tolog + " ## " + str(log)
    print tolog

class ValidationError(Exception):
    def __init__(self, message, errors):
        super(ValidationError, self).__init__(message)
        self.errors = errors

config = None

with open(os.path.abspath("resources/config.json")) as data_file:
    config = json.load(data_file)

def getDataFromConf(key, mandatory = True):
    value = None
    if key in config.keys(): value = config[key]
    else: value = None
    if mandatory and ( value is None or value == "" or value == [] or value == {}): raise ValidationError("cannot find a mandatory config "+ str(key), "NO_CONFIG")
    return value

connectProc = None
nmProc = None
autoConnect = getDataFromConf("autoConnect")

ips_t = {
        "external-ip": "",
        "SSID": "",
        "BSSID": ""
    }
ips = ips_t

msgs_t = {
    "status": "",
    "fail#": 0,
    "msg": ""
}
msgs = msgs_t


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


def view():
    global autoConnect
    app = Flask(__name__)

    @app.route("/stats")
    def stat():
        cl("httpreq", "/stats")
        return json.dumps({"stats": monitor(), "ips": ips, "msgs" : msgs})

    @app.route("/index")
    def index():
        cl("httpreq", "/index")
        with open("./web/index.html", 'rb') as f:
            return f.read()

    @app.route("/web/app.js")
    def appJs():
        cl("httpreq", "/web/app.js")
        with open("./web/app.js", 'rb') as f:
            return f.read()


    @app.route("/disconnect")
    def disconnect():
        cl("httpreq", "/disconnect")
        global nmProc, connectProc, autoConnect
        cl("stopping", "vpn Connect")
        connectProc = stop(connectProc)
        cl("stopping", "network monitor")
        nmProc = stop(nmProc)
        autoConnect = False
        cl("return success", "disconnect")
        return "success"


    @app.route("/autoConnect")
    def autoConnect():
        cl("httpreq", "/autoconnect")
        global nmProc, connectProc, autoConnect
        cl("starting", "vpn Connect")
        connectProc = start(connectProc, Process(target=connect))
        cl("starting", "network monitor")
        nmProc = start(nmProc, Process(target=networkMonitor))
        autoConnect = True
        cl("return success", "autoconnect")
        return "success"

    app.run(port=9001)

def monitor():
    stats = {}
    try:
        f = open('resources/vpn.status', 'rU')
        for line in f.readlines():
            vals = line.split(",")
            if(len(vals)>1):
                stats[vals[0].replace(' ', '_')] = vals[1].rstrip()
    except Exception as e:
        cl("monitor", "exception",str(e))

    return stats


def connect():
    cl("connect", "new process", "connect")
    global connectProc, msgs, msgs_t
    msgs = msgs_t
    while(1):
        if os.path.exists("vpn.log"):
            cl("connect", "removing file", "vpn.log")
            os.remove("vpn.log")

        with open("resources/up" , "w") as up:
            up.write(getDataFromConf("username")+"\n")
            up.write(getDataFromConf("password"))
            up.write(get_otp(getDataFromConf("guardSec")))

        ips["status"] = "Connected"
        cmd = "{} --config {} --status resources/vpn.status 2 --auth-user-pass {} >> resources/vpn.log".format(getDataFromConf("appLoc"),
                                                          "resources" + "/" + getDataFromConf("ovpn_file"),
                                                          "resources/up")
        cl("connect", "issuing command", cmd)
        p = os.system(cmd)

        if p != 0:
            msgs["fail#"]  = msgs["fail#"] + 1
            if msgs["fail#"]> 2:
                cl("connect", "fail count more than 2")
                msgs["status"] = "disconnected"
                msgs["msg"] = "Smtnh Wrong! please check vpn.log"
                connectProc = None
                break
        cl ("connect", 'Some error with the vpn connection", "Connection closed')


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
            key, value = data[0].rstrip().lstrip(), "-".join(data[1:]).rstrip().lstrip()
            wlanStats[key] = value

    if "BSSID" in wlanStats.keys():
        if wlanStats["BSSID"]  != ips["BSSID"]:
            cl("nChange", "Looks like a change in BSSID" , wlanStats["BSSID"])
            ret, ips["external-ip"] = getExternalIp()
            ips["BSSID"] = wlanStats["BSSID"]
            ips["SSID"] = wlanStats["SSID"]
            if ret:
                cl("nChange", "confirmed internet. req to restart VPN" )
                return "stop,start"
            else:
                cl("nChange", "confirmed no internet. req to stop VPN")
                return "stop"
        else:
            cl("nChange", "No BSSID change, no Action required")
            return ""
    else:
        if(ips["BSSID"] == ""):
            cl("nChange", "No network Connected yet, no Action required")
            return ""
        else:
            ips["external-ip"] = ""
            ips["SSID"] = ""
            ips["BSSID"] = ""
            cl("nChange", "Network Connection lost, stopping VPN")
            return "stop"


def start(proc, newProc, type = "None"):
    cl ("startpr", "req to start a process", type)
    if connectProc is not None:
        kill_child_processes(proc.pid)
        proc.terminate()
    newProc.start()
    return newProc


def stop(proc, type = "None"):
    if proc != None:
        cl("stoppro", "request to stop a process", proc.pid, type)
        kill_child_processes(proc.pid)
        proc.terminate()
    return None


def networkMonitor():
    cl("nmonitr", "new process", "networkMonitor")
    global connectProc, ips, ips_t
    ips = ips_t
    if not autoConnect: return
    sleepInterval = 2
    while(True):
        status = detectNetworkChange()
        for s in status.split(","):
            if s == "start":
                connectProc = start(connectProc, Process(target=connect), "connect()")
            if s == "stop": connectProc = stop(connectProc, "connect()")
        if connectProc is None: sleepInterval = 5
        cl("nmonitr", "sleeping for", sleepInterval)
        time.sleep(sleepInterval)


if __name__ == '__main__':
    
    if nmProc == None:
        if autoConnect:
            nmProc = Process(target=networkMonitor)
            nmProc.start()
    view()

