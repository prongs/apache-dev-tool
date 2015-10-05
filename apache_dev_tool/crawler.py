from __future__ import print_function
from collections import Counter, defaultdict
from itertools import chain
import time
import logging


def wrap_pagination(*list_resources):
    sub_lists = []
    for list_resource in list_resources:
        sub_lists.append(list_resource)
        if list_resource.num_items != 0:
            for i in xrange((list_resource.total_results - 1) / list_resource.num_items):
                sub_lists.append(sub_lists[-1].get_next())
    return chain(*sub_lists)


class Crawler:
    def __init__(self, client, opt):
        self.client = client
        self.opt = opt

    def count_comments(self):
        users = self.opt.reviewboard_username or [self.client.rb_client.get_session().get_user().username]
        comment_count = defaultdict(lambda: Counter())
        if self.opt.reviewboard:
            candidate_review_requests = [
                self.client.rb_client.get_review_request(review_request_id=self.opt.reviewboard)]
            total_review_requests = 1
        else:
            review_requests = []
            for repo in self.opt.repositories:
                logging.info("getting review requests for repo %s", repo)
                review_requests.append(self.client.rb_client.get_review_requests(
                    repository=self.client.rb_client.get_repositories(name=repo)[0]['id'],
                    last_updated_from=self.opt.from_time,
                    time_added_to=self.opt.to_time,
                    status="all"))
                logging.info("got %d review requests", review_requests[-1].total_results)
            for user in users:
                logging.info("getting review requests to user %s", user)
                review_requests.append(self.client.rb_client.get_review_requests(
                    to_users=user,
                    last_updated_from=self.opt.from_time,
                    time_added_to=self.opt.to_time,
                    status="all"))
                logging.info("got %d review requests", review_requests[-1].total_results)
                logging.info("getting review requests from user %s", user)
                review_requests.append(self.client.rb_client.get_review_requests(
                    from_user=user,
                    last_updated_from=self.opt.from_time,
                    time_added_to=self.opt.to_time,
                    status="all"))
                logging.info("got %d review requests", review_requests[-1].total_results)
            logging.info("getting all pages for review requests lists")
            total_review_requests = sum(review_request.total_results for review_request in review_requests)
            candidate_review_requests = wrap_pagination(*review_requests)
            logging.info("total review requests(might be repeated): %d", total_review_requests)
        format = '%0' + str(len(str(total_review_requests))) + 'd'
        processed = []
        for counter, review_request in enumerate(candidate_review_requests):
            prefix = ("%s/%s" % (format, format)) % (counter, total_review_requests)
            if review_request.id not in processed:
                logging.info("%s processing review request %s", prefix, review_request.id)
                try:
                    comment_count[review_request.get_repository()['name']] += \
                        self.comments_on_review_request(review_request, users)
                except AttributeError as e:
                    logging.error("Old review requests, repo not available")
                processed.append(review_request.id)
                logging.info("current count: %s", str(comment_count))
            else:
                logging.info("%s not re-processing review request %s", prefix, review_request.id)
        print("Final Count:")
        for repo, count_per_repo in comment_count.items():
            for user, count in count_per_repo.items():
                print(repo, user, count)

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
                        logging.info("%d %04d %s %s: %s", review_request.id, comment_count[review_user],
                                     review.timestamp,
                                     review_user, comment)
            comments = [review.get_diff_comments(), review.get_file_attachment_comments()]
            for reply in wrap_pagination(review.get_replies()):
                comments.append(reply.get_diff_comments())
                comments.append(reply.get_file_attachment_comments())
            for comment in wrap_pagination(*comments):
                username = comment.get_user().username
                if self.timestamp_in_range(comment.timestamp) and username in users:
                    comment_count[username] += 1
                    logging.info("%d %04d %s %s: %s", review_request.id, comment_count[username], comment.timestamp,
                                 username, comment.text)
        return comment_count
