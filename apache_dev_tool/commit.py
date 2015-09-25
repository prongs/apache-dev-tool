from __future__ import print_function
import commands
import os
import sys
from commands import getoutput
import tempfile

import requests
from test_patch import PatchTester


class Committer:
    def __init__(self, client, opt):
        self.client = client
        self.opt = opt
        self.branch = self.opt.branch or self.client.rb_client.branch
        for issue in self.opt.issues:
            if issue.fields.status.name != 'Patch Available':
                raise Exception(issue.key + " is not Patch Available. Skipping all")
        versions = self.client.jira_client.project(self.opt.issues[0].fields.project.id).versions
        dev_version = commands.getoutput(
            "mvn org.apache.maven.plugins:maven-help-plugin:2.1.1:evaluate -Dexpression=project.version"
            "|grep -Ev '(^\[|Download\w+:)'")
        if dev_version.find("SNAPSHOT") == -1:
            raise Exception("Current branch is not on a snapshot version")
        self.fix_version = self.guess_version(dev_version, versions)

    def commit(self):
        os.system("git reset --hard")
        os.system("git checkout " + self.branch)
        os.system("git pull origin " + self.branch)
        for issue in self.opt.issues:
            chosen_attachment = self.client.get_latest_attachment(issue, self.opt.choose_patch)
            email = issue.fields.assignee.emailAddress.replace(' at ', '@').replace(' dot ', '.')
            name = issue.fields.assignee.displayName
            message = issue.fields.summary
            rb_id = self.client.get_rb_for_jira(issue.key)
            if rb_id:
                review_request = self.client.rb_client.get_review_request(review_request_id=rb_id)
                message = review_request.summary
                rb_diff = review_request.get_diffs()[-1].get_patch().data
                jira_diff = requests.get(chosen_attachment.url).text
                if rb_diff.strip() != jira_diff.strip():
                    print("reviewboard diff and chosen diff are different")
                    rb_diff_file_path = tempfile.mktemp()
                    jira_diff_file_path = tempfile.mktemp()
                    with open(rb_diff_file_path, 'w') as rb_diff_file:
                        rb_diff_file.write(rb_diff)
                    with open(jira_diff_file_path, 'w') as jira_diff_file:
                        jira_diff_file.write(jira_diff)
                    os.system("vimdiff %s %s" % (rb_diff_file_path, jira_diff_file_path))
                    if raw_input("Do you still want to commit patch attached in jira? [Y/N]").upper() == 'N':
                        sys.exit(1)
            status = PatchTester.apply_patch(chosen_attachment)
            if status != 0:
                self.client.transition_issue(issue, 'Cancel Patch')
                self.client.jira_client.add_comment(issue,
                                                    "Patch doesn't cleanly apply. Please sync with latest and update")
                sys.exit(status)
            os.system("git add --all .")
            if message.find(issue.key) == -1:
                message = issue.key + ": " + message
            cmd = 'git commit --author "%s <%s>" -m "%s" ' % (name, email, message.replace('"', '\\"'))
            print(cmd)
            status = os.system(cmd)
            if status != 0:
                print("Commit failed")
                sys.exit(status)
            os.system("git commit --amend")
            if self.fix_version:
                issue.fields.fixVersions.append(self.fix_version)
                issue.update(fields={'fixVersions': list(version.raw for version in issue.fields.fixVersions)})
            if issue.fields.assignee.name == self.client.jira_user:
                self.client.jira_client.add_comment(issue, "Committed myself.")
            else:
                self.client.jira_client.add_comment(issue, "Committed. Thanks [~%s]" % issue.fields.assignee.name)
            self.client.transition_issue(issue, 'Resolve Issue')
        if getoutput("git status").find("nothing to commit, working directory clean") != -1:
            print("Everything committed nicely. Pushing")
            os.system("git push origin " + self.branch)

    @staticmethod
    def guess_version(dev_version, versions):
        candidates = []
        for version in versions:
            if dev_version.find(version.name) >= 0:
                candidates.append(version)
        if len(candidates) == 1:
            return candidates[0]
        return None
