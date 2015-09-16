from collections import Counter, defaultdict
from itertools import chain
import time


def wrap_pagination(*list_resources):
    sub_lists = []
    for list_resource in list_resources:
        sub_lists.append(list_resource)
        if list_resource.num_items not in [0, list_resource.total_results]:
            for i in xrange(list_resource.total_results / list_resource.num_items):
                sub_lists.append(sub_lists[-1].get_next())
    return chain(*sub_lists)


class Crawler:
    def __init__(self, client, opt):
        self.client = client
        self.opt = opt

    def count_comments(self):
        users = self.opt.reviewboard_username or [self.client.get_rb_client().get_session().get_user().username]
        comment_count = defaultdict(lambda: Counter())
        if self.opt.reviewboard:
            candidate_review_requests = [
                self.client.get_rb_client().get_review_request(review_request_id=self.opt.reviewboard)]
        else:
            review_requests = []
            for repo in self.opt.repositories:
                review_requests.append(self.client.get_rb_client().get_review_requests(
                    repository=repo,
                    last_updated_from=self.opt.from_time,
                    time_added_to=self.opt.to_time,
                    status="all"))
            for user in users:
                review_requests.append(self.client.get_rb_client().get_review_requests(
                    to_users=user,
                    last_updated_from=self.opt.from_time,
                    time_added_to=self.opt.to_time,
                    status="all"))
                review_requests.append(self.client.get_rb_client().get_review_requests(
                    from_user=user,
                    last_updated_from=self.opt.from_time,
                    time_added_to=self.opt.to_time,
                    status="all"))
            candidate_review_requests = wrap_pagination(*review_requests)
        processed = []
        for review_request in candidate_review_requests:
            if review_request.id not in processed:
                comment_count[review_request.get_repository()['name']] += \
                    self.comments_on_review_request(review_request, users)
                processed.append(review_request.id)
        print "Final Count:"
        for repo, count_per_repo in comment_count.items():
            for user, count in count_per_repo.items():
                print repo, user, count


    def timestamp_in_range(self, t):
        timestamp = time.strptime(t, '%Y-%m-%dT%H:%M:%SZ')
        return not (
            (self.opt.from_time and self.opt.from_time > timestamp) or (
            self.opt.to_time and self.opt.to_time <= timestamp))

    def comments_on_review_request(self, review_request, users):
        comment_count = Counter()
        for review in wrap_pagination(review_request.get_reviews()):
            review_user = review.get_user().username
            if review_user in users and self.timestamp_in_range(review.timestamp):
                for comment in [review.body_top, review.body_bottom]:
                    if len(comment) > 0:
                        comment_count[review_user] += 1
                        if self.opt.verbose:
                            print comment
            comments = [review.get_diff_comments(), review.get_file_attachment_comments()]
            for reply in wrap_pagination(review.get_replies()):
                comments.append(reply.get_diff_comments())
                comments.append(reply.get_file_attachment_comments())
            for comment in wrap_pagination(*comments):
                for i in xrange(10):
                    try:
                        username = comment.get_user().username
                        if self.timestamp_in_range(comment.timestamp) and username in users:
                            comment_count[username] += 1
                            if self.opt.verbose:
                                print review_request.id, \
                                    ("%04d" % comment_count[username]), comment.timestamp, username, ":", comment.text
                        break
                    except Exception as e:
                        print e
        return comment_count
