from __future__ import print_function
import commands
import os
import re


class Cleaner:
    def __init__(self, client):
        self.client = client

    def clean(self):
        self.clean_branches()
        self.close_review_requests()

    def clean_branches(self):
        print("Cleaning Branches")
        for branch in (x for x in commands.getoutput("git branch | awk '{print $(NF)}'").strip().split() if
                       x[:5] == 'LENS-'):
            jira = re.match(r'^LENS-\d+', branch).group(0)
            issue = self.client.jira_client.issue(jira)
            resolution = issue.fields.resolution
            if resolution and resolution.name == 'Fixed':
                print("Deleting branch %s as issue %s is marked Fixed" % (branch, issue))
                os.system("git branch -D %s" % branch)
                os.system("git push origin --delete %s" % branch)
        print("Done")

    def close_review_requests(self):
        print("Closing review requests of fixed jiras")
        to_delete = []
        for jira, rb_id in self.client.jira_to_rbt_map.items():
            issue = self.client.jira_client.issue(jira)
            resolution = issue.fields.resolution
            if resolution and resolution.name == 'Fixed':
                to_delete.append(jira)
                self.client.rb_client.get_review_request(review_request_id=rb_id).update(status='submitted')
        for jira in to_delete:
            del self.client.jira_to_rbt_map[jira]
        print("Done")
