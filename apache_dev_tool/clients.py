from __future__ import print_function
from getpass import getpass
import logging
import os
import pickle
import time

from rbtools.api.client import RBClient
from bs4 import BeautifulSoup
from jira.client import JIRA
from rbtools.api.transport.sync import SyncTransport
import requests
from utils import cached_property


class RetryingSyncTransport(SyncTransport):
    def _execute_request(self, request):
        for i in xrange(10):
            try:
                return super(RetryingSyncTransport, self)._execute_request(request)
            except Exception as e:
                logging.error("Retry#%d, error: " % i + str(e))
                time.sleep(i * 3)
        raise Exception("Couldn't make request even after 10 retries")


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


class RBTJIRAClient:
    def __init__(self, opt):
        self.opt = opt

    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save_jira_to_rbt_map()

    @cached_property
    def post_review_dir(self):
        rbt_jira_dir = os.path.join(os.getenv('HOME'), ".apache-dev-tool")
        if not os.path.exists(rbt_jira_dir):
            os.mkdir(rbt_jira_dir)
        return rbt_jira_dir

    def valid_jira(self, jira):
        try:
            return self.jira_client.issue(jira.upper())
        except Exception as e:
            raise Exception("jira " + jira + " is not valid", e)

    @cached_property
    def jira_to_rbt_map(self):
        map_path = os.path.join(self.post_review_dir, 'jira-to-rbt.map')
        if os.path.exists(map_path):
            with open(map_path) as map_file:
                try:
                    ret = pickle.load(map_file)
                    return ret
                except:
                    pass
        return {}


    def save_jira_to_rbt_map(self):
        map_path = os.path.join(self.post_review_dir, 'jira-to-rbt.map')
        with open(map_path, 'w') as map_file:
            pickle.dump(self.jira_to_rbt_map, map_file)

    def put_rb_for_jira(self, jira, rb):
        self.jira_to_rbt_map[jira.upper()] = rb

    def get_rb_for_jira(self, jira):
        if not self.jira_to_rbt_map.has_key(jira.upper()):
            issue = self.jira_client.issue(jira)
            rb_comments = (comment for comment in issue.fields.comment.comments if
                           comment.body.find('reviews.apache.org/r/') > 0)
            rb_ids = set()
            for comment in rb_comments:
                try:
                    review_request_id = comment.body[
                                        comment.body.find("reviews.apache.org/r/") + len("reviews.apache.org/r/"):] + "/"
                    review_request_id = review_request_id[:review_request_id.find('/')]
                    rb_ids.add(int(review_request_id))
                except Exception:
                    pass
            if len(rb_ids) == 1:
                self.jira_to_rbt_map[jira.upper()] = list(rb_ids)[0]
            else:
                review_requests = []
                for review_request_id in rb_ids:
                    try:
                        review_request = self.rb_client.get_review_request(review_request_id=review_request_id)
                        if review_request.status in ['pending'] and \
                                (jira in review_request.bugs_closed or review_request.summary.find(jira) >= 0):
                            review_requests.append(review_request)
                    except:
                        pass
                if len(review_requests) == 1:
                    self.jira_to_rbt_map[jira.upper()] = review_requests[0].id
                else:
                    msg = "Could not determine review request uniquely. Options were: \n"
                    for review_request in review_requests:
                        msg += "\t" + str(review_request.id) + ":" + review_request.summary + "(solves " + ','.join(
                            bug for bug in review_request.bugs_closed) + ")\n"
                    logging.warn(msg)
            return self.jira_to_rbt_map.get(jira.upper(), None)

    @cached_property
    def jira_client(self):
        options = {
            'server': 'https://issues.apache.org/jira'
        }
        # read the config file
        post_review_path = self.post_review_dir
        jira_path = os.path.join(post_review_path, "jira")
        if os.path.exists(jira_path):
            with open(jira_path) as jira_file:
                try:
                    jira = pickle.load(jira_file)
                    # this is a hack
                    jira._session.max_retries = 3
                    if jira.session():
                        return jira
                except:
                    pass
        username = self.opt.jira_username or raw_input("Enter JIRA Username: ")
        password = self.opt.jira_password or getpass("Enter password: ")
        jira = JIRA(options, basic_auth=(username, password))
        with open(jira_path, 'wb') as jira_file:
            pickle.dump(jira, jira_file)
        return jira


    @cached_property
    def rb_client(self):
        options = {}
        if os.path.exists(".reviewboardrc"):
            with open(".reviewboardrc") as reviewboardrc:
                for line in reviewboardrc:
                    if line.startswith("#"):
                        continue
                    if len(line.strip()) == 0:
                        continue
                    k, v = line.strip().split("=")
                    k = k.strip()
                    v = eval(v.strip())
                    options[k] = v
        rbclient = RBClient(options.get('REVIEWBOARD_URL') or 'https://reviews.apache.org/', RetryingSyncTransport)
        if not rbclient.get_root().get_session()['authenticated']:
            username = self.opt.reviewboard_username[0] if self.opt.reviewboard_username and \
                                                           self.opt.reviewboard_username[0] else raw_input(
                "Enter review board Username: ")
            password = self.opt.reviewboard_password or getpass("Enter password for %s: " % username)
            rbclient.login(username, password)
        root = rbclient.get_root()
        root.repository = options.get('REPOSITORY') or None
        root.branch = options.get('BRANCH') or options.get('TRACKING_BRANCH')
        root.target_groups = None
        if options.has_key('TARGET_GROUPS'):
            root.target_groups = options['TARGET_GROUPS']
        return root

    def get_latest_attachment(self, issue, choose_patch=False):
        attachments = []
        url = self.jira_client._options['server'] + "/browse/" + issue.key
        bs = BeautifulSoup(requests.get(url).text)
        for li in bs.find(id="attachmentmodule").find(id="file_attachments").find_all('li'):
            a = li.find("dt").find('a')
            attachment_link = a['data-downloadurl'][a['data-downloadurl'].find('http'):]
            title = a.contents[0].strip()
            upload_time = li.find("dd", {'class': 'attachment-date'}).find('time')['datetime']
            if title.split(".")[-1] in ('txt', 'patch'):
                attachments.append(Attachment(title, attachment_link, upload_time))
        attachments.sort()
        chosen_attachment = attachments[-1]
        if choose_patch:
            print("The following patches are available. Pick which one you want to commit: ")
            for i, attachment in enumerate(attachments):
                print("%d: %s" % (i, attachment))
            chosen_attachment = attachments[input("Enter the number corresponding to the desired patch: ")]
        return chosen_attachment

    def transition_issue(self, issue, name):
        transitions = [transition for transition in self.jira_client.transitions(issue) if transition['name'] == name]
        if len(transitions) == 0:
            print("No transitions for " + name + " for issue " + issue.key)
            return False
        if len(transitions) > 1:
            print("multiple transitions for " + name + " for issue " + issue.key)
            return False
        self.jira_client.transition_issue(issue, transitions[0]['id'])
        return True

    @property
    def jira_user(self):
        return self.jira_client.session()._session.auth[0]
