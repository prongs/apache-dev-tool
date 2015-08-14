# apache-dev-tool 
Dev tool for Apache Contributors. Provides helpful scripts for review request, jira, and jenkins

## Installation
You can install like this:

    pip install apache-dev-tool --allow-external RBTools

If you want to help in development, clone from [github](https://github.com/prongs/apache-dev-tool)

## Usage
Go to your project's directory. e.g. I'm using it to work on `apache incubator lens`, so I'll do `cd /path/to/clone/of/incubator-lens`. I've already installed `apache-dev-tool`. I'll make sure I have the following things inside `/path/to/clone/of/incubator-lens/.reviewboardrc`:
    
    REVIEWBOARD_URL = "https://reviews.apache.org/"
    REPOSITORY = "lens"
    BRANCH = "master"
    TARGET_GROUPS = 'lens'
    GUESS_FIELDS = True

I'll assume you are using reviewboard(of course) and can understand what the above lines mean. So just change them accordingly.
I can give two examples: [lens](https://github.com/apache/incubator-lens/blob/master/.reviewboardrc) and [hive](https://github.com/apache/hive/blob/master/.reviewboardrc)
`TRACKING_BRANCH` can also be used in place of `BRANCH`

This is what help for the command shows:

        $ apache-dev-tool --help
        usage: apache-dev-tool [-h] [-j [JIRA [JIRA ...]]] [-ju JIRA_USERNAME]
                               [-jp JIRA_PASSWORD] [-ru REVIEWBOARD_USERNAME]
                               [-rp REVIEWBOARD_PASSWORD] [-b BRANCH] [-s SUMMARY]
                               [-d DESCRIPTION] [-r REVIEWBOARD] [-t TESTING_DONE]
                               [-ta [TESTING_DONE_APPEND [TESTING_DONE_APPEND ...]]]
                               [-ch] [-p] [-o] [-rs]
                               [action]
        
        apache dev tool. Command line helper for frequent actions.
        
        positional arguments:
          action                action of the command. One of post-review, submit-
                                patch, commit and clean
        
        optional arguments:
          -h, --help            show this help message and exit
          -j [JIRA [JIRA ...]], --jira [JIRA [JIRA ...]]
                                JIRAs. provide as -j JIRA1 -j JIRA2... Mostly only one
                                option will be used, commit commandcan provide
                                multiple jira ids and commit all of them together.
          -ju JIRA_USERNAME, --jira-username JIRA_USERNAME
                                JIRA Username. If not provided, it will prompt and ask
                                the user.
          -jp JIRA_PASSWORD, --jira-password JIRA_PASSWORD
                                JIRA Password. If not provided, it will prompt and ask
                                the user.
          -ru REVIEWBOARD_USERNAME, --reviewboard-username REVIEWBOARD_USERNAME
                                Review Board Username. If not provided, it will prompt
                                and ask the user.
          -rp REVIEWBOARD_PASSWORD, --reviewboard-password REVIEWBOARD_PASSWORD
                                Review Board Password. If not provided, it will prompt
                                and ask the user.
          -b BRANCH, --branch BRANCH
                                Tracking branch to create diff against. Picks default
                                from .reviewboardrc file
          -s SUMMARY, --summary SUMMARY
                                Summary for the reviewboard. If not provided, jira
                                summary will be picked.
          -d DESCRIPTION, --description DESCRIPTION
                                Description for reviewboard. Defaults to description
                                on jira.
          -r REVIEWBOARD, --rb REVIEWBOARD
                                Review board that needs to be updated. Only needed if
                                you haven't created rb entry using this tool.
          -t TESTING_DONE, --testing-done TESTING_DONE
                                Text for the Testing Done section of the reviewboard.
                                Defaults to empty string.
          -ta [TESTING_DONE_APPEND [TESTING_DONE_APPEND ...]], --testing-done-append [TESTING_DONE_APPEND [TESTING_DONE_APPEND ...]]
                                Text to append to Testing Done section of the
                                reviewboard. Used to provide new testing done in
                                addition to old one already mentioned on rb
          -ch, --choose-patch   Whether Ask for which patch to commit. By default the
                                latest uploaded patch is picked for committing.
          -p, --publish         Whether to make the review request public
          -o, --open            Whether to open the review request in browser
          -rs, --require-ship-it
                                Whether to require Ship It! review before posting
                                patch from rb to jira. True by default.        
        
`action` can be `post-review`, `submit-patch`, `test-patch`, `commit`, `clean`,

It's expected that you run the command in the directory that contains `.reviewboardrc`. So I'd run the command inside `/path/to/clone/of/incubator-lens/`.

### Post review
You either provide a jira id in `-j`, or it tries to deduce jira id from your git branch. Other than jira id, it needs reviewboard id if a request already exists. You can either provide that, or let it deduce itself from the jira id. For that, it keeps a locally stored mapping. If not found in the mapping, it falls back to looking at the issue's comments if a reviewboard url is mentioned. So if not provided, not found in the local mapping and no comments on the issue mentioning this, it assumes a new review request needs to be created. Otherwise it will try and update an already existing review request. 

In any case, it first uploads the new diff to the review request. The diff will be generated using `git diff $BRANCH..HEAD`. `BRANCH` can be provided in arguments but defaults to the value of BRANCH in the `.reviewboardrc`. 

if `SUMMARY` is provided, it's chosen to be the review request's summary. If not, summary is updated only when it's blank in the review request(which will happen if a new request was created). If blank, summary of the issue is picked and copied in review request's summary. Similar logic applies to the description of the review request.

If `TESTING_DONE` is provided, the review request is updated with the new value. 

If `publish` flag is on, the review request is made public. The first time the review request is made public, a comment will be added on the issue mentioning the review request. 


### Submit patch
Submit patch -- like post review -- checks if a corresponding reviewboard entry exists. If yes, it takes patch from the review board entry. If not, it checks the diff using `git diff $BRANCH..HEAD`. If diff is small enough, takes patch from there. If not, it recommends you create a reviewboard entry and exits.

After it has patch, it adds it to the issue as attachment, marks it patch available and posts a comment on the jira. 

Just like post-review, it needs `-j` argument, but can deduce from current branch name. 

### Test patch
Takes latest patch from jira, applies it and runs `mvn clean install`. It's expected that this command takes care of 
all guidelines and test cases. So it's assumed that `mvn clean install` will only pass when the patch is 
commitable according to project guidelines. 

### Commit

Commits the given jira id. Checks whether it's patch available, if yes, gets the most recent diff. If there's a reviewboard entry, compares most recent diffs of both. proceeds only if same. Then applies the patch, commits the changes. Picks commit message if passed in the command. Otherwise it picks from reviewboard if exists. The last preference is to pick from jira summary. Commits, comments on jira, resolves the jira and pushes the commit. 

### Clean
Deletes branches for jiras resolved. cleans up local storage. Closes reviewboards corresponding to resolved jiras. 


## Optimal workflow for contributor
Keep your `$BRANCH` in sync with apache repo's `$BRANCH`. i.e. do not do any work on that branch. It shouldn't (ideally) matter whether you have forked the repo before cloning or not. Whenever you work on a jira, create a branch with the issue name(e.g. LENS-26) and work on that. 

git commits can be checkpoints(e.g. when you have to switch branch, you'll perform a checkpoint commit). So I've kept `committing` separate from `post-review`. Once you are sure you want to push a review request, do `apache-dev-tool post-review`. This will create the review request. You can open that, most of the fields will be already set. 

Generally when you create a review request, you get to see the diff and you decide some of the changes need rectifying. You will now browse through the diff of your review request (which is not published yet), make changes on your local, and once done, do a `git commit` followed by `apache-dev-tool post-review -p`. This will publish the request. You can provide `-d`, `-s`, `-t` as and when required. 

Another general assumption is that jira summary is the symptom of the problem. reviewboard summary can mention what is the actual change. So you'll provide summary once (anytime when you are doing post-review) and that will permanently become the summary of the review request.

Once you see that your review request is approved, you can do `apache-dev-tool submit-patch`. You can use this command also when you have made a very small change and directly want to submit patch to jira. 

For both of the commands, all changes you intend to send across must be committed. 


## Workflow for committer
have apache's remote cloned separately. To commit, just do 

    apache-dev-tool commit -j jira-id

The commit message will be picked for you from reviewboard summary or jira summary whichever exists first. The tool 
first commits and then issues a amend commit command which will let you modify the commit message. You can commit 
multiple jiras at once too. 
    
    apache-dev-tool commit -j jira-id1 -j jira-id2 ...

The jiras need to be `patch-available` to be eligible for committing. The patches will be picked, committed one by one, 
pushed to remote. Also the jiras will be marked resolved with a comment thanking the assignee(if the assignee is not you)

## Setting up a pre-commit job in apache jenkins

This script has a `test-patch` option which is ideal for a pre-commit job for an apache project. Apache lens is using 
this for its pre-commit job. See the configuration [here](https://builds.apache.org/view/PreCommit%20Builds/job/PreCommit-lens-Build/configure)
Look for `execute shell` in the config page. 