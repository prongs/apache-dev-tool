from __future__ import print_function
from commands import getoutput
import os
import sys
import tempfile
import time
import datetime
import webbrowser


class ReviewPoster:
    def __init__(self, client, opt):
        self.client = client
        self.opt = opt
        self.issue = self.opt.issues[0]
        self.jira = self.opt.jira[0]
        self.opt.reviewboard = self.opt.reviewboard or self.client.get_rb_for_jira(self.jira)
        self.opt.branch = self.opt.branch or self.client.rb_client.branch

    def post_review(self):
        if self.opt.reviewboard:
            review_request = self.client.rb_client.get_review_request(review_request_id=self.opt.reviewboard)
        else:
            review_request = self.client.rb_client.get_review_requests().create(
                repository=self.client.rb_client.repository)
        os.system("git remote update")
        os.system("git merge " + self.opt.branch)
        os.system("git mergetool")
        os.system('git commit -am "merge with ' + self.opt.branch + '"')
        diff_str = getoutput('git diff --full-index --binary ' + self.opt.branch + "..HEAD") + '\n'
        review_request.get_diffs().upload_diff(diff_str)
        draft = review_request.get_draft()
        draft_update_args = {"bugs_closed": self.jira, "branch": self.opt.branch}
        if self.client.rb_client.target_groups:
            draft_update_args['target_groups'] = self.client.rb_client.target_groups
        draft_update_args['summary'] = self.opt.summary or draft.summary or self.issue.fields.summary
        if draft_update_args['summary'].upper().find(self.jira) != 0:
            draft_update_args['summary'] = self.issue.key + ": " + draft_update_args['summary']
        if draft_update_args['summary'] == draft.summary:
            del draft_update_args['summary']
        draft_update_args['description'] = self.opt.description or draft.description or self.issue.fields.description
        if not draft_update_args['description'] or draft_update_args['description'] == draft.description:
            del draft_update_args['description']
        if self.opt.testing_done:
            draft_update_args['testing_done'] = self.opt.testing_done
        if self.opt.testing_done_append:
            draft_update_args['testing_done'] = draft.testing_done + "\n" + "\n".join(self.opt.testing_done_append)
        if self.opt.publish:
            draft_update_args['public'] = True
        draft.update(**draft_update_args)
        self.client.transition_issue(self.issue, 'Start Progress')
        print("created/updated:", review_request.absolute_url)
        if self.opt.open:
            webbrowser.open_new_tab(review_request.absolute_url)
        if not self.opt.reviewboard:
            self.client.put_rb_for_jira(self.jira, review_request.id)
        if self.opt.publish and review_request.get_diffs().total_results <= 1:
            self.client.jira_client.add_comment(self.issue, "Created " + review_request.absolute_url)

    def submit_patch(self):
        if not self.opt.reviewboard:
            print("no reviewboard entry found")
            diff_str = getoutput('git diff --full-index --binary ' + self.opt.branch + "..HEAD")
            pluses = diff_str.count('\n+')
            minuses = diff_str.count('\n-')
            if pluses + minuses > 20:
                print("Creating a review request is recommended. Please use post-review command")
                if raw_input("Do you still want to continue? [Y/N]").lower() not in ['y', 'yes', 'true', 'ok']:
                    sys.exit(0)
            print("Diff is small enough, posting directly to jira as attachment")
            ts = time.time()
            st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d_%H:%M:%S')
            self.attach_patch_in_jira(st, diff_str, "Small enough diff. Attaching directly")
        else:
            review_request = self.client.rb_client.get_review_request(review_request_id=self.opt.reviewboard)
            if self.opt.require_ship_it and (
                    not [review['ship_it'] for review in review_request.get_reviews() if review['ship_it']]):
                print("No Ship it! Reviews on the review request: " + review_request.absolute_url + ". Hence exiting.")
                sys.exit(1)
            diffs = review_request.get_diffs()
            diff_str = diffs[-1].get_patch().data
            self.attach_patch_in_jira("%02d" % len(diffs), diff_str, "Taking patch from reviewboard and attaching")

    def attach_patch_in_jira(self, file_suffix, data, comment):
        if len(data.strip()) == 0:
            print("No diff")
            sys.exit(2)
        patch_file_path = tempfile.gettempdir() + "/" + self.jira + '.' + str(file_suffix) + '.patch'
        with open(patch_file_path, 'w') as patch_file:
            patch_file.write(data)
        print("patch file at: ", patch_file_path)
        if not self.issue.fields.assignee or self.issue.fields.assignee.name != \
                self.client.jira_user:
            self.client.jira_client.assign_issue(self.issue, self.client.jira_user)
        self.client.transition_issue(self.issue, 'Submit Patch')
        self.client.jira_client.add_attachment(self.issue, patch_file_path)
        self.client.jira_client.add_comment(self.issue, comment)
        print("Submitted patch in jira")
