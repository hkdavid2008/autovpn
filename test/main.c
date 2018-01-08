#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#define snprintf _snprintf

void writeHttpsRequest(const char *format, ...) {
	va_list ap;
	va_start(ap, format);
    int size = vsnprintf(NULL, 0, format, ap);
    char *pkt = (char *)malloc(size+1);
    vsprintf(pkt, format, ap);
    printf("http request: %s\n", pkt);
    free(pkt);
	va_end(ap);
}

static void dmRegisterHTTPS() {
        char *sn="simsim", *uid="uid", *cloudToken="cloudtoken", *did="did", *cloudHostname="129.123.123.342";
		char *format = "{\"sn\":\"%s\",\"climsg\":\"up.to.date\",\"uids\":[\"%s\"],\"os\":\"N/A\",\"app\":\"N/A\",\"assetType\":\"SIM\",\"token\":\"%s\",\"did\":\"%s\",\"clientUrl\":\"https://devicemgr-dev.fcawitech.com\"}";
		int contentLength = snprintf(NULL, 0, format, sn, uid, cloudToken, did);
		char *content = malloc(contentLength + 1);
		sprintf(content, format, sn, uid, cloudToken, did);
		writeHttpsRequest("POST /registerPendingConnection HTTP/1.1\r\n"
			"Host: %s\r\n"
			"accept: */*\r\n"
			"Connection: Keep-Alive\r\n"
			"content-type: application/json\r\n"
			"content-length: %d\r\n\r\n", cloudHostname, contentLength);
}
