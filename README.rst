======
Moneta
======

Moneta is a fault-tolerant, distributed task manager.
It is intended to be a replacement for the traditional UNIX cron systems, allowing a scheduled execution of tasks on one or several nodes of a cluster.

It requires a Zookeeper cluster for configuration storage and cluster synchronization.
Task execution reports can be stored in ElasticSearch, in a way that is easily exploitable using Kibana.

.. contents::

Usage
=====

::

 moneta --listen 127.0.0.1:3200 --nodename mynode --zookeeper zookeepernode:2181

The IP address on which Moneta listens is the one announced to other nodes, so it must be reachable by them.

More parameters are available, refer to --help.

Config files can be used instead of command line parameters, see examples in the "misc" directory.

Tutorial
========

A tutorial to setup Moneta and Zookeeper is available at `<doc/setup_tutorial.en.rst>`_.

API
===

Moneta can be configured using a REST API. Any moneta node can be used to configure the whole cluster.
An AngularJS/Foundation app is available to offer a nice GUI (see http://github.com/geneanet/moneta-web).

The API is documented using apiDoc markup in the code (mainly in moneta/server.py).

The rendered documentation can be seen at : http://geneanet.github.io/moneta/apidoc/index.html.

Dependencies
============

- `gevent <https://github.com/gevent/gevent>`_
- `Kazoo <https://github.com/python-zk/kazoo>`_
- `dateutil <https://github.com/dateutil/dateutil>`_
- `PyYAML <https://github.com/yaml/pyyaml>`_
