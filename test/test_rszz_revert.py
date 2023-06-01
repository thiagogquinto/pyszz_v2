# include project root in sys path
import sys
import os
# insert at 1, 0 is the script path (or '' in REPL)
sys.path.insert(1, os.path.abspath("../"))

import argparse
import json
import logging as log
import os
from time import time as ts
from typing import Dict
import yaml
import dateparser
from szz.r_szz import RSZZ
from szz.util.check_requirements import check_requirements

log.basicConfig(level=log.INFO, format='%(asctime)s :: %(funcName)s - %(levelname)s :: %(message)s')
log.getLogger('pydriller').setLevel(log.WARNING)

# ierton/xkb-switch- fix_commit_hash=5d8cee18015b9a64aa3e06a81802f8186a99cc02
oracle = ['42abcc0da1c7f1062d069349edf90aa3b8832ca4']


def main(input_json: str, out_json: str, conf: Dict, repos_dir: str):
    with open(input_json, 'r') as in_file:
        bugfix_commits = json.loads(in_file.read())

    tot = len(bugfix_commits)
    for i, commit in enumerate(bugfix_commits):
        bug_inducing_commits = set()
        repo_name = commit['repo_name']
        repo_url = f'https://test:test@github.com/{repo_name}.git'  # using test:test as git login to skip private repos during clone
        fix_commit = commit['fix_commit_hash']

        log.info(f'{i + 1} of {tot}: {repo_name} {fix_commit}')

        szz_name = conf['szz_name']
        if szz_name == 'r':
            r_szz = RSZZ(repo_full_name=repo_name, repo_url=repo_url, repos_dir=repos_dir)
            imp_files = r_szz.get_impacted_files(fix_commit_hash=fix_commit, file_ext_to_parse=conf.get('file_ext_to_parse'), only_deleted_lines=conf.get('only_deleted_lines', True))
            # settings for the commit used as test case
            bug_inducing_commits = r_szz.find_bic(fix_commit_hash=fix_commit,
                                      impacted_files=imp_files,
                                      ignore_revs_file_path=conf.get('ignore_revs_file_path'),
                                      max_change_size=conf.get('max_change_size'),
                                      detect_move_from_other_files=conf.get('detect_move_from_other_files'),
                                      detect_move_within_file=conf.get('detect_move_within_file'),
                                      filter_revert_commits=conf.get('filter_revert_commits'))
            log.info(bug_inducing_commits)
        else:
            log.info(f'SZZ implementation not found: {szz_name}')
            exit(-3)

        log.info(f"result: {bug_inducing_commits}")
        found_bic = [bic.hexsha for bic in bug_inducing_commits if bic]
        assert set(found_bic) == set(oracle)

    log.info("+++ Test passed +++")


if __name__ == "__main__":
    check_requirements()

    parser = argparse.ArgumentParser(description='USAGE: python main.py <bugfix_commits.json> <conf_file path> <repos_directory(optional)>\n* If <repos_directory> is not set, pyszz will download each repository')
    parser.add_argument('input_json', type=str, help='/path/to/bug-fixes.json')
    parser.add_argument('conf_file', type=str, help='/path/to/configuration-file.yml')
    parser.add_argument('repos_dir', type=str, nargs='?', help='/path/to/repo-directory')
    args = parser.parse_args()

    if not os.path.isfile(args.input_json):
        log.error('invalid input json')
        exit(-2)
    if not os.path.isfile(args.conf_file):
        log.error('invalid conf file')
        exit(-2)

    with open(args.conf_file, 'r') as f:
        conf = yaml.safe_load(f)

    log.info(f"parsed conf yml: {conf}")
    szz_name = conf['szz_name']

    out_dir = 'out'
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    out_json = os.path.join(out_dir, f'bic_{szz_name}_{int(ts())}.json')

    if not szz_name:
        log.error('The configuration file does not define the SZZ name. Please, fix.')
        exit(-3)

    log.info(f'Launching {szz_name}-szz')

    main(args.input_json, out_json, conf, args.repos_dir)
