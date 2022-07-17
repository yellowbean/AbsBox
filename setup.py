from distutils.core import setup
from distutils import util
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

if __name__ == "__main__":
    local = util.convert_path('absbox/local')
    setup(
        name = 'AbsBox',
        package_dir = {
            'absbox':'absbox',
            'absbox.local':local
        },
        packages = ['absbox','absbox.local'],
        version = '0.1.1.1',
        license='Apache',
        description = 'an analytical library for cashflow modeling on ABS/MBS products',
        long_description = long_description,
        long_description_content_type='text/markdown',
        author = 'xiaoyu,zhang',
        author_email = 'always.zhang@gmail.com',
        url = 'https://github.com/yellowbean/PyABS',
        download_url = 'https://github.com/yellowbean/PyABS/archive/refs/tags/pre-release.tar.gz',
        keywords = ['MBS', 'ABS', 'Modelling','Structured Finance','Cashflow'],
        install_requires=[
            'requests',
            'pandas',
        ],
        classifiers=[
            'Development Status :: 3 - Alpha',
            'Intended Audience :: Developers',
            'Intended Audience :: Financial and Insurance Industry',
            'Topic :: Software Development :: Build Tools',
            'License :: OSI Approved :: MIT License',
            'Programming Language :: Python :: 3.10',
        ],
    )