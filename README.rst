Moneta
======

Moneta is a fault-tolerant, distributed task manager.
It is intended to be a replacement for the traditional UNIX cron systems, allowing a scheduled execution of tasks on one or several nodes of a cluster.

It requires a Zookeeper cluster for configuration storage and cluster synchronization.
Task execution reports can be stored in ElasticSearch, in a way that is easily exploitable using Kibana.

.. contents::

Usage
-----

moneta --listen 127.0.0.1:3200 --nodename mynode --zookeeper zookeepernode:2181

The IP address on which Moneta listens is the one announced to other nodes, so it must be reachable by them.

More parameters are available, refer to --help.

Config files can be used instead of command line parameters, see examples in the "misc" directory.

API
---

Moneta can be configured using a REST API. Any moneta node can be used to configure the whole cluster.
An AngularJS/Foundation app is available to offer a nice GUI (see http://github.com/geneanet/moneta-web).


- **GET /cluster/pools**

  Return the list of pools managed by the cluster, and for each pool the list of its members.
  ::

    {
      "pool1": ["node1", "node2"],
      "pool2: ["node1", "node3"]
    }

- **GET /cluster/status**

  Return a summary of the cluster status.
  ::

    {
      "nodes": {
        "node1": {
          "pools": ["pool1", "pool2"],
          "address": "127.0.0.1:32001"
        },
        "node2": {
          "pools": ["pool1"],
          "address": "127.0.0.1:32002"
        },
        "node3": {
          "pools": ["pool2"],
          "address": "127.0.0.1:32003"
        },
      },
      "leader": "node1"
    }

- **GET /cluster/config/<option>**

  Get the config option <option>

- **PUT /cluster/config/<option>**

  Set the config option <option>

- **<action> /node/<nodename>/<url>**

  Proxy the request "<action> <url>" to the node <nodename>

- **GET /status**

  Return the status of the node, with currently running tasks.
  ::

    {
      "execution_enabled": true,
      "leader": false,
      "name": "node2",
      "scheduler_running": false,
      "address": "127.0.0.1:32002",
      "pools": ["pool1", "pool2"],
      "running_processes": {
        "b26e5cc2ef3f11e4817b0026b951c045": {
          "started": "2015-04-30T13:49:18.351494+00:00",
          "task": "508b4b72e44611e49e76c81f66cd0cca"
        }
      },
      "cluster_joined": true,
      "contending_for_lead": true,
      "pools_joined": true
    }

- **POST /tasks/<task>/(en|dis)able**

  Enable/disable a task.

- **GET /tasks/<task>**

  Returns the configuration of a task.
  ::

    {
      "name": "My task",
      "description": "Task description",
      "tags": ["tasg1", "tag2"],
      "enabled": true,
      "mode": "all",
      "pools": ["web"],
      "schedules": [
        {"minute": ["*/1"]}
      ],
      "command": "/bin/true",
      "workdir": "/tmp/",
      "user": "www-data",
      "group": "www-data",
      "env": {
        "GNT_CONF": "/etc/geneanet/geneaconfig/"
      },
      "mailreport": "output",
      "mailto": ["cron.doc@geneanet.org"],
    }

- **DELETE /tasks/<task>**

  Delete a task.

- **PUT /tasks/<task>**

  Update the configuration of a task (must send the whole config, not a partial update).

- **POST /tasks**

  Add a new task, providing its configuration. Returns the id of the task.
  ::

    {
      "created": true,
      "id": "021b2092ef4111e481a852540064e600"
    }

- **GET /tasks**

  Return a list of all configured tasks, along with their configuration.
  ::

    {
      "021b2092ef4111e481a852540064e600": { ... config ... },
      "508b4b72e44611e49e76c81f66cd0cca": { ... config ... }
    }

- **GET /tags**

  Return the list of all tags.
  ::

    [
      "tag1",
      "tag2"
    ]

- **GET /plugins**

  Return the list of all plugins loaded on the node.
  ::

    [
      "configbackup",
      "mailer",
      "executionsummary"
    ]

Dependencies
------------
- gevent
- Kazoo
- dateutil
- PyYAML
