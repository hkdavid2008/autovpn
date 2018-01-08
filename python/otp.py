import pyotp
import datetime
import time
import sys

secret = sys.argv[1]
gaurdSec = int(sys.argv[2])
totp = pyotp.TOTP(sys.argv[1])
t = totp.now()
while not totp.verify(t, for_time=datetime.datetime.now()+ datetime.timedelta(seconds=gaurdSec)):
    time.sleep(gaurdSec)
    t = totp.now(secret)

print t
