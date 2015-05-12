from commands import getoutput
import os


class ReviewPoster:
    def __init__(self, client, opt):
        self.client = client
        self.opt = opt
        self.opt.jira = self.opt.jira.upper()
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


