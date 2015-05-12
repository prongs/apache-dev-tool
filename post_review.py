from commands import getoutput
import os
import sys
import tempfile
import time
import datetime


class ReviewPoster:
    def __init__(self, client, opt):
        self.client = client
        self.opt = opt
        self.opt.jira = self.opt.jira[0].upper()
        self.issue = self.client.jira_client.issue(self.opt.jira)
        self.opt.reviewboard = self.opt.reviewboard or self.client.get_rb_for_jira(self.opt.jira)
        self.opt.branch = self.opt.branch or self.client.branch

    def post_review(self):
        if self.opt.reviewboard:
            review_request = self.client.rb_client.get_review_request(review_request_id=self.opt.reviewboard)
        else:
            review_request = self.client.rb_client.get_review_requests().create(repository=self.client.repository)
        os.system("git remote update")
        os.system("git merge " + self.opt.branch)
        os.system("git mergetool")
        os.system('git commit -am "merge with ' + self.opt.branch + '"')
        diff_str = getoutput('git diff ' + self.opt.branch + "..HEAD")
        review_request.get_diffs().upload_diff(diff_str)
        draft = review_request.get_draft()
        draft_update_args = {"bugs_closed": self.opt.jira}
        if self.client.reviewers:
            draft_update_args['target_groups'] = self.client.reviewers
        draft_update_args['summary'] = self.opt.summary or draft.summary or self.issue.fields.summary
        if draft_update_args['summary'].upper().find(self.opt.jira) != 0:
            draft_update_args['summary'] = self.issue.key + ": " + draft_update_args['summary']
        if draft_update_args['summary'] == draft.summary:
            del draft_update_args['summary']
        if not draft.description or self.opt.description:
            draft_update_args['description'] = self.opt.description or self.issue.fields.description
            if not draft_update_args['description']:
                del draft_update_args['description']
        if self.opt.testing_done:
            draft_update_args['testing_done'] = self.opt.testing_done
        if self.opt.publish:
            draft_update_args['public'] = True
        draft.update(**draft_update_args)
        print "created/updated:", review_request.absolute_url
        if not self.opt.reviewboard:
            self.client.put_rb_for_jira(self.opt.jira, review_request.id)
        if self.opt.publish and review_request.get_diffs().total_results <= 1:
            self.client.jira_client.add_comment(self.issue, "Created " + review_request.absolute_url)

    def avail_patch(self):
        if not self.opt.reviewboard:
            diff_str = getoutput('git diff ' + self.opt.branch + "..HEAD")
            pluses = diff_str.count('\n+')
            minuses = diff_str.count('\n-')
            if pluses + minuses > 10:
                print "Creating a review request is recommended. Please use post-review command"
                sys.exit(0)
            print "Diff is small enough, posting directly to jira as attachment"
            ts = time.time()
            st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d_%H:%M:%S')
            self.attach_patch_in_jira(st, diff_str, "Small enough diff. Attaching directly")
        else:
            review_request = self.client.rb_client.get_review_request(review_request_id=self.opt.reviewboard)
            if not [review['ship_it'] for review in review_request.get_reviews() if review['ship_it']]:
                print "No Ship it! Reviews on the review request: " + review_request.absolute_url + ". Hence exiting."
                sys.exit(1)
            diffs = review_request.get_diffs()
            diff_str = diffs[-1].get_patch().data
            self.attach_patch_in_jira("%02d" % len(diffs), diff_str, "Taking patch from reviewboard and attaching")

    def attach_patch_in_jira(self, file_suffix, data, comment):
        patch_file_path = tempfile.gettempdir() + "/" + self.opt.jira + '_' + str(file_suffix) + '.patch'
        with open(patch_file_path, 'wb') as patch_file:
            patch_file.write(data)
        self.client.jira_client.add_attachment(self.issue, patch_file_path)
        self.client.jira_client.add_comment(self.issue, comment)
        print "Attached to jira"