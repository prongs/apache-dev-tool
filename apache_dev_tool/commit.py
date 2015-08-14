import os
import sys
from commands import getoutput
import tempfile

import requests


class Committer:
    def __init__(self, client, opt):
        self.client = client
        self.branch = self.client.branch
        self.issues = list(self.client.jira_client.issue(jira) for jira in opt.jira)
        self.opt = opt
        for issue in self.issues:
            if issue.fields.status.name != 'Patch Available':
                raise Exception(issue.key + " is not Patch Available. Skipping all")

    def commit(self):
        os.system("git reset --hard")
        os.system("git checkout " + self.branch)
        os.system("git pull origin " + self.branch)
        for issue in self.issues:
            chosen_attachment = self.client.get_latest_attachment(issue, self.opt.choose_patch)
            email = issue.fields.assignee.emailAddress.replace(' at ', '@').replace(' dot ', '.')
            name = issue.fields.assignee.displayName
            message = issue.fields.summary
            rb_id = self.client.get_rb_for_jira(issue.key)
            if rb_id:
                review_request = self.client.get_rb_client().get_review_request(review_request_id=rb_id)
                message = review_request.summary
                rb_diff = review_request.get_diffs()[-1].get_patch().data
                jira_diff = requests.get(chosen_attachment.url).text
                if rb_diff.strip() != jira_diff.strip():
                    print "reviewboard diff and chosen diff are different"
                    rb_diff_file_path = tempfile.mktemp()
                    jira_diff_file_path = tempfile.mktemp()
                    with open(rb_diff_file_path, 'w') as rb_diff_file:
                        rb_diff_file.write(rb_diff)
                    with open(jira_diff_file_path, 'w') as jira_diff_file:
                        jira_diff_file.write(jira_diff)
                    os.system("vimdiff %s %s" % (rb_diff_file_path, jira_diff_file_path))
                    if raw_input("Do you still want to commit patch attached in jira? [Y/N]").upper() == 'N':
                        sys.exit(1)
            status = os.system("curl " + chosen_attachment.url + " | git apply")
            if status != 0:
                transitions = [transition for transition in self.client.jira_client.transitions(issue) if
                               transition['name'] == 'Cancel Patch']
                if not transitions:
                    print "No transitions to cancel patch"
                    sys.exit(1)
                self.client.jira_client.add_comment(issue,
                                                    "Patch doesn't cleanly apply. Please sync with latest and update")
                self.client.jira_client.transition_issue(issue, transitions[0]['id'])
                sys.exit(status)
            os.system("git add --all .")
            if message.find(issue.key) == -1:
                message = issue.key + ": " + message
            cmd = 'git commit --author "%s <%s>" -m "%s" ' % (name, email, message.replace('"', '\\"'))
            print cmd
            status = os.system(cmd)
            if status != 0:
                print "Commit failed"
                sys.exit(status)
            os.system("git commit --amend")
            transitions = [transition for transition in self.client.jira_client.transitions(issue) if
                           transition['name'] == 'Resolve Issue']
            if not transitions:
                print "No transitions for resolve issue"
                sys.exit(1)
            if issue.fields.assignee.name == self.client.jira_client.session()._session.auth[0]:
                self.client.jira_client.add_comment(issue, "Committed myself.")
            else:
                self.client.jira_client.add_comment(issue, "Committed. Thanks [~%s]" % (issue.fields.assignee.name))
            self.client.jira_client.transition_issue(issue, transitions[0]['id'])
        if getoutput("git status").find("nothing to commit, working directory clean") != -1:
            print "Everything committed nicely. Pushing"
            os.system("git push origin " + self.branch)