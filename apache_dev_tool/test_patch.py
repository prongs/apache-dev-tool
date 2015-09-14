import commands
import os


def text_status(status):
    return "Success" if status == 0 else "Failure"


class PatchTester:
    def __init__(self, client, opt):
        self.client = client
        self.opt = opt
        self.issue = self.client.jira_client.issue(self.opt.jira)
        self.branch = self.opt.branch or self.client.get_branch()

    def test_patch(self):
        os.system("git reset --hard")
        os.system("git clean -f -d")
        os.system("git checkout " + self.branch)
        os.system("git pull origin " + self.branch)
        attachment = self.client.get_latest_attachment(self.issue)
        apply_command = "curl " + attachment.url + " | git apply"
        status, output = commands.getstatusoutput(apply_command)
        print "apply latest patch status:", text_status(status)
        if status != 0:
            comment = "Patch does not apply. Output of command %s was:\n%s" % (apply_command, output)
            self.client.jira_client.add_comment(self.issue, comment)
            self.client.transition_issue(self.issue, "Cancel Patch")
            return status
        # status, output = commands.getstatusoutput("mvn clean install")
        command = self.opt.test_patch_command
        status = os.system(command)
        comment = "Applied patch: [%s|%s] and ran command: %s. " \
                  "Result: %s. " \
                  "Build Job: %s" % (attachment.title, attachment.url, command,
                                     text_status(status), os.getenv("BUILD_URL", "No url availavle"))
        self.client.jira_client.add_comment(self.issue, comment.strip())
        print "resetting patch " + str(attachment)
        os.system("git reset --hard")
        os.system("git clean -f -d")
