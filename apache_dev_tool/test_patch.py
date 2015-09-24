from __future__ import print_function
import commands
import os


def text_status(status):
    return "Success" if status == 0 else "Failure"


class PatchTester:
    def __init__(self, client, opt):
        self.opt = opt
        self.issue = self.opt.issues[0]
        self.client = client
        self.branch = self.opt.branch or self.client.rb_client.branch

    def test_patch(self):
        os.system("git reset --hard")
        os.system("git clean -f -d")
        os.system("git checkout " + self.branch)
        os.system("git pull origin " + self.branch)
        attachment = self.client.get_latest_attachment(self.issue)
        if self.apply_patch(attachment) != 0:
            comment = "Patch does not apply. Build job: %s" % (os.getenv("BUILD_URL", "No url availavle"))
            self.client.jira_client.add_comment(self.issue, comment)
            self.client.transition_issue(self.issue, "Cancel Patch")
            return -1
        command = self.opt.test_patch_command
        status = os.system(command)
        comment = "Applied patch: [%s|%s] and ran command: %s. " \
                  "Result: %s. " \
                  "Build Job: %s" % (attachment.title, attachment.url, command,
                                     text_status(status), os.getenv("BUILD_URL", "No url availavle"))
        self.client.jira_client.add_comment(self.issue, comment.strip())
        print("resetting patch ", str(attachment))
        os.system("git reset --hard")
        os.system("git clean -f -d")

    @staticmethod
    def apply_patch(attachment):
        apply_command_base = "curl " + attachment.url + " | git apply"
        status = -1
        for suffix in ["", "-p0", "-p1"]:
            apply_command = apply_command_base + " " + suffix
            print("applying patch with", apply_command)
            os.system("git reset --hard")
            os.system("git clean -f -d")
            status, output = commands.getstatusoutput(apply_command)
            print("apply latest patch status:", text_status(status))
            if status == 0:
                return 0
        return status
