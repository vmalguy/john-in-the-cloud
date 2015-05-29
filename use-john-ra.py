#!/usr/bin/env python

from __future__ import unicode_literals, print_function, with_statement
from os import path
import os
import sys
import time
import random
from array import *

from fabric.api import *
from fabric.contrib.console import confirm
from fabric.contrib.files import append,exists

from runabove import Runabove
from runabove.exception import APIError

from ConfigParser import SafeConfigParser

parser = SafeConfigParser()
parser.read('settings.conf')
env.key_filename = parser.get('ra','ssh_key_filename')
application_key = parser.get('ra', 'application_key')
application_secret = parser.get('ra','application_secret')
consumer_key = parser.get('ra','consumer_key')

list_ip = []
list_con = []
node_list = ""
ips_master = ""
env.connection_attempts = 5
env.parallel = True


#fonction fabric pour installer john the ripper
def install_pre():
	with hide('output'):
		run("date")
		#copy de la clef  pour que tous les host se parle entre eu
		with open(os.path.expanduser(env.key_filename)) as f:
	         key_text = f.read()
	    #bug : on devrait overight pas append
		append('~/.ssh/id_rsa', key_text)
		with open(os.path.expanduser(env.key_filename + '.pub')) as f:
	         key_text = f.read()
	    #bug : on devrait overight pas append
		append('~/.ssh/id_rsa.pub', key_text)
		run ("chmod 0600 ~/.ssh/*")
		run ("sudo apt-get update")
		run ("sudo apt-get install libopenmpi-dev openmpi-bin build-essential libssl-dev nfs-common -y")
		env.warn_only = True
		run ("sudo mkdir /var/mpishare 2> /dev/null ")
		run ("sudo umount /var/mpishare 2> /dev/null")
		env.warn_only = False
		#run ("wget http://www.openwall.com/john/j/john-1.8.0-jumbo-1.tar.gz")
		#put("john-1.8.0-jumbo-1.tar.gz", "john-1.8.0-jumbo-1.tar.gz")
		#run ("tar xzvf john-1.8.0-jumbo-1.tar.gz")
		#run ("cd john-1.8.0-jumbo-1/src/ ; ./configure --enable-mpi")
		#run ("cd john-1.8.0-jumbo-1/src/ ; make clean && make -s")
		#run ("mv john-1.8.0-jumbo-1 /usr/share/")
		#recup le nombre de core et le mettre dans la mpi-host
		#for host in nodelist
		run ("sudo chmod 777 /etc/ssh/ssh_config")
		append("/etc/ssh/ssh_config","StrictHostKeyChecking no", use_sudo=True)
		#run ("sudo echo \"StrictHostKeyChecking no\" >> /etc/ssh/ssh_config")
		#for ips in list_ip:
			#FIXME : use appen + nombre de core dynamiquement
			#run ("echo \"%s slots=`nproc`\"> john-1.8.0-jumbo-1/run/mpi-nodes.txt" % (ips))

def launch_john():
	#run ("mpiexec   -hostfile john-1.8.0-jumbo-1/run/mpi-nodes.txt john-1.8.0-jumbo-1/run/john --test")
	with open(os.path.expanduser(parser.get('ra','hashfile'))) as f:
	         key_text = f.read()
	put("hash", '/var/mpishare/hash')
	#put("cain.txt", '/var/mpishare/cain.txt')
        cmd = "time mpiexec   -hostfile /var/mpishare/mpi-nodes.txt john-1.8.0-jumbo-1/run/john /var/mpishare/hash --pot=/var/mpishare/shared.pot --wordlist=john-1.8.0-jumbo-1/run/password.lst --rules=All "
        if len(sys.argv) > 1:
            cmd = cmd + sys.argv[1]
	run (cmd)


