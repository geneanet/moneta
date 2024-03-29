# -*- coding: utf-8 -*-



import logging

from email.mime.text import MIMEText
import smtplib
from textwrap import dedent
import dateutil.tz
import dateutil.parser
from jinja2 import Environment
import math

logger = logging.getLogger('moneta.plugins.mailer')

default_template  = dedent(
    '''\
    -------------------------------------------------------------------------------
    Task: {{ task.name }}
    Command: {{ task.command }}
    -------------------------------------------------------------------------------
    Status: {{ report.status }}
    Executed on node: {{ report.node }}
    Started: {{ report.start_time|format_datetime }} (time zone {{ report.start_time|format_datetime('%Z') }})
    Ended: {{ report.end_time|format_datetime }}
    Duration: {{ report.duration|format_duration }}
    {% if report.status == 'fail' -%}
    Error: {{ report.error }}
    {%- else -%}
    Return code: {{ report.returncode }}
    {%- endif %}
    -------------------------------------------------------------------------------
    Max memory used: {{ report.maxrss|format_bytes }}
    CPU time: {{ report.cputime_system|format_duration }} system; {{ report.cputime_user|format_duration }} user
    -------------------------------------------------------------------------------
    {% if report.output.buffer|length > 0 -%}
    Program produced {{ report.output.bytes.stdout }} bytes on stdout and {{ report.output.bytes.stderr }} bytes on stderr.
    Last {{ report.output.buffer|length }} lines of output :
    {% for line in report.output.buffer -%}
    {{ line.time|format_datetime('%d/%m %X') }} | {{ line.channel }} | {{ line.text }}
    {% endfor -%}
    -------------------------------------------------------------------------------
    {%- endif %}
    ''')

def getDependencies():
    """ Return modules that need to be injected to the plugin constructor """
    return ['PluginRegistry', 'Cluster']

def init(config, registry, cluster):
    """ Instanciate the plugin """
    return MailerPlugin(config, registry, cluster)

class MailerPlugin(object):
    """ Mailer Plugin """

    def __init__(self, config, registry, cluster):
        """ Constructor """
        self.config = config
        self.registry = registry
        self.cluster = cluster

        self.cluster.config.create_key('mailer', {
            'smtpserver': None,
            'sender': None,
            'timezone': None,
            'template': default_template
        }, self.__validate_config)

        self.registry.register_hook('ReceivedReport', self.onReceivedReport)

    @staticmethod
    def __validate_config(config):
        """ Validate plugin the configuration """
        if not isinstance(config, dict):
            raise TypeError('Value must be a dictionary')

        if not set(config.keys()).issubset(set(['smtpserver', 'sender', 'timezone'])):
            raise ValueError('Allowed keys are: smtpserver, sender and timezone')

        if 'timezone' in config and config['timezone'] and not dateutil.tz.gettz(config['timezone']):
            raise ValueError('Timezone {0} not supported'.format(config['timezone']))

        if not config['smtpserver'] or not config['sender']:
            raise ValueError('Keys smtpserver and sender must be specified')

    def onReceivedReport(self, report):
        """Send a report by email"""

        try:
            report = dict(report)

            task = report['task']
            taskconfig = self.cluster.config.get('tasks')[task]
            mailerconfig = self.cluster.config.get('mailer')

            report['task_name'] = taskconfig['name']
            if 'tags' in taskconfig:
                report['task_tags'] = taskconfig['tags']

            if not ('mailreport' in taskconfig and (
                    (taskconfig['mailreport'] == 'error' and report['status'] != 'ok')
                    or (taskconfig['mailreport'] == 'stdout' and report['output']['bytes']['stdout'] > 0)
                    or (taskconfig['mailreport'] == 'stderr' and report['output']['bytes']['stderr'] > 0)
                    or (taskconfig['mailreport'] == 'output' and len(report['output']['buffer']) > 0)
                    or taskconfig['mailreport'] == 'always'
                )):
                return

            logger.info("Sending mail report for task %s", task)

            if not 'smtpserver' in mailerconfig or not mailerconfig['smtpserver']:
                raise Exception("An email report should be delivered for task %s, but no smtp server has been configured." % task)

            if not 'sender' in mailerconfig or not mailerconfig['sender']:
                raise Exception("An email report should be delivered for task %s, but no sender email has been configured." % task)

            if not 'mailto' in taskconfig or not taskconfig['mailto']:
                raise Exception("An email report should be delivered for task %s, but the task has no mailto parameter or mailto is empty." % task)

            # Message
            env = Environment()

            def format_datetime(dt, format='%x %X'):
                if 'timezone' in mailerconfig and mailerconfig['timezone']:
                    dt = dt.astimezone(dateutil.tz.gettz(mailerconfig['timezone']))
                return dt.strftime(format)
            env.filters['format_datetime'] = format_datetime

            def format_bytes(size):
                units = ['B', 'KB', 'MB', 'GB', 'TB']
                u = 0
                while size > 1024:
                    size /= 1024
                    u += 1
                return '%.2f %s' % (size, units[u])
            env.filters['format_bytes'] = format_bytes

            def format_duration(duration):
                units = ['d', 'h', 'min', 's', 'ms']
                units_s = [86400, 3600, 60, 1, 0.001]
                output = ''
                for u in range(0, len(units)):
                    if (duration < units_s[u]):
                        continue
                    t = math.floor(duration / units_s[u])
                    output += '%d%s ' % (t, units[u])
                    duration %= units_s[u]
                return output.rstrip()
            env.filters['format_duration'] = format_duration

            template = env.from_string(mailerconfig['template'] if ('template' in mailerconfig and mailerconfig['template']) else default_template)
            mail_body = template.render(task = taskconfig, report = report)
            msg = MIMEText(mail_body, "plain", "utf-8")

            mailto = taskconfig['mailto']
            if isinstance(mailto, str):
                mailto = [ mailto ]

            msg['Subject'] = "Execution Report - Task %s (status: %s)" % (taskconfig['name'], report['status'])
            msg['From'] = mailerconfig['sender']
            msg['To'] = ",".join(mailto)

            msg['X-Moneta-Status'] = report['status']
            if 'returncode' in report:
                msg['X-Moneta-Return-Code'] = "%d" % (report['returncode'])

            # Send

            s = smtplib.SMTP(mailerconfig['smtpserver'])
            s.sendmail(mailerconfig['sender'], mailto, msg.as_string())
            s.quit()

        except Exception as e:
            logger.exception(e)
            logger.error('An error has been encountered while sending a report by mail (%s)', str(e))
