=================================
Tutoriel d'installation de Moneta
=================================

Ce tutoriel présente l'installation de Moneta sur une seule machine (sans redondance, donc), mais l'installation sur plusieurs machines est identique.

Le scénario est étudié pour Ubuntu 16.04 mais s'adapte facilement à n'importe quelle distribution.

Moneta pour fonctionner nécessite plusieurs choses:

- Un cluster Zookeeper
- Un démon Moneta sur chaque machine devant exécuter des tâches
- Un GUI hébergé en local ou sur un serveur web

.. contents:: Sommaire

1. Mise en place de Zookeeper
=============================

Pour être résilient, un cluster Zookeeper doit comporter au moins 3 instances, les déploiements typiques en ayant généralement 3 ou 5. Dans cette section, le terme *cluster* désignera le cluster Zookeeper.

Les commandes suivantes sont à exécuter sur chaque machine constituant le cluster.

Dans notre exemple, dans un but de simplicité, nous n'utiliserons qu'une seule machine, il n'y aura donc pas de redondance.

1. Installer le package Zookeeper::

    herve@tuto-moneta:~$ sudo apt-get install zookeeperd

2. Configurer un ID numérique unique à chaque machine compris entre 1 et 255::

    herve@tuto-moneta:~$ sudo vim /etc/zookeeper/conf/myid

   Dans cet exemple on choisira l'ID 1.

3. Editer la configuration pour lister chaque serveur du cluster::

    herve@tuto-moneta:~$ sudo vim /etc/zookeeper/conf/zoo.cfg

   Ceux-ci sont au format suivant::

    server.<id>=<host>:2888:3888

   Les deux derniers nombres correspondent aux ports utilisés pour respectivement la communication entre les instances et l'élection du leader.

   Dans cet exemple, on écrira donc::

    server.1=127.0.0.1:2888:3888

5. Enfin, démarrer Zookeeper::

    herve@tuto-moneta:~$ service zookeeper restart

Maintenant, nous avons un cluster Zookeeper disponible . Il peut être joint sur n'importe quelle machine de celui-ci, sur le port TCP 2181.

2. Mise en place de Moneta
==========================

Les commandes suivantes sont à exécuter sur chaque machine constituant le cluster Moneta.

Dans notre exemple, dans un but de simplicité, nous n'utiliserons qu'une seule machine, il n'y aura donc pas de redondance.

1. Moneta nécessite les packages suivants:

   - ``gevent``
   - ``kazoo``
   - ``dateutil``
   - ``yaml``
   - ``setuptool``

   On les installe via le gestionnaire de packages de l'OS::

    herve@tuto-moneta:~$ sudo apt-get install python-gevent python-kazoo python-dateutil python-yaml python-setuptools

   On pourrait aussi les installer via ``pip``.

2. Récupération de Moneta depuis Github::

    herve@tuto-moneta:~$ git clone https://github.com/geneanet/moneta.git
    Cloning into 'moneta'...
    remote: Counting objects: 565, done.
    remote: Total 565 (delta 0), reused 0 (delta 0), pack-reused 565
    Receiving objects: 100% (565/565), 99.15 KiB | 0 bytes/s, done.
    Resolving deltas: 100% (395/395), done.
    Checking connectivity... done.

3. On se place dans le dossier source::

    herve@tuto-moneta:~$ cd moneta

4. Installation du programme::

    herve@tuto-moneta:~/moneta$ sudo python setup.py install
    running install
    [...]
    Using /usr/lib/python2.7/dist-packages
    Finished processing dependencies for moneta-scheduler==1.0.0b1

5. Installation des plugins::

    herve@tuto-moneta:~/moneta$ sudo mkdir -p /usr/share/moneta
    herve@tuto-moneta:~/moneta$ sudo cp -r plugins /usr/share/moneta/plugins

6. Création du chemin pour les backups de configuration::

    herve@tuto-moneta:~/moneta$ sudo mkdir -p /var/lib/moneta

7. Mise en place de la configuration::

    herve@tuto-moneta:~/moneta$ sudo mkdir /etc/moneta
    herve@tuto-moneta:~/moneta$ sudo cp misc/logging.conf /etc/moneta/

   On édite ensuite ``/etc/moneta/config.yml`` ainsi::

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

8. Mise en place du service systemd et démarrage du démon ::

    herve@tuto-moneta:~/moneta$ sudo cp misc/systemd.service /etc/systemd/system/moneta.service
    herve@tuto-moneta:~/moneta$ sudo systemctl daemon-reload
    herve@tuto-moneta:~/moneta$ sudo systemctl start moneta

Maintenant, nous avons un démon Moneta fonctionnel, on peut le vérifier par la commandes suivantes::

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

On peut donc interroger le démon via une requête REST pour obtenir son état::

    herve@tuto-moneta:~/moneta$ curl http://localhost:32000/status
    {"execution_enabled": true, "name": "mynode", "scheduler_running": true, "address": "127.0.0.1:32000", "pools": ["default"], "running_processes": {}, "cluster_joined": true, "leader": true, "contending_for_lead": true, "pools_joined": true}

Si le démon ne démarre pas correctement, les logs dans ``/var/log/moneta.log`` permettront de déterminer l'origine du problème.

2.1. Configuration des plugins
------------------------------

Les plugins ``mailer`` et ``audit`` nécessitent une configuration qui n'est à l'heure actuelle pas possible via l'interface graphique.
Ce tutorial ne les présentera pas en détail, mais voici les configurations de base pour ces plugins.

- Plugin ``mailer``::

   curl -XPUT 'http://localhost:32000/cluster/config/mailer' -d '{"timezone": "Europe/Paris", "smtpserver": "smtp.myprovider.net", "sender": "moneta@mydomain.net"}'

- Plugin ``audit``::

   curl -XPUT 'http://localhost:32000/cluster/config/audit' -d '{"url": "http://elasticsearchserver:9200/", "index": "moneta-${date}", "dateformat": "%Y.%m"}'

3. Mise en place du GUI
=======================

Le GUI est basé sur AngularJS et Foundation. Il peut fonctionner en étant distribué par un serveur Web ou bien directement sur un poste utilisateur.

La procédure d'installation est la suivante:

1. Récupération du dépôt Git::

    herve@tuto-moneta:~/moneta$ cd ~
    herve@tuto-moneta:~$ git clone https://github.com/geneanet/moneta-web.git
    herve@tuto-moneta:~$ cd moneta-web

2. Installation de dépendances::

    herve@tuto-moneta:~/moneta-web$ sudo apt-get install bower
    herve@tuto-moneta:~/moneta-web$ bower install

Le GUI est alors accessible en ouvrant ``index.html`` avec un navigateur Web.

Trois possibilités existent pour spécifier au GUI l'adresse du démon Moneta sur lequel se connecter:

- Un fichier ``config.json`` peut être placé auprès du ``index.html`` avec le format suivant::

   moneta_backend='http://localhost:32000';

- Le paramètre ``backend`` peut être passé dans l'URL, avant le hash::

   index.html?backend=http://localhost:32000#

- Si ni l'un ni l'autre n'est disponible, la configuration par défaut est ``127.0.0.1`` port ``32000``.

Le GUI étant entièrement en JS côté client, il ne fournit pas de passerelle pour accéder à l'API REST de Moneta: si les démons Moneta sont sur un réseau privé et qu'on souhaite proposer un GUI sur un réseau public, il conviendra de mettre en place un reverse proxy (par exemple nginx ou haproxy) pour ouvrir l'API sur le réseau public, avec au besoin une authentification.
