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
import ssl


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


class logger():

    levels = {
        'error' : [0, "ERROR"],
        'warn' : [1, "WARN"],
        'info' : [2, "INFO"],
        'debug' : [3, "DEBUG"]
    }

    def __init__(self, logLevel):
        if logLevel >=0 and logLevel <=3:
            self.logLevel = logLevel
        else: raise ValidationError("undefined level "+ str(logLevel), "UNKNOWN_LOG_LEVEL")

    def error(self, *logs):
        level = self.levels["error"]
        self.cl( level[0], level[1], *logs)

    def warn(self, *logs):
        level = self.levels["warn"]
        self.cl(level[0], level[1], *logs)

    def info(self, *logs):
        level = self.levels["info"]
        self.cl(level[0], level[1], *logs)

    def debug(self, *logs):
        level = self.levels["debug"]
        self.cl(level[0], level[1], *logs)

    def cl(self, levelInt, levelString, *logs):
        ts = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        tolog = levelString
        for log in logs:
            tolog = tolog + " - " + str(log)
        tolog = ts + tolog
        if levelInt >= 1:
            msgs["timestamp"] = ts
            msgs["msg"] = tolog
        if levelInt <= self.logLevel:  print tolog

log = logger(getDataFromConf("loglevel"))

connectProc = None
nmProc = None
autoConnect = getDataFromConf("autoConnect")
ips_t = {
        "external-ip": "",
        "SSID": "",
        "BSSID": ""
    }
ips = ips_t
msgs = {}


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
        log.debug("httpreq", "/stats")
        return json.dumps({"stats": monitor(), "ips": ips, "msgs" : msgs})

    @app.route("/index")
    def index():
        log.info("httpreq", "/index")
        with open("./web/index.html", 'rb') as f:
            return f.read()

    @app.route("/web/app.js")
    def appJs():
        log.info("httpreq", "/web/app.js")
        with open("./web/app.js", 'rb') as f:
            return f.read()

    @app.route("/disconnect")
    def disconnect():
        log.info("httpreq", "/disconnect")
        autoConnect = False
        msgs["autoconnect"] = autoConnect
        log.debug("return success", "disconnect")
        return "success"


    @app.route("/autoConnect")
    def autoConnect():
        log.info("httpreq", "/autoConnect")
        autoConnect = True
        msgs["autoconnect"] = autoConnect
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
        log.error("monitor", "exception",str(e))

    return stats


def connect():
    log.info("connect", "new process", "connect")
    while(1):
        if os.path.exists("vpn.log"):
            log.info("connect", "removing file", "vpn.log")
            os.remove("vpn.log")

        with open("resources/up" , "w") as up:
            up.write(getDataFromConf("username")+"\n")
            up.write(getDataFromConf("password"))
            up.write(get_otp(getDataFromConf("guardSec")))

        cmd = "{} --config {} --status resources/vpn.status 2 --auth-user-pass {} >> resources/vpn.log".format(getDataFromConf("appLoc"),
                                                          "resources" + "/" + getDataFromConf("ovpn_file"),
                                                          "resources/up")
        log.info("connect", "issuing command", cmd)
        p = os.system(cmd)

        if p != 0:
            msgs["fail#"]  = msgs["fail#"] + 1
            if msgs["fail#"]> 2:
                connectProc = None
                break
        log.error ("connect", 'Some error with the vpn connection", "Connection closed')


def getExternalIp():
    try:
        gcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        return True, urllib2.urlopen("https://myexternalip.com/raw", context=gcontext).read().rstrip();
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
            log.warn("nChange", "Looks like a change in BSSID" , wlanStats["BSSID"])
            ret, ips["external-ip"] = getExternalIp()
            ips["BSSID"] = wlanStats["BSSID"]
            ips["SSID"] = wlanStats["SSID"]
            if ret:
                log.warn("nChange", "confirmed internet. req to restart VPN" )
                return "stop,start"
            else:
                log.warn("nChange", "confirmed no internet. req to stop VPN")
                return "stop"
        else:
            log.debug("nChange", "No BSSID change, no Action required")
            return ""
    else:
        if(ips["BSSID"] == ""):
            log.debug("nChange", "No network Connected yet, no Action required")
            return ""
        else:
            ips["external-ip"] = ""
            ips["SSID"] = ""
            ips["BSSID"] = ""
            log.warn("nChange", "Network Connection lost, stopping VPN")
            return "stop"


def start(proc, newProc, type = "None"):
    log.info ("startpr", "req to start a process", type)
    if proc is not None:
        kill_child_processes(proc.pid)
        proc.terminate()
    newProc.start()
    return newProc


def stop(proc, type = "None"):
    if proc != None:
        log.info("stoppro", "request to stop a process", proc.pid, type)
        kill_child_processes(proc.pid)
        proc.terminate()
    return None


def networkMonitor():
    log.debug("nmonitr", "new process", "networkMonitor")
    global connectProc
    sleepInterval = 2
    while(True):
        if not autoConnect:
            sleepInterval == 5
            connectProc = stop(connectProc, "connect()")
            time.sleep(sleepInterval)
            continue

        status = detectNetworkChange()
        for s in status.split(","):
            if s == "start":
                connectProc = start(connectProc, Process(target=connect), "connect()")
            elif s == "stop":
                connectProc = stop(connectProc, "connect()")
        if connectProc is None: sleepInterval = 5
        else: sleepInterval = 2
        log.debug("nmonitr", "sleeping for", sleepInterval)
        time.sleep(sleepInterval)


if __name__ == '__main__':
    Thread(target = view).start()
    networkMonitor()

