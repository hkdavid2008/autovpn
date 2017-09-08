#####################################################################
# Project: autovpn
# desc: light weight One Vpn management program with web interface
# author: Sai Innamuri <sundeepi9@yahoo.in>
# 
#####################################################################

Motivation: 
Open Vpn disconnects everytime network is changed or computer wakes from sleep.
With the recent attack on "Vpn" our organisation enforced MFA. This created a 
lot of trouble to someone like me who often forgets their phone at home :) and 
hence this project.

Steps: 
-------
1. install OpenVpn on your system
2. download .ovpn file for your vpn. (contact your system admin if ur not sure what this is)
3. if u are a developer clone master/develop, else clone/download release branch
4. configure the resources\config.json. 

		config.json 
		------------
		{
		  "secret"     : "RHXC4PAKKPD2CQWERTYUIPTC2C6C2XT", // your MFA secret. Scan the QR 
																code with barcode scanner 
																and enter the secret here
		  "username"   : "Krishnam",                        // your Open Vpn user name
		  "password"   : "VandeJagathgurum"                 // Your Open Vpn password
		  "guardSec"   : 7,									// gaurd interval to pick OTP. 
																will pick if the otp is gng 
																to expire in less than 7 sec
		  "ovpn_file"  : "client.ovpn",                     //.ovpn file path. copy it to project 
																root to avoid any plausibke
		  "appLoc"     : "C:/\"Program Files\"/OpenVPN/bin/openvpn.exe",
															//openvpn executable path on your system
															   becarefull with the spaces. 
		  "port"       :9001                                //port on which the web interface should run
		}
		
5. if u are in develop/master run the main.py python file as Admin
6. if u are in release branch run the vpn.bat from commad line as admin. 
	(I hope to make it a windows service once all the bugs are taken care of)
7. go to page localhost:9001/index. this the web interface for our program.
8. test with a page that os only accessible through the Vpn
