from setuptools import setup

setup(
    name='patsy',
    version='0.2',
    url='https://github.com/sral/patsy',
    license='GPLv2',
    author='Lars Djerf',
    author_email='lars.djerf@gmail.com',
    description='Patsy - track and scrobble (Last.fm) logs',
    install_requires=["pyinotify", "requests"],
    packages=["patsy"],
    entry_points={
        "console_scripts": ["patsy = patsy.patsy:main_func"]
    })
