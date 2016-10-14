=====================
Moneta setup tutorial
=====================

This tutorial presents the setup of Moneta on one machine (without redundancy), but setup on multiple machines is identical.

The scenario is designed for Ubuntu 16.04 but easily adapts to any distribution.

Moneta requires several things:
- A Zookeeper cluster
- A Moneta daemon on each machine that will execute tasks
- A GUI hosted locally or on a web server

.. contents:: Summary

1. Zookeeper Setup
==================

To be resilient, a Zookeeper cluster must have at least three instances, the typical deployments generally having 3 or 5. In this section, the term *cluster* means the Zookeeper cluster.

The following commands are to be run on each machine constituting the cluster.

In our example, for simplicity, we will use only a single machine, so there will be no redundancy.

1. Install the Zookeeper package::

    herve@tuto-moneta:~$ sudo apt-get install zookeeperd

2. Configure a unique ID for each machine between 1 and 255::

    herve@tuto-moneta:~$ sudo vim /etc/zookeeper/conf/myid

  In this example we will choose ID 1.

3. Edit the configuration to list each server in the cluster::

    herve@tuto-moneta:~$ sudo vim /etc/zookeeper/conf/zoo.cfg

   The format is as follows::

    server.<id>=<host>:2888:3888

   The last two numbers corresponds to the ports used for communication between Zookeeper instances and for leader election.

   In this example, we will then write::

    server.1=127.0.0.1:2888:3888

5. Finally, start Zookeeper::

    herve@tuto-moneta:~$ service zookeeper restart

Now we have a Zookeeper cluster available. It can be reached on any of its instances, on TCP port 2181.

2. Moneta Setup
===============

The following commands are to be run on each machine constituting the Moneta cluster.

In our example, for simplicity, we will use only a single machine, so there will be no redundancy.

1. Moneta requires the following packages:

   - ``gevent``
   - ``kazoo``
   - ``dateutil``
   - ``yaml``
   - ``setuptool``

   Install them through the OS' package manager::

    herve@tuto-moneta:~$ sudo apt-get install python-gevent python-kazoo python-dateutil python-yaml python-setuptools

   We also could have installed them using ``pip``.

2. Fetch the souces of Moneta from Github::

    herve@tuto-moneta:~$ git clone https://github.com/geneanet/moneta.git
    Cloning into 'moneta'...
    remote: Counting objects: 565, done.
    remote: Total 565 (delta 0), reused 0 (delta 0), pack-reused 565
    Receiving objects: 100% (565/565), 99.15 KiB | 0 bytes/s, done.
    Resolving deltas: 100% (395/395), done.
    Checking connectivity... done.

3. Get into the sources directory::

    herve@tuto-moneta:~$ cd moneta

4. Install the program::

    herve@tuto-moneta:~/moneta$ sudo python setup.py install
    running install
    [...]
    Using /usr/lib/python2.7/dist-packages
    Finished processing dependencies for moneta-scheduler==1.0.0b1

5. Install the plugins::

    herve@tuto-moneta:~/moneta$ sudo mkdir -p /usr/share/moneta
    herve@tuto-moneta:~/moneta$ sudo cp -r plugins /usr/share/moneta/plugins

6. Create the path for configuration backup::

    herve@tuto-moneta:~/moneta$ sudo mkdir -p /var/lib/moneta

7. Setup the configuration files::

    herve@tuto-moneta:~/moneta$ sudo mkdir /etc/moneta
    herve@tuto-moneta:~/moneta$ sudo cp misc/logging.conf /etc/moneta/

   Edit ``/etc/moneta/config.yml`` with the following content::

    log:
      config: /etc/moneta/logging.conf

    plugins:
      path: /usr/share/moneta/plugins
      load:
        - mailer
        - audit
        - configbackup
        - executionsummary

    config:
      configbackup:
        path: /car/lib/moneta/config-backup.json
        format: json

    pools:
      - default

    listen: 127.0.0.1:32000

    zookeeper:
      - 127.0.0.1:2181

    nodename: mynode

    leader: true

8. Setup systemd config file and start the daemon ::

    herve@tuto-moneta:~/moneta$ sudo cp misc/systemd.service /etc/systemd/system/moneta.service
    herve@tuto-moneta:~/moneta$ sudo systemctl daemon-reload
    herve@tuto-moneta:~/moneta$ sudo systemctl start moneta

Now we should have a working Moneta daemon, we can check that with the following commands::

    root@tuto-moneta:~/moneta# systemctl status moneta
    ● moneta.service - Moneta Daemon
       Loaded: loaded (/etc/systemd/system/moneta.service; disabled; vendor preset:     enabled)
       Active: active (running) since Fri 2016-08-12 16:33:32 CEST; 9min ago
     Main PID: 16191 (moneta)
        Tasks: 3
       Memory: 48.8M
          CPU: 694ms
       CGroup: /system.slice/moneta.service
               └─16191 /usr/bin/python /usr/local/bin/moneta --config /etc/moneta/config.yml

    Aug 12 16:33:32 tuto-moneta systemd[1]: Started Moneta Daemon.

We can then ask for Moneta state using a REST call::

    herve@tuto-moneta:~/moneta$ curl http://localhost:32000/status
    {"execution_enabled": true, "name": "mynode", "scheduler_running": true, "address": "127.0.0.1:32000", "pools": ["default"], "running_processes": {}, "cluster_joined": true, "leader": true, "contending_for_lead": true, "pools_joined": true}

If the daemon does not start correctly, the logs in ``/var/log/moneta.log`` should help to find the cause.

2.1. Plugins configuration
------------------------------

Plugins ``mailer`` et ``audit`` require une configuration which is not possible through the GUI for now.
This tutorial will not cover it in details but here are the basic configurations for those plugins.

- ``mailer``::

   curl -XPUT 'http://localhost:32000/cluster/config/mailer' -d '{"timezone": "Europe/Paris", "smtpserver": "smtp.myprovider.net", "sender": "moneta@mydomain.net"}'

- ``audit``::

   curl -XPUT 'http://localhost:32000/cluster/config/audit' -d '{"url": "http://elasticsearchserver:9200/", "index": "moneta-${date}", "dateformat": "%Y.%m"}'


3. GUI Setup
============

The GUI is based on AngularJS and Foundation. It can be delivered through a Web server or used locally on a client workstation.

The setup procedur is as follows:

1. Fetch the sources from Github::

    herve@tuto-moneta:~/moneta$ cd ~
    herve@tuto-moneta:~$ git clone https://github.com/geneanet/moneta-web.git
    herve@tuto-moneta:~$ cd moneta-web

2. Install the dependencies::

    herve@tuto-moneta:~$ sudo apt-get install bower
    herve@tuto-moneta:~$ bower install

The GUI is then available by opening  ``index.html`` in a web browser.

Three options are available to specify the address of the Moneta daemon to which the GUI will connect:

- A ``config.json`` file can be put along ``index.html`` with the following content::

   moneta_backend='http://localhost:32000';

- The ``backend`` parameter can be passed in the URL, before the hash::

   index.html?backend=http://localhost:32000#

- If neither method is used, the default configuration is ``127.0.0.1`` port ``32000``.

The GUI being completely client-side, it does not provide a gateway to reach Moneta REST API: if the daemons are on a private network and you want to provide the GUI on a public network, then you should setup a reverse proxy (line nginx or haproxy) to expose the API endpoint on the public network, probably adding some authentification.
