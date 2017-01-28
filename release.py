import sys
import tempfile
import os
import shutil
import subprocess

def main(args):
    if len(args) <= 2:
        print(
            "Must provide a version (e.g., 0.0.1-alpha) and the package name to {}".format(args[0]))
        return
    project = args[1]
    version = args[2]
    package_directory = project
    write_version_to_file(version)
    update_main_package_version(package_directory, version)
    commit_to_vcs_with_version_changes()
    tag_vcs_commit_with_version(version)

def commit_to_vcs_with_version_changes():
    call_with_prompt_on_error('git commit -a', "add commit with version changes")

def call_with_prompt_on_error(command, action):
    try:
        subprocess.check_call(command.split(" "))
        return False
    except subprocess.CalledProcessError:
        if yes_no_prompt("Failed to {} with `{}`. Exit?".format(action, command)):
            sys.exit()
        return True

def yes_no_prompt(prompt):
    print(prompt+ "(Y/n)")
    line = sys.stdin.readline()
    if line.lower().startswith('n'):
        return False
    return True

def update_main_package_version(package_directory, version):
    path = os.path.join(package_directory, '__init__.py')
    _, temppath = tempfile.mkstemp()
    temp = open(temppath, 'w')
    with open(path, 'r') as f:
        line = f.readline()
        while len(line) > 0:
            if line.startswith('__version__'):
                print("updating version")
                line = '__version__ = "{}"\n'.format(version)
            temp.write(line)
            line = f.readline()
    temp.close()
    shutil.copy2(temppath, path)

def write_version_to_file(version):
    with open("version.txt", "w") as f:
        f.write(version)
        f.flush()

def tag_vcs_commit_with_version(version):
    vtag_name = "v" + version
    if call_with_prompt_on_error("git tag --annotate " + vtag_name, "add VCS tag"):
        if yes_no_prompt("force tag creation?"):
            if call_with_prompt_on_error("git tag --force --annotate " + vtag_name, "add VCS tag"):
                print("Coluldn't append tag to commit")


if __name__ == '__main__':
    main(sys.argv)
