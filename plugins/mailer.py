# -*- coding: utf-8 -*-

from __future__ import absolute_import

import logging

from email.mime.text import MIMEText
import smtplib
from textwrap import dedent

logger = logging.getLogger('moneta.plugins.mailer')

def getDependencies():
    return ['PluginRegistry', 'Cluster']

def init(config, registry, cluster):
    return MailerPlugin(config, registry, cluster)

class MailerPlugin(object):
    def __init__(self, config, registry, cluster):
        self.config = config
        self.registry = registry
        self.cluster = cluster

        self.registry.register_hook('ReceivedReport', self.onReceivedReport)

    def onReceivedReport(self, report):
        """Send a report by email"""

        task = report['task']
        taskconfig = self.cluster.config['tasks'][task]

        report['task_name'] = taskconfig['name']
        if 'tags' in taskconfig:
            report['task_tags'] = taskconfig['tags']

        if not ('mailreport' in taskconfig and (
                (taskconfig['mailreport'] == 'error' and report['status'] != 'ok')
                or (taskconfig['mailreport'] == 'stdout' and 'stdout' in report and report['stdout'])
                or (taskconfig['mailreport'] == 'stderr' and 'stderr' in report and report['stderr'])
                or (taskconfig['mailreport'] == 'output' and (
                    ('stderr' in report and report['stderr'])
                    or ('stdout' in report and report['stdout'])
                    ))
                or taskconfig['mailreport'] == 'always'
            )):
            return

        logger.info("Sending mail report for task %s", task)

        if not self.cluster.config['smtpserver']:
            raise Exception("An email report should be delivered for task %s, but no smtp server has been configured.")

        if not self.cluster.config['email']:
            raise Exception("An email report should be delivered for task %s, but no sender email has been configured.")

        if not 'mailto' in taskconfig or not taskconfig['mailto']:
            raise Exception("An email report should be delivered for task %s, but the task has no mailto parameter or mailto is empty.")

        # Template

        msgbody = dedent(
            u"""\
            Task: {task[name]}
            -------------------------------------------------------------------------------
            Command: {task[command]}
            -------------------------------------------------------------------------------
            Status: {report[status]}
            Executed on node: {report[node]}
            Started: {report[start_time]}
            Ended: {report[end_time]}
            Duration: {report[duration]} seconds
            -------------------------------------------------------------------------------
            """)

        if report['status'] == "fail":
            msgbody += "Error: {report[error]}\n"
        else:
            msgbody += "Return code: {report[returncode]}\n"

            if report['stdout']:
                msgbody += dedent(
                    """\

                    stdout :
                    -------------------------------------------------------------------------------
                    {report[stdout]}
                    -------------------------------------------------------------------------------
                    """)

            if report['stderr']:
                msgbody += dedent(
                    """\

                    stderr :
                    -------------------------------------------------------------------------------
                    {report[stderr]}
                    -------------------------------------------------------------------------------
                    """)

        # Message

        msg = MIMEText(msgbody.format(task = taskconfig, report = report), "plain", "utf-8")

        mailto = taskconfig['mailto']
        if isinstance(mailto, str) or isinstance(mailto, unicode):
            mailto = [ mailto ]

        msg['Subject'] = u"Moneta Execution Report - Task %s" % taskconfig['name']
        msg['From'] = self.cluster.config['email']
        msg['To'] = ",".join(mailto)

        msg['X-Moneta-Status'] = report['status']
        if 'returncode' in report:
            msg['X-Moneta-Return-Code'] = "%d" % (report['returncode'])

        # Send

        s = smtplib.SMTP(self.cluster.config['smtpserver'])
        s.sendmail(self.cluster.config['email'], mailto, msg.as_string())
        s.quit()
