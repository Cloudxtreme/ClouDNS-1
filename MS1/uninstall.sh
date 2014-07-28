#!/bin/sh

check () {
    ERROR=$( $1 2>&1 )
    if [ -z "$ERROR" ]; then
        echo "DONE"
    else
        echo "FAILED"
        echo "==> ERROR: $ERROR"
    fi
}


if [ "$(id -u)" != "0" ]; then
    echo "domaininfo: This script must be run as root" 1>&2
    exit 1
fi

while true
do
    echo "Target Linux distributions"
    echo "1 - Debian"
    echo "2 - RHEL"
    read -p "Enter the number of the selected distro [1-2]: " distro_num

    case $distro_num in
        1)
            DISTRO="debian"
            break
            ;;
        2)
            DISTRO="rhel"
            break
            ;;
        *)
            echo "Error: please select between 1 or 2!"
            ;;
    esac
done

echo
echo  "$DISTRO selected."
echo

echo "domaininfo: stop the daemon if it's running ..."
/etc/init.d/domaininfo stop

echo
echo  "domaininfo: uninstall init script"
echo -n "   *  remove from init system ... "
if [ $DISTRO = "debian" ]; then
    check "insserv -r /etc/init.d/domaininfo"
else
    check "chkconfig --del domaininfo"
fi
echo -n "   *  delete the init script ..."
check "rm /etc/init.d/domaininfo"

echo
echo -n "domaininfo: remove daemon ... "
check "rm /usr/local/sbin/domaininfo"
check "rm /usr/local/sbin/MongoConnector.py"


echo
echo -n "domaininfo: remove config file ... "
check "rm /etc/domaininfo.conf"


echo
echo -n "domaininfo: remove logs ... "
check "rm /var/log/domaininfo*"


echo
echo "domaininfo: uninstall script done."
echo
