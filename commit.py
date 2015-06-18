import os

from bs4 import BeautifulSoup
import requests
import sys


class Attachment:
    def __init__(self, title, url, timestamp):
        self.title = title
        self.url = url
        self.timestamp = timestamp

    def __repr__(self):
        return self.title + "(" + self.timestamp + "): " + self.url

    def __str__(self):
        return self.__repr__()

    def __cmp__(self, other):
        return cmp(self.timestamp, other.timestamp)


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
            url = self.client.jira_client._options['server'] + "/browse/" + issue.key
            bs = BeautifulSoup(requests.get(url).text)
            attachments = []
            for li in bs.find(id="attachmentmodule").find(id="file_attachments").find_all('li'):
                a = li.find("dt").find('a')
                attachment_link = a['data-downloadurl'][a['data-downloadurl'].find('http'):]
                title = a.contents[0].strip()
                upload_time = li.find("dd", {'class': 'attachment-date'}).find('time')['datetime']
                attachments.append(Attachment(title, attachment_link, upload_time))
            attachments.sort()
            chosen_attachment = attachments[-1]
            if self.opt.choose_patch:
                print "The following patches are available. Pick which one you want to commit: "
                for i, attachment in enumerate(attachments):
                    print "%d: %s" % (i, attachment)
                chosen_attachment = attachments[input("Enter the number corresponding to the desired patch: ")]
            status = os.system("curl " + chosen_attachment.url + " | git apply")
            if status != 0:
                "Patch Doesn't cleanly apply."
                sys.exit(status)
            os.system("git add --all .")
            email = issue.fields.assignee.emailAddress.replace(' at ', '@').replace(' dot ', '.')
            name = issue.fields.assignee.displayName
            message = issue.fields.summary
            rb_id = self.client.get_rb_for_jira(issue.key)
            if rb_id:
                review_request = self.client.rb_client.get_review_request(review_request_id=rb_id)
                message = review_request.summary
            if message.find(issue.key) == -1:
                message = issue.key + ": " + message
            cmd = 'git commit --author "%s <%s>" -m "%s" ' % (name, email, message)
            print cmd
            status = os.system(cmd)
            if status != 0:
                print "Commit failed"
                sys.exit(status)
        if self.opt.publish:
            print "publish true, but not pushing commits."