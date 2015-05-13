import os


class Committer:
    def __init__(self, client, opt):
        self.client = client
        self.branch = self.client.branch
        self.issues = list(self.client.jira_client.issue(jira) for jira in opt.jira)
        for issue in self.issues:
            if issue.fields.status.name != 'Patch Available':
                raise Exception(issue.key + " is not Patch Available. Skipping all")

    def commit(self):
        os.system("git checkout " + self.branch)
        os.system("git pull origin " + self.branch)
        for issue in self.issues:
            print issue.fields.attachment