def nfs_master():
	with hide('output'):
		run ("sudo apt-get install  nfs-kernel-server portmap -y") 
		run ("sudo chmod 777 /etc/exports")
		append("/etc/exports", "/var/mpishare	  *(rw,sync)",use_sudo=True)
		#run ("sudo echo \"/var/mpishare	  *(rw,sync)\" > /etc/exports")
		env.warn_only = True
		run ("sudo service rpcbind  restart")
		run ("sudo service nfs-kernel-server restart")
		run("rm /var/mpishare/mpi-nodes.txt")
		env.warn_only = False
		#run ("sudo exportfs -a ")
		run ("sudo chmod 777 /var/mpishare/")
		#run ("echo `ip a | grep global | awk '{print $2}' | awk -F\"/\" '{print $1}'` slots=`nproc` > /var/mpishare/mpi-nodes.txt")
		append("/var/mpishare/mpi-nodes.txt", node_list)
		if not exists("/var/mpishare/john-1.8.0-jumbo-1.tar.gz"):
			run ("wget http://www.openwall.com/john/j/john-1.8.0-jumbo-1.tar.gz -O /var/mpishare/john-1.8.0-jumbo-1.tar.gz")
	


def build_john():
	with hide('output'):
		if not exists("john-1.8.0-jumbo-1/run/john"):
			run ("sudo cp /var/mpishare/john-1.8.0-jumbo-1.tar.gz .")
			run ("tar xzvf john-1.8.0-jumbo-1.tar.gz")
			run ("cd john-1.8.0-jumbo-1/src/ ; ./configure --enable-mpi")
			run ("cd john-1.8.0-jumbo-1/src/ ; make clean && make -s")



def nfs_node():
	env.warn_only = True
	run ("sudo mount %s:/var/mpishare /var/mpishare" % (ips_master))
	env.warn_only = False
	#run ("echo `ip a | grep global | awk '{print $2}' | awk -F\"/\" '{print $1}'` slots=`nproc`>> /var/mpishare/mpi-nodes.txt")
	
def pick_in_list(list_name, obj_list):
    """Generic function to ask the user to choose from a list."""
    print('\n%ss available' % list_name)
    for num, i in enumerate(obj_list):
        print('\t%d) %s' % (num+1, i.name))
    try:
        selected_num = raw_input('\nPlease select a %s number [1]: ' %
                                 list_name.lower())
        selected_num = int(selected_num) - 1
        selected = obj_list[selected_num]
    except (ValueError, IndexError):
        selected = obj_list[0]
    print('Using %s %s.' % (list_name.lower(), selected.name))
    return selected

# Create the Runabove SDK interface
ra = Runabove(application_key,
               application_secret,
               consumer_key=consumer_key)

# Check if the user has a Consumer Key
if not ra.get_consumer_key():
    print('\nEach user using your application needs a Consumer Key.')
    choice = raw_input('\nWould you like to get one? (y/N): ')
    if choice.lower() != 'y':
        print('Not requesting a Consumer Key, aborting')
        sys.exit(0)
    else:
        print('\nYou can get it here %s' % ra.get_login_url())
        raw_input('\nWhen you are logged, press Enter ')
        print('Your consumer key is: %s' % ra.get_consumer_key())

# Get information about the account
acc = ra.account.get()
print('\nHi %s,' % acc.first_name)

# Get the list of raning instances
choice = 'n'
instances = ra.instances.list()
print('\nYou have %d instance(s) runing' % len(instances))
for i in instances:
    print('\t- [%s] %s (%s, %s)' % (i.region.name, i.name, i.ip, i.image.name))
    if choice.lower() == 'a':
    	if "master" in i.name and  ips_master == "":
    		print ('MASTER FOUND !')
    		ips_master = i.ip
    	else:
	    	list_ip.append(i.ip)
	    	list_con.append("admin@"+i.ip)
    	node_list = node_list + i.ip + " slots=" + "6" + "\n"

    else:
    	choice = raw_input('\nWould you like to use it in the cluster ? : (a/y/N)')
    	if choice.lower() == 'y' or choice.lower() == 'a':
    		if "master" in i.name and  ips_master == "":
    			ips_master = i.ip
    			print ('MASTER FOUND !')
    		else:
		    	list_ip.append(i.ip)
		    	list_con.append("admin@"+i.ip)
    		node_list = node_list + i.ip + " slots=" + "6" + "\n" 



