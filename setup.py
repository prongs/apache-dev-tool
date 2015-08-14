from distutils.core import setup

with open("./requirements.txt") as requirements_file:
    requirements = requirements_file.read().strip().split("\n")
setup(
    name='apache_dev_tool',
    packages=['apache_dev_tool'],  # this must be the same as the name above
    version='0.1',
    description='Tool for apache contributors and committers.',
    author='Rajat Khandelwal',
    author_email='rajatgupta59@gmail.com',
    url='https://github.com/prongs/apache_dev_tool',  # use the URL to the github repo
    download_url='https://github.com/prongs/apache_dev_tool/tarball/0.1',  # I'll explain this in a second
    keywords=['apache', 'open-source', 'reviewboard', 'jira', 'test-patch'],  # arbitrary keywords
    classifiers=[],
    install_requires=requirements,
    entry_points = {
        'console_scripts': ['apache-dev-tool=apache_dev_tool.apache_dev_tool:main'],
    }
)
