import os


class PatchTester:
    def __init__(self, client, opt):
        self.client = client
        self.opt = opt
        self.issue = self.client.jira_client.issue(self.opt.jira)
        self.opt.branch = self.opt.branch or self.client.branch

    def test_patch(self):
        attachment = self.client.get_latest_attachment(self.issue)
        status = os.system("curl " + attachment.url + " | git apply")
        print "apply latest patch status:", status
        if status != 0:
            return status
        # status, output = commands.getstatusoutput("mvn clean install")
        command = "mvn clean install"
        status = os.system(command)
        comment = "Command: " + command + " in Pre Commit Build " + (
            "Succeeded" if status == 0 else "Failed") + " " + os.getenv("BUILD_URL", "")
        self.client.jira_client.add_comment(self.issue, comment.strip())
