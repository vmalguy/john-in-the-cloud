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

reload(sys)

parser = SafeConfigParser()
parser.read('settings.conf')
env.key_filename = parser.get('ra','ssh_key_filename')
application_key = parser.get('ra', 'application_key')
application_secret = parser.get('ra','application_secret')

list_ip = []
list_con = []
node_list = ""
ips_master = ""
env.connection_attempts = 5
env.parallel = True
instance_list=[]


#fonction fabric pour installer john the ripper
def install_pre():
	if not exists("JohnTheRipper/run/john"):
		with hide('everything'):
			#copy de la clef  pour que tous les host se parle entre eu
			with open(os.path.expanduser(env.key_filename)) as f:
		         key_text = f.read()
		    #bug : on devrait overight pas append
			append('~/.ssh/id_rsa', key_text)
			with open(os.path.expanduser(env.key_filename + '.pub')) as f:
		         key_text = f.read()
		    #bug : on devrait overight pas append
			append('~/.ssh/id_rsa.pub', key_text)
		with hide('output'):
			run ("chmod 0600 ~/.ssh/*")
			env.warn_only = True
			run ("sudo apt-get update")
			env.warn_only = False
			run ("sudo apt-get install libopenmpi-dev openmpi-bin build-essential libssl-dev nfs-common -y")
			env.warn_only = True
			run ("sudo mkdir /var/mpishare 2> /dev/null ")
			run ("sudo umount /var/mpishare 2> /dev/null")
			env.warn_only = False
			append("/etc/ssh/ssh_config","StrictHostKeyChecking no", use_sudo=True)

def launch_john():
	with open(os.path.expanduser(parser.get('ra','hashfile'))) as f:
	        key_text = f.read()
		put("hash", '/var/mpishare/hash')
		cmd = "time mpiexec   -hostfile /var/mpishare/mpi-nodes.txt JohnTheRipper/run/john /var/mpishare/hash --pot=/var/mpishare/shared.pot --wordlist=JohnTheRipper/run/password.lst --rules=All "
		if len(sys.argv) > 1:
			cmd = cmd + sys.argv[1]
		run (cmd)
		run("JohnTheRipper/run/john /var/mpishare/hash --pot=/var/mpishare/shared.pot --show")


def nfs_master():
	with hide('output'):
		run ("sudo apt-get install  nfs-kernel-server portmap git -y") 
		run ("sudo chmod 777 /etc/exports")
		append("/etc/exports", "/var/mpishare	  *(rw,sync)",use_sudo=True)
		#run ("sudo echo \"/var/mpishare	  *(rw,sync)\" > /etc/exports")
		env.warn_only = True
		run ("sudo service rpcbind  restart")
		run ("sudo service nfs-kernel-server restart")
		env.warn_only = False
		#run ("sudo exportfs -a ")
		run ("sudo chmod 777 /var/mpishare/")
		#run ("echo `ip a | grep global | awk '{print $2}' | awk -F\"/\" '{print $1}'` slots=`nproc` > /var/mpishare/mpi-nodes.txt")
		if exists("/var/mpishare/mpi-nodes.txt"):
			run("rm /var/mpishare/mpi-nodes.txt")
		append("/var/mpishare/mpi-nodes.txt", node_list)
		if not exists("/var/mpishare/JohnTheRipper"):
			#run ("wget http://www.openwall.com/john/j/john-1.8.0-jumbo-1.tar.gz -O /var/mpishare/john-1.8.0-jumbo-1.tar.gz")
			run ("git clone https://github.com/magnumripper/JohnTheRipper.git")
			run ("mv JohnTheRipper /var/mpishare/")



def build_john():
	with hide('output'):
		if not exists("JohnTheRipper/run/john"):
			run ("sudo cp -R /var/mpishare/JohnTheRipper/ .")
			run("sudo chmod -R 777 JohnTheRipper")
			run ("cd JohnTheRipper/src/ ; ./configure --enable-mpi")
			run ("cd JohnTheRipper/src/ ; make clean && make -s")
		else:
			print ("john build detected, skipping compilling")



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

def find_in_list(list_name, obj_list):
    for num, i in enumerate(obj_list):
        #print('\t%d) %s against %s' % (num+1, i.name, parser.get('ra', list_name)))
    	if i.name == parser.get('ra', list_name):
    		#print('selecting : %s' % i.name)
    		return i

# Get information about the account
while True:
    try :
        consumer_key = parser.get('ra','consumer_key')
        # Create the Runabove SDK interface
        ra = Runabove(application_key,
               application_secret,
               consumer_key=consumer_key)
        acc = ra.account.get()
        print('\nHi %s,' % acc.first_name)
        break
    except:
        print('\nLogin failed.')
        choice = raw_input('\nWould you like to get a new consumer key? (n/Y): ')
        if choice.lower() == 'n':
            print('Not requesting a Consumer Key, aborting')
            sys.exit(0)
        else:
            print('\nYou need to login on this site %s' % ra.get_login_url())
            raw_input('\nWhen you are logged, press Enter ')
            #print('Your consumer key is: %s' % ra.get_consumer_key())
            parser.set('ra', 'consumer_key', ra.get_consumer_key())
            # Writing our configuration file
            with open('settings.conf', 'wb') as configfile:
                parser.write(configfile)


