import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
from src.autovpn import *

class AppServerSvc (win32serviceutil.ServiceFramework):
    _svc_name_ = "autovpn"
    _svc_display_name_ = "AutoVPN"

    def __init__(self,args):
        win32serviceutil.ServiceFramework.__init__(self,args)
        self.hWaitStop = win32event.CreateEvent(None,0,0,None)
        socket.setdefaulttimeout(60)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)

        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_,''))
        self.main()

    def main(self):
        rc = None
        print "started"
        Thread(target=view).start()
        Thread(target=networkMonitor).start()
        while rc != win32event.WAIT_OBJECT_0:
            rc = win32event.WaitForSingleObject(self.hWaitStop, 24 * 60 * 60 * 1000)
        stop(connectProc)
        sys.exit(0)


if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(AppServerSvc)