# Ask the user to select one region
region = pick_in_list('Region', ra.regions.list())


# Get the list of SSH keys in the selected region
ssh_keys = ra.ssh_keys.list_by_region(region)
if ssh_keys:
    print('\nYou have %d SSH key(s) in %s' % (len(ssh_keys), region.name))
    for s in ssh_keys:
        print('\t- [%s] %s (%s)' % (s.region.name, s.name, s.finger_print))


if ra.ssh_keys.list_by_region(region):
    choice = raw_input('\nHow many instances would you like to create  in %s? : '
                       % region.name)
    for i in range(0,int(choice)):
        #image = pick_in_list('Image', ra.images.list_by_region(region))
        #flavor = pick_in_list('Flavor', ra.flavors.list_by_region(region))
        #ssh_key = pick_in_list('SSH key', ra.ssh_keys.list_by_region(region))
	        image = ra.images.list_by_region(region)[14] #10) Ubuntu 14.04 Power 8 (a dynamiser)
	        flavor = ra.flavors.list_by_region(region)[3] #5) ra.p8.2xl
	        ssh_key = ra.ssh_keys.list_by_region(region)[2] # faire un grep from config
	        if  ips_master == "":
	        	instance_name = "master"
	        	print ('MASTER CREATED !')
	        else:
	        	instance_name = "node" + str(i)
	    
	        instance = ra.instances.create(region, instance_name,
	                                        flavor, image, ssh_key)
	        print('\nInstance created')
	        #parallel ? via instance+i =ra.. puis ACTIVE en cascade
	        print('Waiting for instance to be ready...')
	        
	        while not instance.status == 'ACTIVE':
	            time.sleep(10)
	            instance = ra.instances.get_by_id(instance.id)
	        #a rendre dynamique via un GET /flavor vcpu
	        node_list = node_list + instance.ip + " slots=" + "6" + "\n" 
	        if "master" in instance_name:
	        	ips_master = instance.ip
	        else:
	        	list_con.append("admin@"+instance.ip)
	        	list_ip.append(instance.ip)
	        print('Instance launched')
	        print('\t-  IP: %s' % instance.ip)
	        print('\t- VNC: %s' % instance.vnc)
	        print('\t- SSH: ssh admin@%s' % instance.ip)
	        #enregistrement des ip dans un array
			
#virgule = ""
#line_host = ""
#for ips in list_ip:
#	print ('install john and mpi on node %s' % ips)
#	line_host = line_host + virgule + "admin@" + ips 
#	virgule = ","
	#execute(install_john, hosts=["admin@" + ips])

#print ('executing on %s' % line_host)
#execute(install_john, hosts=list_con)


#launch john on master . on essaye de retrouver le precedent master
#if not ips_master:
#	ips_master = list_ip[0]
#	list_con.pop(0)
print ('ips master = ' + ips_master + '-')
execute(install_pre,hosts=list_con)
execute(install_pre,hosts=["admin@" + ips_master])
execute(nfs_master, hosts=["admin@" + ips_master])
execute(nfs_node, hosts=list_con)
execute(build_john,hosts=list_con)
execute(build_john,hosts=["admin@" + ips_master])
execute(launch_john, hosts=["admin@" + ips_master])
print ("your result on ssh "+ "admin@" + ips_master + " john-1.8.0-jumbo-1/run/john /var/mpishare/hash --pot=/var/mpishare/shared.pot --show")		



	        #choice = raw_input('\nWould you like to delete the instance? (y/N): ')
	        #if choice.lower() == 'y':
	        #    instance.delete()
	        #    print('Instance deleted')

