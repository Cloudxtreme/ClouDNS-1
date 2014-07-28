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

echo  "domaininfo: install pkg requirements ..."
if [ $DISTRO = "debian" ]; then
    apt-get install python-pip python-dev libxml2 libxml2-dev libxslt1.1 libxslt1-dev
else
    yum install gcc python-devel libxml2 libxml2-devel libxslt libxslt-devel bind-utils
fi

echo
echo  "domaininfo: install python pkg requirements ..."
pip install -r requirements.txt

echo
echo  -n "domaininfo: copy config file ... "
check "cp domaininfo.conf /etc/"


echo
echo  "domaininfo: copy daemon"
echo -n "   *  add permission ... "
check "chmod a+x domaininfo.py"
check "chmod a+x MongoConnector.py"
echo -n "   *  copy files to its destination folder ... "
check "cp domaininfo.py /usr/local/sbin/domaininfo"
check "cp MongoConnector.py /usr/local/sbin/MongoConnector.py"

echo
echo  "domaininfo: install init script"
echo -n "   *  move it to destination folder ... "
if [ $DISTRO = "debian" ]; then
    check "cp domaininfo.init.debian /etc/init.d/domaininfo"
else
    check "cp domaininfo.init.rhel /etc/init.d/domaininfo"
fi
echo -n "   *  add permission ... "
check "chmod a+x /etc/init.d/domaininfo"
echo -n "   *  add it to init system ... "
if [ $DISTRO = "debian" ]; then
    check "insserv /etc/init.d/domaininfo"
else
    check "chkconfig --add domaininfo"
fi

echo
echo  "domaininfo: install done."
echo "domaininfo: it needs to be started manually by typing"
echo
echo  "      (sudo) /etc/init.d/domaininfo start"
echo
echo "domaininfo: or it will be started automatically after the next startup."
echo
