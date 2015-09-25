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


from __future__ import print_function
import logging
import sys
from commands import *
import time

import argparse

from crawler import Crawler
from cleaner import Cleaner
from clients import RBTJIRAClient
from commit import Committer
from post_review import ReviewPoster
from test_patch import PatchTester

possible_options = ['post-review', 'clean', 'submit-patch', 'commit', 'count-comments', 'test-patch']


def option(s):
    s = s.lower()
    if s not in possible_options:
        raise argparse.ArgumentTypeError(
            "you provided " + s + " which is not in possible options: " + str(possible_options))
    return s


def parsed_time(s):
    return time.strptime(s, '%Y-%m-%dT%H:%M:%SZ')


def main():
    popt = argparse.ArgumentParser(description='apache dev tool. Command line helper for frequent actions.')
    popt.add_argument('action', nargs='?', action="store", help="action of the command. One of post-review, "
                                                                "submit-patch, commit and clean", type=option)
    popt.add_argument('-j', '--jira', action='store', dest='jira', required=False,
                      help='JIRAs. provide as -j JIRA1 JIRA2... Mostly only one option will be used, commit command'
                           'can provide multiple jira ids and commit all of them together.',
                      default=[getoutput("git rev-parse --abbrev-ref HEAD")], nargs="*")
    popt.add_argument('-ju', '--jira-username', action='store', dest='jira_username', required=False,
                      help='JIRA Username. If not provided, it will prompt and ask the user.')
    popt.add_argument('-jp', '--jira-password', action='store', dest='jira_password', required=False,
                      help='JIRA Password. If not provided, it will prompt and ask the user.')
    popt.add_argument('-repo', '--repository', action='store', dest='repositories', required=False,
                      help='Reviewboard Repository names', nargs='*', default=[])
    popt.add_argument('-ru', '--reviewboard-username', action='store', dest='reviewboard_username', required=False,
                      help='Reviewboard username'
                           'can provide multiple jira ids and commit all of them together.', nargs="*")
    popt.add_argument('-rp', '--reviewboard-password', action='store', dest='reviewboard_password', required=False,
                      help='Review Board Password. If not provided, it will prompt and ask the user.')
    popt.add_argument('-b', '--branch', action='store', dest='branch', required=False,
                      help='Tracking branch to create diff against. Picks default from .reviewboardrc file')
    popt.add_argument('-s', '--summary', action='store', dest='summary', required=False,
                      help='Summary for the reviewboard. If not provided, jira summary will be picked. ')
    popt.add_argument('-d', '--description', action='store', dest='description', required=False,
                      help='Description for reviewboard. Defaults to description on jira. ')
    popt.add_argument('-r', '--rb', action='store', dest='reviewboard', required=False,
                      help='Review board that needs to be updated. Only needed if you haven\'t created rb entry using '
                           'this tool.')
    popt.add_argument('-t', '--testing-done', action='store', dest='testing_done', required=False,
                      help='Text for the Testing Done section of the reviewboard. Defaults to empty string.')
    popt.add_argument('-ta', '--testing-done-append', action='store', dest='testing_done_append', required=False,
                      help='Text to append to Testing Done section of the reviewboard. Used to provide '
                           'new testing done in addition to old one already mentioned on rb', nargs="*")
    popt.add_argument('-ch', '--choose-patch', action='store_true', dest='choose_patch', required=False,
                      help='Whether Ask for which patch to commit. By default the latest uploaded '
                           'patch is picked for committing.', default=False)
    popt.add_argument('-p', '--publish', action='store_true', dest='publish', required=False,
                      help='Whether to make the review request public', default=False)
    popt.add_argument('-o', '--open', action='store_true', dest='open', required=False,
                      help='Whether to open the review request in browser', default=False)
    popt.add_argument('-tpc', '--test-patch-command', action='store', dest='test_patch_command', required=False,
                      help='Whether to open the review request in browser', default="mvn clean install")
    popt.add_argument('-rs', '--require-ship-it', action='store_true', dest='require_ship_it', required=False,
                      help='Whether to require Ship It! review before posting patch from rb to jira. True by default.',
                      default=True)
    popt.add_argument('-from', '--from', action='store', dest='from_time', required=False, help='Time range start',
                      type=parsed_time)
    popt.add_argument('-to', '--to', action='store', dest='to_time', required=False, help='Time range end',
                      type=parsed_time)
    popt.add_argument('-v', '--verbose', action='store_true', dest='verbose', required=False, help='Verbose',
                      default=False)
    opt = popt.parse_args()

    logging.basicConfig(format='%(asctime)s %(name)-6s %(levelname)-6s %(message)s',
                        level=logging.INFO if opt.verbose else logging.WARN)

    with RBTJIRAClient(opt) as client:
        def validate_jiras():
            opt.issues = [client.valid_jira(jira) for jira in opt.jira]

        def validate_single_jira_provided():
            if len(opt.jira) != 1:
                raise Exception("Only single JIRA expected for this action")

        if opt.action in ['post-review', 'submit-patch', 'test-patch', 'commit']:
            validate_jiras()

        if opt.action in ['post-review', 'submit-patch']:
            validate_single_jira_provided()
            review_poster = ReviewPoster(client, opt)
            if opt.action == 'post-review':
                review_poster.post_review()
            elif opt.action == 'submit-patch':
                review_poster.submit_patch()
        elif opt.action == 'test-patch':
            validate_single_jira_provided()
            return PatchTester(client, opt).test_patch()
        elif opt.action == 'commit':
            return Committer(client, opt).commit()
        elif opt.action == "count-comments":
            return Crawler(client, opt).count_comments()
        elif opt.action == "clean":
            return Cleaner(client).clean()
        else:
            print("Provided action not supported, you provided: ", opt.action)
            print("Provide --help option to understand usage")
            return 1


if __name__ == '__main__':
    sys.exit(main())