# Get the list of raning instances
choice = 'n'
instances = ra.instances.list()
print('\nYou have %d instance(s) runing' % len(instances))
for i in instances:
    print('\t- [%s] %s (%s, %s) with %s vcpus' % (i.region.name, i.name, i.ip, i.image.name, i.flavor.vcpus))
    if choice.lower() == 'a':
    	if "master" in i.name and  ips_master == "":
    		print ('MASTER FOUND !')
    		ips_master = i.ip
    	else:
	    	list_ip.append(i.ip)
	    	list_con.append("admin@"+i.ip) 	
    	node_list = node_list + i.ip + " slots=%i \n" % i.flavor.vcpus
    	#print (node_list)

    else:
    	choice = raw_input('\nWould you like to use it in the cluster ? : (a/y/N)')
    	if choice.lower() == 'y' or choice.lower() == 'a':
    		if "master" in i.name and  ips_master == "":
    			ips_master = i.ip
    			print ('MASTER FOUND !')
    		else:
		    	list_ip.append(i.ip)
		    	list_con.append("admin@"+i.ip)
		   	node_list = node_list + i.ip + " slots=%i \n" % i.flavor.vcpus
    		#print (node_list)

region = find_in_list('Region', ra.regions.list())


if ra.ssh_keys.list_by_region(region):
    choice = raw_input('\nHow many instances would you like to create  in %s? : ' % region.name)
    for i in range(0,int(choice)):
    	flavor = find_in_list('Flavor', ra.flavors.list_by_region(region))
        image = find_in_list('Image', ra.images.list_by_region(region))
        print ("requesting a %s with %s OS" % (flavor.name,image.name))
        if  ips_master == "":
        	instance_name = "master"
        	ips_master = 'reserved'
        	print ('MASTER CREATED !')
        else:
        	instance_name = "node" + str(i)
        #ssh_key = ra.ssh_keys.list_by_region(region)[2]
        for j,s in enumerate(ra.ssh_keys.list_by_region(region)):
			if s.name in parser.get('ra','ssh_key_name'):
				ssh_key = ra.ssh_keys.list_by_region(region)[j]
        instance_list.append(ra.instances.create(region, instance_name, flavor, image, ssh_key))
        print('\nInstance resquested') 


    print('Waiting for instance to be ready...')
    for i in range(0,int(choice)):
	    while  instance_list[i].status == 'BUILD':
	        print ("waiting for %s (%s) is still in %s state...." % (instance_list[i].name,instance_list[i].id,instance_list[i].status))
	        time.sleep(2)
	        instance_list[i] = ra.instances.get_by_id(instance_list[i].id)
	       	

	    if instance_list[i].status == 'ACTIVE' and instance_list[i].ip:
		    node_list = node_list + instance_list[i].ip + " slots=%i \n" % instance_list[i].flavor.vcpus
		    #print (node_list)
		    
		    if "master" in instance_list[i].name:
		    	ips_master = instance_list[i].ip
		    else:
	    		list_con.append("admin@"+instance_list[i].ip)
	    		list_ip.append(instance_list[i].ip)
	    	#print('Instance launched')
	    	#print('\t-  IP: %s' % instance_list[i].ip)
	    	#print('\t- SSH: ssh admin@%s' % instance_list[i].ip)
	    else:
		  	print ("OOPS, This one seems broken ... ")
		  	instance_list[i].delete()
		  	print ("deleted. requesting a brand new one insted !")
		  	choice = choice + 1
	        
			

print ('ips master = ' + ips_master + '-')
#if ready and fonctionnal skip to launch !
#le master est souvent creer avant les autres donc il est dispo avant les autres
execute(install_pre,hosts=["admin@" + ips_master])
execute(install_pre,hosts=list_con)
execute(nfs_master, hosts=["admin@" + ips_master])
execute(nfs_node, hosts=list_con)
execute(build_john,hosts=list_con)
execute(build_john,hosts=["admin@" + ips_master])
execute(launch_john, hosts=["admin@" + ips_master])
print ("your result on ssh -i "+ parser.get('ra','ssh_key_filename') + " admin@" + ips_master + " JohnTheRipper/run/john /var/mpishare/hash --pot=/var/mpishare/shared.pot --show")		


choice1 = raw_input('\nWould you like to delete all your cluster instances? (y/N):')
if choice1.lower() == 'y':
	for i in range(0,int(choice)):
		instance_list[i].delete()
    	print('Instance %s deleted', instance_list[i].name)

