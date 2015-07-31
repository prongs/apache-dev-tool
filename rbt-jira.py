#!/usr/bin/env python

# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# Modified based on Kafka's patch review tool

# Required Modules:
# - python-argparse
# - python-rbtools
# - python-setuptools
# - jira
# - jira-python


import sys
from commands import *

import argparse

from cleaner import Cleaner
from clients import RBTJIRAClient
from commit import Committer
from post_review import ReviewPoster

possible_options = ['post-review', 'clean', 'submit-patch', 'commit']


def Option(s):
    s = s.lower()
    if s not in possible_options:
        raise argparse.ArgumentTypeError(
            "you provided " + s + " which is not in possible options: " + str(possible_options))
    return s


def main():
    ''' main(), shut up, pylint '''
    popt = argparse.ArgumentParser(description='rbt jira command line tool')
    popt.add_argument('action', nargs='?', action="store", help="action of the command. One of post-review, "
                                                                "submit-patch, commit and clean")
    popt.add_argument('-j', '--jira', action='store', dest='jira', required=False,
                      help='JIRAs. ',
                      default=[getoutput("git rev-parse --abbrev-ref HEAD")], nargs="*")
    popt.add_argument('-b', '--branch', action='store', dest='branch', required=False,
                      help='Tracking branch to create diff against')
    popt.add_argument('-s', '--summary', action='store', dest='summary', required=False,
                      help='Summary for the reviewboard')
    popt.add_argument('-m', '--commit-message', action='store', dest='commit_message', required=False,
                      help='Commit Message')
    popt.add_argument('-d', '--description', action='store', dest='description', required=False,
                      help='Description for reviewboard')
    popt.add_argument('-r', '--rb', action='store', dest='reviewboard', required=False,
                      help='Review board that needs to be updated')
    popt.add_argument('-t', '--testing-done', action='store', dest='testing_done', required=False,
                      help='Text for the Testing Done section of the reviewboard')
    popt.add_argument('-ta', '--testing-done-append', action='store', dest='testing_done_append', required=False,
                      help='Text to append to Testing Done section of the reviewboard', nargs="*")
    popt.add_argument('-c', '--comment', action='store', dest='comment', required=False,
                      help='What to comment on jira')
    popt.add_argument('-ch', '--choose-patch', action='store_true', dest='choose_patch', required=False,
                      help='Whether Ask for which patch to commit.', default=False)
    popt.add_argument('-p', '--publish', action='store_true', dest='publish', required=False,
                      help='Whether to make the review request public', default=False)
    popt.add_argument('-o', '--open', action='store_true', dest='open', required=False,
                      help='Whether to open the review request in browser', default=False)
    popt.add_argument('-rs', '--require-ship-it', action='store_true', dest='require_ship_it', required=False,
                      help='Whether to require Ship It! review before posting patch from rb to jira', default=False)
    opt = popt.parse_args()

    client = RBTJIRAClient()
    if opt.action in ['post-review', 'submit-patch']:
        if len(opt.jira) != 1:
            print "Please supply exactly one jira for", opt.action
            sys.exit(1)
        client.valid_jira(opt.jira[0])
        review_poster = ReviewPoster(client, opt)
        if opt.action == 'post-review':
            review_poster.post_review()
        else:
            review_poster.submit_patch()
    elif opt.action == 'commit':
        Committer(client, opt).commit()
    elif opt.action == "clean":
        Cleaner(client).clean()


if __name__ == '__main__':
    sys.exit(main())
