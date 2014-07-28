#!/usr/bin/env python2

from __future__ import print_function
import os
try:
    from MongoConnector import CMongoConnector
except ImportError:
    import imp
    imp.load_source('MongoConnector', os.getcwd())
    from MongoConnector import CMongoConnector
import ConfigParser
import atexit
import logging
import re
import signal
import sys
import time
import awis
import pyinotify
import xmltodict

# Globals Section
# Bind9 Log File Pointer
fp = None
# Boolean to verify if DB is up
db_client = None


def daemonize(pidfile, stdin='/dev/null',
                       stdout='/dev/null',
                       stderr='/dev/null'):

    if os.path.exists(pidfile):
        raise RuntimeError('Already running')

    # First fork (detaches from parent)
    try:
        if os.fork() > 0:
            raise SystemExit(0)  # Parent exit
    except OSError as err:
        raise RuntimeError('fork #1 failed.')

    os.chdir('/')
    os.umask(0)
    os.setsid()

    # Second fork (relinquish session leadership)
    try:
        if os.fork() > 0:
            raise SystemExit(0)
    except OSError as err:
        raise RuntimeError('fork #2 failed.')

    sys.stdout.flush()
    sys.stderr.flush()

    with open(stdin, 'rb', 0) as f:
        os.dup2(f.fileno(), sys.stdin.fileno())
    with open(stdout, 'ab', 0) as f:
        os.dup2(f.fileno(), sys.stdout.fileno())
    with open(stderr, 'ab', 0) as f:
        os.dup2(f.fileno(), sys.stderr.fileno())

    # Write the PID file
    with open(pidfile, 'w') as f:
        print(os.getpid(), file=f)

    # Arrange to have the PID file removed on exit/signal
    def remove_pid(pidfile):
        if os.path.exists(pidfile):
            os.remove(pidfile)
    atexit.register(remove_pid, pidfile)

    # Signal handler for termination (required)
    def sigterm_handler(signo, frame):
        raise SystemExit(1)

    signal.signal(signal.SIGTERM, sigterm_handler)


