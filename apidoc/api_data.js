define({ "api": [
  {
    "type": "get",
    "url": "/cluster/config/:key",
    "title": "Get cluster parameter",
    "name": "GetClusterConfig",
    "group": "Cluster",
    "version": "1.0.0",
    "parameter": {
      "fields": {
        "Parameter": [
          {
            "group": "Parameter",
            "type": "string",
            "optional": false,
            "field": ":key",
            "description": "<p>Name of the parameter to get</p>"
          }
        ]
      }
    },
    "filename": "./moneta/server.py",
    "groupTitle": "Cluster"
  },
  {
    "type": "get",
    "url": "/cluster/pools",
    "title": "Get cluster pools",
    "name": "GetClusterPools",
    "group": "Cluster",
    "version": "1.0.0",
    "description": "<p>List pools and nodes registered into each.</p>",
    "success": {
      "fields": {
        "Success 200": [
          {
            "group": "Success 200",
            "type": "String[]",
            "optional": false,
            "field": "pool",
            "description": "<p>List of nodes registered into the pool.</p>"
          }
        ]
      },
      "examples": [
        {
          "title": "Example response:",
          "content": "{\n  \"pool1\": [\"node1\", \"node2\"],\n  \"pool2: [\"node1\", \"node3\"]\n}",
          "type": "json"
        }
      ]
    },
    "filename": "./moneta/server.py",
    "groupTitle": "Cluster"
  },
  {
    "type": "get",
    "url": "/cluster/status",
    "title": "Get cluster status",
    "name": "GetClusterStatus",
    "group": "Cluster",
    "version": "1.0.0",
    "success": {
      "fields": {
        "Success 200": [
          {
            "group": "Success 200",
            "type": "Object",
            "optional": false,
            "field": "nodes",
            "description": "<p>Nodes in the cluster.</p>"
          },
          {
            "group": "Success 200",
            "type": "Object",
            "optional": false,
            "field": "nodes.node",
            "description": "<p>Node.</p>"
          },
          {
            "group": "Success 200",
            "type": "String[]",
            "optional": false,
            "field": "nodes.node.pools",
            "description": "<p>Pools in which the node is registered.</p>"
          },
          {
            "group": "Success 200",
            "type": "String",
            "optional": false,
            "field": "nodes.node.address",
            "description": "<p>IP address of the node.</p>"
          },
          {
            "group": "Success 200",
            "type": "String",
            "optional": false,
            "field": "leader",
            "description": "<p>Leader node.</p>"
          }
        ]
      },
      "examples": [
        {
          "title": "Example response:",
          "content": "{\n  \"nodes\": {\n    \"node1\": {\n      \"pools\": [\"pool1\", \"pool2\"],\n      \"address\": \"127.0.0.1:32001\"\n    },\n    \"node2\": {\n      \"pools\": [\"pool1\"],\n      \"address\": \"127.0.0.1:32002\"\n    },\n    \"node3\": {\n      \"pools\": [\"pool2\"],\n      \"address\": \"127.0.0.1:32003\"\n    },\n  },\n  \"leader\": \"node1\"\n}",
          "type": "json"
        }
      ]
    },
    "filename": "./moneta/server.py",
    "groupTitle": "Cluster"
  },
  {
    "type": "put",
    "url": "/cluster/config/:key",
    "title": "Set cluster parameter",
    "name": "SetClusterConfig",
    "group": "Cluster",
    "version": "1.0.0",
    "parameter": {
      "fields": {
        "Parameter": [
          {
            "group": "Parameter",
            "type": "string",
            "optional": false,
            "field": ":key",
            "description": "<p>Name of the parameter to set</p>"
          }
        ]
      }
    },
    "filename": "./moneta/server.py",
    "groupTitle": "Cluster"
  },
  {
    "type": "get",
    "url": "/tags",
    "title": "List tags",
    "name": "GetTags",
    "group": "Misc",
    "version": "1.0.0",
    "description": "<p>List currenty used tags</p>",
    "success": {
      "examples": [
        {
          "title": "Example response:",
          "content": "[\n  \"tag1\",\n  \"tag2\"\n]",
          "type": "json"
        }
      ]
    },
    "filename": "./moneta/server.py",
    "groupTitle": "Misc"
  },
  {
    "type": "ANY",
    "url": "/node/:node/:uri",
    "title": "Proxy a request",
    "name": "ProxyToNode",
    "group": "Misc",
    "version": "1.0.0",
    "description": "<p>Proxy the request :uri to the node :node, and forward the response.</p>",
    "parameter": {
      "fields": {
        "Parameter": [
          {
            "group": "Parameter",
            "type": "string",
            "optional": false,
            "field": ":node",
            "description": "<p>Node name.</p>"
          },
          {
            "group": "Parameter",
            "type": "string",
            "optional": false,
            "field": ":uri",
            "description": "<p>URI.</p>"
          }
        ]
      }
    },
    "filename": "./moneta/server.py",
    "groupTitle": "Misc"
  },
  {
    "type": "get",
    "url": "/status",
    "title": "Get node status",
    "name": "GetNodeStatus",
    "group": "Node",
    "version": "1.1.0",
    "success": {
      "fields": {
        "Success 200": [
          {
            "group": "Success 200",
            "type": "Boolean",
            "optional": false,
            "field": "execution_enabled",
            "description": "<p>Task execution is enabled on the node.</p>"
          },
          {
            "group": "Success 200",
            "type": "Boolean",
            "optional": false,
            "field": "leader",
            "description": "<p>Node is the leader.</p>"
          },
          {
            "group": "Success 200",
            "type": "String",
            "optional": false,
            "field": "name",
            "description": "<p>Node name.</p>"
          },
          {
            "group": "Success 200",
            "type": "Boolean",
            "optional": false,
            "field": "scheduler_running",
            "description": "<p>The scheduler is running on the node.</p>"
          },
          {
            "group": "Success 200",
            "type": "String",
            "optional": false,
            "field": "address",
            "description": "<p>Node IP address.</p>"
          },
          {
            "group": "Success 200",
            "type": "String[]",
            "optional": false,
            "field": "pools",
            "description": "<p>Pools in which the node is registered.</p>"
          },
          {
            "group": "Success 200",
            "type": "Object",
            "optional": false,
            "field": "running_processes",
            "description": "<p>Processes running on the host.</p>"
          },
          {
            "group": "Success 200",
            "type": "Object",
            "optional": false,
            "field": "running_processes.process",
            "description": "<p>Process.</p>"
          },
          {
            "group": "Success 200",
            "type": "String",
            "optional": false,
            "field": "running_processes.process.start_time",
            "description": "<p>Time the process started, ISO 8601 formatted.</p>"
          },
          {
            "group": "Success 200",
            "type": "String",
            "optional": false,
            "field": "running_processes.process.task",
            "description": "<p>ID of the task.</p>"
          },
          {
            "group": "Success 200",
            "type": "Boolean",
            "optional": false,
            "field": "cluster_joined",
            "description": "<p>Node has joined the cluster.</p>"
          },
          {
            "group": "Success 200",
            "type": "Boolean",
            "optional": false,
            "field": "contending_for_lead",
            "description": "<p>Node is contending for lead.</p>"
          },
          {
            "group": "Success 200",
            "type": "Boolean",
            "optional": false,
            "field": "pools_joined",
            "description": "<p>Node has joined its pools.</p>"
          }
        ]
      },
      "examples": [
        {
          "title": "Example response:",
          "content": "{\n  \"execution_enabled\": true,\n  \"leader\": false,\n  \"name\": \"node2\",\n  \"scheduler_running\": false,\n  \"address\": \"127.0.0.1:32002\",\n  \"pools\": [\"pool1\", \"pool2\"],\n  \"running_processes\": {\n    \"b26e5cc2ef3f11e4817b0026b951c045\": {\n      \"start_time\": \"2015-04-30T13:49:18.351494+00:00\",\n      \"task\": \"508b4b72e44611e49e76c81f66cd0cca\"\n    }\n  },\n  \"cluster_joined\": true,\n  \"contending_for_lead\": true,\n  \"pools_joined\": true\n}",
          "type": "json"
        }
      ]
    },
    "filename": "./moneta/server.py",
    "groupTitle": "Node"
  },
  {
    "type": "get",
    "url": "/plugins",
    "title": "List plugins",
    "name": "GetPlugins",
    "group": "Node",
    "version": "1.0.0",
    "description": "<p>List plugins loaded on the node.</p>",
    "success": {
      "examples": [
        {
          "title": "Example response:",
          "content": "[\n  \"configbackup\",\n  \"mailer\",\n  \"executionsummary\"\n]",
          "type": "json"
        }
      ]
    },
    "filename": "./moneta/server.py",
    "groupTitle": "Node"
  },
  {
    "type": "kill",
    "url": "/processes/:id",
    "title": "Kill a running process",
    "name": "KillProcesses",
    "group": "Processes",
    "version": "1.1.0",
    "parameter": {
      "fields": {
        "Parameter": [
          {
            "group": "Parameter",
            "type": "String",
            "optional": false,
            "field": ":id",
            "description": "<p>Process ID.</p>"
          }
        ]
      }
    },
    "success": {
      "examples": [
        {
          "title": "Example response:",
          "content": "{\n  \"killed\": true,\n  \"id\": \"021b2092ef4111e481a852540064e600\"\n}",
          "type": "json"
        }
      ]
    },
    "filename": "./moneta/server.py",
    "groupTitle": "Processes"
  },
  {
    "type": "delete",
    "url": "/task/:id",
    "title": "Delete a task",
    "name": "DeleteTask",
    "group": "Tasks",
    "version": "1.0.0",
    "description": "<p>Delete a task.</p>",
    "parameter": {
      "fields": {
        "Parameter": [
          {
            "group": "Parameter",
            "type": "String",
            "optional": false,
            "field": ":id",
            "description": "<p>Task ID.</p>"
          }
        ]
      }
    },
    "success": {
      "fields": {
        "Success 200": [
          {
            "group": "Success 200",
            "type": "Boolean",
            "optional": false,
            "field": "deleted",
            "description": "<p>The task has been deleted.</p>"
          },
          {
            "group": "Success 200",
            "type": "String",
            "optional": false,
            "field": "id",
            "description": "<p>ID of the task.</p>"
          }
        ]
      },
      "examples": [
        {
          "title": "Example response:",
          "content": "{\n  \"deleted\": true,\n  \"id\": \"021b2092ef4111e481a852540064e600\"\n}",
          "type": "json"
        }
      ]
    },
    "filename": "./moneta/server.py",
    "groupTitle": "Tasks"
  },
  {
    "type": "delete",
    "url": "/tasks",
    "title": "Delete all tasks",
    "name": "DeleteTasks",
    "group": "Tasks",
    "version": "1.0.0",
    "description": "<p>Delete all tasks. Use with caution.</p>",
    "success": {
      "fields": {
        "Success 200": [
          {
            "group": "Success 200",
            "type": "Boolean",
            "optional": false,
            "field": "deleted",
            "description": "<p>The tasks have been deleted.</p>"
          }
        ]
      },
      "examples": [
        {
          "title": "Example response:",
          "content": "{\n  \"deleted\": true\n}",
          "type": "json"
        }
      ]
    },
    "filename": "./moneta/server.py",
    "groupTitle": "Tasks"
  },
  {
    "type": "post",
    "url": "/task/:id/disable",
    "title": "Disable a task",
    "name": "DisableTask",
    "group": "Tasks",
    "version": "1.0.0",
    "parameter": {
      "fields": {
        "Parameter": [
          {
            "group": "Parameter",
            "type": "String",
            "optional": false,
            "field": ":id",
            "description": "<p>Task ID.</p>"
          }
        ]
      }
    },
    "success": {
      "fields": {
        "Success 200": [
          {
            "group": "Success 200",
            "type": "Boolean",
            "optional": false,
            "field": "updated",
            "description": "<p>The task has been updated.</p>"
          },
          {
            "group": "Success 200",
            "type": "String",
            "optional": false,
            "field": "id",
            "description": "<p>ID of the task.</p>"
          }
        ]
      },
      "examples": [
        {
          "title": "Example response:",
          "content": "{\n  \"updated\": true,\n  \"id\": \"021b2092ef4111e481a852540064e600\"\n}",
          "type": "json"
        }
      ]
    },
    "filename": "./moneta/server.py",
    "groupTitle": "Tasks"
  },
  {
    "type": "post",
    "url": "/task/:id/enable",
    "title": "Enable a task",
    "name": "EnableTask",
    "group": "Tasks",
    "version": "1.0.0",
    "parameter": {
      "fields": {
        "Parameter": [
          {
            "group": "Parameter",
            "type": "String",
            "optional": false,
            "field": ":id",
            "description": "<p>Task ID.</p>"
          }
        ]
      }
    },
    "success": {
      "fields": {
        "Success 200": [
          {
            "group": "Success 200",
            "type": "Boolean",
            "optional": false,
            "field": "updated",
            "description": "<p>The task has been updated.</p>"
          },
          {
            "group": "Success 200",
            "type": "String",
            "optional": false,
            "field": "id",
            "description": "<p>ID of the task.</p>"
          }
        ]
      },
      "examples": [
        {
          "title": "Example response:",
          "content": "{\n  \"updated\": true,\n  \"id\": \"021b2092ef4111e481a852540064e600\"\n}",
          "type": "json"
        }
      ]
    },
    "filename": "./moneta/server.py",
    "groupTitle": "Tasks"
  },
  {
    "type": "execute",
    "url": "/task/:id",
    "title": "Execute a task",
    "name": "ExecuteTask",
    "group": "Tasks",
    "version": "1.1.0",
    "description": "<p>Execute a task.</p>",
    "parameter": {
      "fields": {
        "Parameter": [
          {
            "group": "Parameter",
            "type": "String",
            "optional": false,
            "field": ":id",
            "description": "<p>Task ID.</p>"
          },
          {
            "group": "Parameter",
            "type": "String",
            "optional": false,
            "field": ":target",
            "description": "<p>Target for task execution (&quot;local&quot; to execute on the local node, otherwise execute on the nodes on which the task is configured to run).</p>"
          },
          {
            "group": "Parameter",
            "type": "Boolean",
            "optional": false,
            "field": ":force",
            "description": "<p>Force the execution even if the concurrency limit is reached.</p>"
          }
        ]
      }
    },
    "success": {
      "fields": {
        "Success 200": [
          {
            "group": "Success 200",
            "type": "Boolean",
            "optional": false,
            "field": "Executed",
            "description": "<p>The task has been executed.</p>"
          },
          {
            "group": "Success 200",
            "type": "String",
            "optional": false,
            "field": "id",
            "description": "<p>ID of the task.</p>"
          }
        ]
      },
      "examples": [
        {
          "title": "Example response:",
          "content": "{\n  \"deleted\": true,\n  \"id\": \"021b2092ef4111e481a852540064e600\"\n}",
          "type": "json"
        }
      ]
    },
    "filename": "./moneta/server.py",
    "groupTitle": "Tasks"
  },
  {
    "type": "get",
    "url": "/tasks/:id",
    "title": "Get a task",
    "name": "GetTask",
    "group": "Tasks",
    "version": "1.0.0",
    "description": "<p>Returns the configuration of a task.</p>",
    "parameter": {
      "fields": {
        "Parameter": [
          {
            "group": "Parameter",
            "type": "String",
            "optional": false,
            "field": ":id",
            "description": "<p>Task ID.</p>"
          }
        ]
      }
    },
    "success": {
      "fields": {
        "Success 200": [
          {
            "group": "Success 200",
            "type": "String",
            "optional": false,
            "field": "name",
            "description": "<p>Name.</p>"
          },
          {
            "group": "Success 200",
            "type": "String",
            "optional": false,
            "field": "description",
            "description": "<p>Description.</p>"
          },
          {
            "group": "Success 200",
            "type": "String[]",
            "optional": false,
            "field": "tags",
            "description": "<p>Tags.</p>"
          },
          {
            "group": "Success 200",
            "type": "Boolean",
            "optional": false,
            "field": "enabled",
            "description": "<p>Task is enabled.</p>"
          },
          {
            "group": "Success 200",
            "type": "String",
            "optional": false,
            "field": "mode",
            "description": "<p>Task mode (&quot;any&quot; or &quot;all&quot;).</p>"
          },
          {
            "group": "Success 200",
            "type": "String[]",
            "optional": false,
            "field": "pools",
            "description": "<p>Pools on which the task should run.</p>"
          },
          {
            "group": "Success 200",
            "type": "Object[]",
            "optional": false,
            "field": "schedules",
            "description": "<p>Schedules at which the task should run.</p>"
          },
          {
            "group": "Success 200",
            "type": "String",
            "optional": false,
            "field": "command",
            "description": "<p>Command to run.</p>"
          },
          {
            "group": "Success 200",
            "type": "String",
            "optional": false,
            "field": "workdir",
            "description": "<p>Working directory.</p>"
          },
          {
            "group": "Success 200",
            "type": "String",
            "optional": false,
            "field": "user",
            "description": "<p>User which the task will be run.</p>"
          },
          {
            "group": "Success 200",
            "type": "String",
            "optional": false,
            "field": "group",
            "description": "<p>Group which the task will be run.</p>"
          },
          {
            "group": "Success 200",
            "type": "Object",
            "optional": false,
            "field": "env",
            "description": "<p>Environment variables to set.</p>"
          },
          {
            "group": "Success 200",
            "type": "String",
            "optional": false,
            "field": "mailreport",
            "description": "<p>If the mailer plugin is enabled, condition to send a report (&quot;error&quot;, &quot;stdout&quot;, &quot;stderr&quot;, &quot;output&quot;, &quot;always&quot;).</p>"
          },
          {
            "group": "Success 200",
            "type": "String[]",
            "optional": false,
            "field": "mailto",
            "description": "<p>If the mailer plugin is enabled, email addresses to send the reports to.</p>"
          }
        ]
      },
      "examples": [
        {
          "title": "Example response:",
          "content": "{\n  \"name\": \"My task\",\n  \"description\": \"Task description\",\n  \"tags\": [\"tasg1\", \"tag2\"],\n  \"enabled\": true,\n  \"mode\": \"all\",\n  \"pools\": [\"web\"],\n  \"schedules\": [\n    {\"minute\": [\"*/1\"]}\n  ],\n  \"command\": \"/bin/true\",\n  \"workdir\": \"/tmp/\",\n  \"user\": \"www-data\",\n  \"group\": \"www-data\",\n  \"env\": {\n    \"MYENVVAR\": \"myvalue\"\n  },\n  \"mailreport\": \"output\",\n  \"mailto\": [\"user@domain.org\"]\n}",
          "type": "json"
        }
      ]
    },
    "filename": "./moneta/server.py",
    "groupTitle": "Tasks"
  },
  {
    "type": "get",
    "url": "/tasks",
    "title": "List tasks",
    "name": "GetTasks",
    "group": "Tasks",
    "version": "1.0.0",
    "description": "<p>Return a list of all configured tasks, along with their configuration.</p>",
    "success": {
      "examples": [
        {
          "title": "Example response:",
          "content": "{\n  \"021b2092ef4111e481a852540064e600\": {\n      \"name\": \"task 1\",\n      \"enabled\": true,\n      \"mode\": \"all\",\n      \"pools\": [\"web\"],\n      \"schedules\": [\n        {\"minute\": [\"*/5\"]}\n      ],\n      \"command\": \"/bin/task1\",\n  },\n  \"508b4b72e44611e49e76c81f66cd0cca\": {\n      \"name\": \"task 2\",\n      \"enabled\": false,\n      \"mode\": \"all\",\n      \"pools\": [\"pool2\"],\n      \"schedules\": [\n        {\"hours\": [15], \"minutes\": [0]}\n      ],\n      \"command\": \"/bin/task2\",\n  }\n}",
          "type": "json"
        }
      ]
    },
    "filename": "./moneta/server.py",
    "groupTitle": "Tasks"
  },
  {
    "type": "get",
    "url": "/task/:id/running",
    "title": "Check if a task is running",
    "name": "IsTaskRunning",
    "group": "Tasks",
    "version": "1.1.0",
    "parameter": {
      "fields": {
        "Parameter": [
          {
            "group": "Parameter",
            "type": "String",
            "optional": false,
            "field": ":id",
            "description": "<p>Task ID.</p>"
          }
        ]
      }
    },
    "success": {
      "fields": {
        "Success 200": [
          {
            "group": "Success 200",
            "type": "Boolean",
            "optional": false,
            "field": "running",
            "description": "<p>The task is running.</p>"
          },
          {
            "group": "Success 200",
            "type": "String",
            "optional": false,
            "field": "id",
            "description": "<p>ID of the task.</p>"
          }
        ]
      },
      "examples": [
        {
          "title": "Example response:",
          "content": "{\n  \"running\": true,\n  \"id\": \"021b2092ef4111e481a852540064e600\"\n}",
          "type": "json"
        }
      ]
    },
    "filename": "./moneta/server.py",
    "groupTitle": "Tasks"
  },
  {
    "type": "get",
    "url": "/task/:id/processes",
    "title": "List running processes for a task",
    "name": "ListTaskProcesses",
    "group": "Tasks",
    "version": "1.1.0",
    "parameter": {
      "fields": {
        "Parameter": [
          {
            "group": "Parameter",
            "type": "String",
            "optional": false,
            "field": ":id",
            "description": "<p>Task ID.</p>"
          }
        ]
      }
    },
    "success": {
      "examples": [
        {
          "title": "Example response:",
          "content": "{\n    \"021b2092ef4111e481a852540064e600\" : {\n        \"node\": \"node1\",\n        \"start_time\": \"2018-03-29T15:01:13.465183+00:00\",\n        \"task\": \"e4d07482e44711e49e76c81f66cd0cca\"\n    },\n    \"253a96e29868135d746989a6123f521e\" : {\n        \"node\": \"node2\",\n        \"start_time\": \"2018-03-29T14:01:13.352067+00:00\",\n        \"task\": \"508b4b72e44611e49e76c81f66cd0cca\"\n    },\n    ...\n}",
          "type": "json"
        }
      ]
    },
    "filename": "./moneta/server.py",
    "groupTitle": "Tasks"
  },
  {
    "type": "post",
    "url": "/tasks",
    "title": "Create a new task",
    "name": "PostTasks",
    "group": "Tasks",
    "version": "1.0.0",
    "description": "<p>Add a new task, providing its configuration.</p>",
    "parameter": {
      "fields": {
        "Parameter": [
          {
            "group": "Parameter",
            "type": "String",
            "optional": false,
            "field": "name",
            "description": "<p>Name.</p>"
          },
          {
            "group": "Parameter",
            "type": "String",
            "optional": false,
            "field": "description",
            "description": "<p>Description.</p>"
          },
          {
            "group": "Parameter",
            "type": "String[]",
            "optional": false,
            "field": "tags",
            "description": "<p>Tags.</p>"
          },
          {
            "group": "Parameter",
            "type": "Boolean",
            "optional": false,
            "field": "enabled",
            "description": "<p>Task is enabled.</p>"
          },
          {
            "group": "Parameter",
            "type": "String",
            "optional": false,
            "field": "mode",
            "description": "<p>Task mode (&quot;any&quot; or &quot;all&quot;).</p>"
          },
          {
            "group": "Parameter",
            "type": "String[]",
            "optional": false,
            "field": "pools",
            "description": "<p>Pools on which the task should run.</p>"
          },
          {
            "group": "Parameter",
            "type": "Object[]",
            "optional": false,
            "field": "schedules",
            "description": "<p>Schedules at which the task should run.</p>"
          },
          {
            "group": "Parameter",
            "type": "String",
            "optional": false,
            "field": "command",
            "description": "<p>Command to run.</p>"
          },
          {
            "group": "Parameter",
            "type": "String",
            "optional": false,
            "field": "workdir",
            "description": "<p>Working directory.</p>"
          },
          {
            "group": "Parameter",
            "type": "String",
            "optional": false,
            "field": "user",
            "description": "<p>User which the task will be run.</p>"
          },
          {
            "group": "Parameter",
            "type": "String",
            "optional": false,
            "field": "group",
            "description": "<p>Group which the task will be run.</p>"
          },
          {
            "group": "Parameter",
            "type": "Object",
            "optional": false,
            "field": "env",
            "description": "<p>Environment variables to set.</p>"
          },
          {
            "group": "Parameter",
            "type": "String",
            "optional": false,
            "field": "mailreport",
            "description": "<p>If the mailer plugin is enabled, condition to send a report (&quot;error&quot;, &quot;stdout&quot;, &quot;stderr&quot;, &quot;output&quot;, &quot;always&quot;).</p>"
          },
          {
            "group": "Parameter",
            "type": "String[]",
            "optional": false,
            "field": "mailto",
            "description": "<p>If the mailer plugin is enabled, email addresses to send the reports to.</p>"
          }
        ]
      },
      "examples": [
        {
          "title": "Example parameters:",
          "content": "{\n  \"name\": \"My task\",\n  \"description\": \"Task description\",\n  \"tags\": [\"tasg1\", \"tag2\"],\n  \"enabled\": true,\n  \"mode\": \"all\",\n  \"pools\": [\"web\"],\n  \"schedules\": [\n    {\"minute\": [\"*/1\"]}\n  ],\n  \"command\": \"/bin/true\",\n  \"workdir\": \"/tmp/\",\n  \"user\": \"www-data\",\n  \"group\": \"www-data\",\n  \"env\": {\n    \"MYENVVAR\": \"myvalue\"\n  },\n  \"mailreport\": \"output\",\n  \"mailto\": [\"user@domain.org\"]\n}",
          "type": "json"
        }
      ]
    },
    "success": {
      "fields": {
        "Success 200": [
          {
            "group": "Success 200",
            "type": "Boolean",
            "optional": false,
            "field": "created",
            "description": "<p>The task has been created.</p>"
          },
          {
            "group": "Success 200",
            "type": "String",
            "optional": false,
            "field": "id",
            "description": "<p>ID of the newly created task.</p>"
          }
        ]
      },
      "examples": [
        {
          "title": "Example response:",
          "content": "{\n  \"created\": true,\n  \"id\": \"021b2092ef4111e481a852540064e600\"\n}",
          "type": "json"
        }
      ]
    },
    "filename": "./moneta/server.py",
    "groupTitle": "Tasks"
  },
  {
    "type": "put",
    "url": "/task/:id",
    "title": "Update a task",
    "name": "PutTask",
    "group": "Tasks",
    "version": "1.0.0",
    "description": "<p>Update a task. Can also be used to create a task with a specific ID.</p>",
    "parameter": {
      "fields": {
        "Parameter": [
          {
            "group": "Parameter",
            "type": "String",
            "optional": false,
            "field": ":id",
            "description": "<p>Task ID.</p>"
          },
          {
            "group": "Parameter",
            "type": "String",
            "optional": false,
            "field": "name",
            "description": "<p>Name.</p>"
          },
          {
            "group": "Parameter",
            "type": "String",
            "optional": false,
            "field": "description",
            "description": "<p>Description.</p>"
          },
          {
            "group": "Parameter",
            "type": "String[]",
            "optional": false,
            "field": "tags",
            "description": "<p>Tags.</p>"
          },
          {
            "group": "Parameter",
            "type": "Boolean",
            "optional": false,
            "field": "enabled",
            "description": "<p>Task is enabled.</p>"
          },
          {
            "group": "Parameter",
            "type": "String",
            "optional": false,
            "field": "mode",
            "description": "<p>Task mode (&quot;any&quot; or &quot;all&quot;).</p>"
          },
          {
            "group": "Parameter",
            "type": "String[]",
            "optional": false,
            "field": "pools",
            "description": "<p>Pools on which the task should run.</p>"
          },
          {
            "group": "Parameter",
            "type": "Object[]",
            "optional": false,
            "field": "schedules",
            "description": "<p>Schedules at which the task should run.</p>"
          },
          {
            "group": "Parameter",
            "type": "String",
            "optional": false,
            "field": "command",
            "description": "<p>Command to run.</p>"
          },
          {
            "group": "Parameter",
            "type": "String",
            "optional": false,
            "field": "workdir",
            "description": "<p>Working directory.</p>"
          },
          {
            "group": "Parameter",
            "type": "String",
            "optional": false,
            "field": "user",
            "description": "<p>User which the task will be run.</p>"
          },
          {
            "group": "Parameter",
            "type": "String",
            "optional": false,
            "field": "group",
            "description": "<p>Group which the task will be run.</p>"
          },
          {
            "group": "Parameter",
            "type": "Object",
            "optional": false,
            "field": "env",
            "description": "<p>Environment variables to set.</p>"
          },
          {
            "group": "Parameter",
            "type": "String",
            "optional": false,
            "field": "mailreport",
            "description": "<p>If the mailer plugin is enabled, condition to send a report (&quot;error&quot;, &quot;stdout&quot;, &quot;stderr&quot;, &quot;output&quot;, &quot;always&quot;).</p>"
          },
          {
            "group": "Parameter",
            "type": "String[]",
            "optional": false,
            "field": "mailto",
            "description": "<p>If the mailer plugin is enabled, email addresses to send the reports to.</p>"
          }
        ]
      },
      "examples": [
        {
          "title": "Example parameters:",
          "content": "{\n  \"name\": \"My task\",\n  \"description\": \"Task description\",\n  \"tags\": [\"tasg1\", \"tag2\"],\n  \"enabled\": true,\n  \"mode\": \"all\",\n  \"pools\": [\"web\"],\n  \"schedules\": [\n    {\"minute\": [\"*/1\"]}\n  ],\n  \"command\": \"/bin/true\",\n  \"workdir\": \"/tmp/\",\n  \"user\": \"www-data\",\n  \"group\": \"www-data\",\n  \"env\": {\n    \"MYENVVAR\": \"myvalue\"\n  },\n  \"mailreport\": \"output\",\n  \"mailto\": [\"user@domain.org\"]\n}",
          "type": "json"
        }
      ]
    },
    "success": {
      "fields": {
        "Success 200": [
          {
            "group": "Success 200",
            "type": "Boolean",
            "optional": false,
            "field": "updated",
            "description": "<p>The task has been updated.</p>"
          },
          {
            "group": "Success 200",
            "type": "String",
            "optional": false,
            "field": "id",
            "description": "<p>ID of the task.</p>"
          }
        ]
      },
      "examples": [
        {
          "title": "Example response:",
          "content": "{\n  \"updated\": true,\n  \"id\": \"021b2092ef4111e481a852540064e600\"\n}",
          "type": "json"
        }
      ]
    },
    "filename": "./moneta/server.py",
    "groupTitle": "Tasks"
  }
] });
