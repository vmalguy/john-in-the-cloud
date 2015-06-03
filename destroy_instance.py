#!/usr/bin/env python

from __future__ import unicode_literals, print_function
from os import path
import sys
import time

from runabove import Runabove
from runabove.exception import APIError

from ConfigParser import SafeConfigParser

parser = SafeConfigParser()
parser.read('settings.conf')
#env.key_filename = parser.get('ra','ssh_key_filename')
application_key = parser.get('ra', 'application_key')
application_secret = parser.get('ra','application_secret')





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
choice = raw_input('\nWould you like to delete all your instances? (y/N): ')
if choice.lower() == 'y':
	for i in instances:
	    print('\t- [%s] %s (%s, %s)' % (i.region.name, i.name, i.ip, i.image.name))
	    instance = ra.instances.get_by_id(i.id)
	    instance.delete()
	    print('Instance deleted')