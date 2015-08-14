from distutils.core import setup

setup(
    name='apache_dev_tool',
    packages=['apache_dev_tool'],  # this must be the same as the name above
    version='0.2',
    description='Tool for apache contributors and committers.',
    author='Rajat Khandelwal',
    author_email='rajatgupta59@gmail.com',
    url='https://github.com/prongs/apache_dev_tool',  # use the URL to the github repo
    download_url='https://github.com/prongs/apache-dev-tool/tarball/0.2',  # I'll explain this in a second
    keywords=['apache', 'open-source', 'reviewboard', 'jira', 'test-patch'],  # arbitrary keywords
    classifiers=[],
    install_requires=[
        "argparse>=1.3.0",
        "jira>=0.47",
        "beautifulsoup4>=4.3.2",
        "RBTools>=0.7.4",
        "requests>=2.7.0",
    ],
    entry_points={
        'console_scripts': ['apache-dev-tool=apache_dev_tool.apache_dev_tool:main'],
    }
)