def main():
    sys.stdout.write('%s Daemon started with pid %d\n' % (time.ctime(),
                                                          os.getpid()))
    # READ Config file
    logging.debug('Starts Reading Config File...')
    config = ConfigParser.ConfigParser()
    config.read('/etc/domaininfo.conf')
    if not config.sections():
        print('%s ERROR: no config file found, exiting.' % time.ctime(),
              file=sys.stderr)
        raise SystemExit(1)

    # Read General Config data
    client_name = config.get('general', 'client_name')

    # Setup logging files and format
    bind9_log_file = config.get('daemon', 'bind_log_path')

    debug_enabled = config.getboolean('daemon', 'debug')
    log_format = '%(asctime)s: %(levelname)s - %(message)s'
    if debug_enabled:
        logging.basicConfig(level=logging.DEBUG, format=log_format)
    else:
        logging.basicConfig(level=logging.ERROR, format=log_format)

    # Setup DB Connection
    global db_client
    db_ip = config.get('db', 'mongo_ip')
    db_port = config.get('db', 'mongo_port')
    db_use_auth = config.get('db', 'use_auth')
    # Check if DB Connection auth is requiered
    if db_use_auth is True:
        db_user = config.get('db', 'mongo_user')
        db_pass = config.get('db', 'mongo_pass')
    else:
        db_user = None
        db_pass = None

    logging.debug('Following DB Details: %s@%s, Auth:%s, %s@%s' % (db_ip, db_port, db_use_auth, db_user, db_pass))

    db_client = CMongoConnector()
    conn_status = db_client.init_connection(db_ip, int(db_port), db_user, db_pass)
    if conn_status is False:
        logging.error("DBConnection:: An error Occurred during DB Connection Initiation...")
        raise SystemExit(1)

    # Check if DB connection was successful
    if db_client.is_alive() is False:
        logging.error("DBConnection:: An error Occurred during DB Connection...")
        raise SystemExit(1)

    # Start Reading BIND9 log file
    global fp
    fp = open(bind9_log_file, 'r')
    if not fp:
        logging.error('BIND9 LogFile:: No log file found, exiting.')
        raise SystemExit(1)
    fp.seek(0, 2)

    wm = pyinotify.WatchManager()
    dirmask = pyinotify.IN_MODIFY | pyinotify.IN_DELETE | pyinotify.IN_MOVE_SELF | pyinotify.IN_CREATE

    # Process Log line
    def process(line):
        REGEXP = r'(\d{2}-[A-Za-z]{3}-\d{4}\s\d{2}:\d{2}:\d{2}\.\d+)\D+(\d+\.\d+\.\d+\.\d+)#\d+.*\s(([a-zA-Z0-9-]+\.)+[a-zA-Z]+).*'
        result = re.match(REGEXP, line)
        if result:
            timestamp, source_ip, domain, _ = result.groups()
        else:
            logging.error('BIND9 LogFile:: Failed to analyze line: %s with current RegExp.' % line)
            return

        # Build request JSON...
        json_dns_query = {'Client': client_name, 'Domain': domain, 'Source IP': source_ip, 'Timestamp': timestamp}
        logging.debug(json_dns_query)

        ######## Add Threads Support while insert data to DB #################
        #t = Thread(target=handle_query, args=json_dns_query)
        #t.start()
        #logging.debug('Thread started with domain: %s.' % domain)

        ######## Add DB Connection Monitoring to prevent data loss #################
        # Check if DB connection was created...
        #if db_client.is_connected() is True:
        query_id = db_client.insert_dns_query(json_dns_query)
        logging.debug("BIND9 LogFile:: New Query ID: %s" % query_id)
        #else:
        #    json.dumps(json_dns_query, sort_keys=True,
        #               indent=4, separators=(',', ': '))

    # Event handlers
    class PTmp(pyinotify.ProcessEvent):
        #File was modified
        def process_IN_MODIFY(self, event):
            if bind9_log_file not in os.path.join(event.path, event.name):
                return
            else:
                global fp
                process(fp.readline().rstrip())

        #File was moved
        def process_IN_MOVE_SELF(self, event):
            pass

        #Subfile was created
        def process_IN_CREATE(self, event):
            if bind9_log_file in os.path.join(event.path, event.name):
                global fp
                if fp:
                    fp.close()
                fp = open(bind9_log_file, 'r')
                for line in fp.readlines():
                    process(line.rstrip())
                # Jump to the end, wait for more IN_MODIFY events
                fp.seek(0, 2)
            return

    notifier = pyinotify.Notifier(wm, PTmp())
    # Watch out for logrotate
    index = bind9_log_file.rfind('/')
    wm.add_watch(bind9_log_file[:index], dirmask)

    while True:
        notifier.process_events()
        if notifier.check_events():
            notifier.read_events()

    notifier.stop()
    fp.close()



if __name__ == '__main__':
    PIDFILE = '/var/run/domaininfo.pid'

    if len(sys.argv) != 2:
        print('Usage: %s [start|stop]' % sys.argv[0], file=sys.stderr)
        raise SystemExit(1)

    if sys.argv[1] == 'start':
        try:
            daemonize(PIDFILE,
                      stdout='/var/log/domaininfo.log',
                      stderr='/var/log/domaininfo.err')
        except RuntimeError as e:
            print(e, file=sys.stderr)
            raise SystemExit(1)

        main()

    elif sys.argv[1] == 'stop':
        if os.path.exists(PIDFILE):
            with open(PIDFILE) as f:
                os.kill(int(f.read()), signal.SIGTERM)
        else:
            print('Not running', file=sys.stderr)
            raise SystemExit(1)

    else:
        print('Unknown command %r' % sys.argv[1], file=sys.stderr)
        raise SystemExit(1)
