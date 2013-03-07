from setuptools import setup, find_packages

setup(
    name = "mcstatus_widget",
    version = "1.0",
    author = "Adam Strauch",
    author_email = "cx@initd.cz",
    description = ("Library for querying minecraft status. It can generate widgets too."),
    license = "BSD",
    keywords = "minecraft",
    url = "https://github.com/creckx/mcstatus",
    long_description="Library for querying minecraft status. It can generate widgets too.",
    packages = find_packages(exclude=['ez_setup', 'examples', 'tests']),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
        ],
    package_data={'mcstatus': [
        'DejaVuSans.ttf', 'PT_Sans-Web-Regular.ttf', 'bg/*', 'script.ini',
    ]},
    entry_points="""
    [console_scripts]
    mcstatus_cli = mcstatus.cli:main
    mcstatus_widget = mcstatus.cli_widget:main
    mcstatus_datamining = mcstatus.datamining:main
    """
)
