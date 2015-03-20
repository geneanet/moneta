Moneta
======

Moneta is a fault-tolerant, distributed task manager.
It is intended to be a replacement for the traditional UNIX cron systems, allowing a scheduled execution of tasks on one or several nodes of a cluster.

It requires a Zookeeper cluster for configuration storage and cluster synchronization.
Task execution reports can be stored in ElasticSearch, in a way that is easily exploitable using Kibana.

Usage
-----

moneta --listen 127.0.0.1:3200 --nodename mynode --zookeeper zookeepernode:2181

The IP address on which Moneta listens is the one announced to other nodes, so it must be reachable by them.

API
---

Moneta can be configured using a REST API. Any moneta node can be used to configure the whole cluster.
An AngularJS/Foundation app is available to offer a nice GUI.

Dependencies:
-------------
- gevent
- kazoo
- pytz