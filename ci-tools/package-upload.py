"""upload the packages created by CI to Anaconda cloud
"""
import os
import sys
import glob
import subprocess
import traceback

token = os.getenv('ANACONDA_TOKEN')

def upload_anaconda():
    file_glob = "pyswashes-*.tar.bz2"

    # set the path depending on the CI environment
    if os.environ.get('APPVEYOR'):
        python_arch = os.environ.get('PYTHON_ARCH')
        path_glob = "C:\conda\conda-bld\win-{}\{}".format(python_arch,file_glob)
    elif os.environ.get('CIRCLECI'):
        path_glob = "/opt/conda/conda-bld/linux-64/{}".format(file_glob)

    cmd = ['anaconda', '-t', token, 'upload', '--force']
    packages = glob.glob(path_glob, recursive=True)
    cmd.extend(packages)
    return cmd


def upload_pypi():
    pass


def main():
    # parse cli and call adequate function
    pkg_type = sys.argv[1]
    if pkg_type == 'conda':
        cmd = upload_anaconda()
    elif pkg_type == 'pypi':
        cmd = upload_pypi()
    # execute cmd
    subprocess.check_call(cmd)


if __name__ == "__main__":
    sys.exit(main())
