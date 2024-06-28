import argparse
import json
import logging as log
import os
from time import time as ts
import shutil

import dateparser
import yaml
from typing import Dict
from szz.ag_szz import AGSZZ
from szz.aszz.a_szz import ASZZ
from szz.b_szz import BaseSZZ
from szz.util.check_requirements import check_requirements
from szz.dfszz.df_szz import DFSZZ
from szz.l_szz import LSZZ
from szz.ma_szz import MASZZ, DetectLineMoved
from szz.r_szz import RSZZ
from szz.ra_szz import RASZZ
from szz.pd_szz import PyDrillerSZZ
from szz.common.issue_date import parse_issue_date
from pathlib import Path
import random

log.basicConfig(level=log.INFO, format='%(asctime)s :: %(funcName)s - %(levelname)s :: %(message)s')
log.getLogger('pydriller').setLevel(log.WARNING)

TIME_LIMIT = 5 * 3600 + 30 * 60  # 5 hours + 30 minutes

if not os.path.exists('repos_dir'):
    os.makedirs('repos_dir')

def clear_directory(directory):
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isdir(file_path):
            shutil.rmtree(file_path)
        else:
            os.remove(file_path)

def clone_repo(repo_path: str):
    os.system(f"git clone https://github.com/{repo_path}.git repos_dir/{repo_path}")

def main(input_json: str, out_json: str, conf: Dict, repos_dir: str):

    start_time = ts()

    with open(input_json, 'r') as in_file:
        bugfix_commits = json.loads(in_file.read())

    previous_repo_name = None
    tot = len(bugfix_commits)
    for i, commit in enumerate(bugfix_commits):

        if ts() - start_time > TIME_LIMIT:
            break

        bug_inducing_commits = set()
        repo_name = commit['repo_name']

        if previous_repo_name != repo_name:
            if previous_repo_name is not None:
                clear_directory('repos_dir')
            log.info(f"Cloning repository {repo_name}")
            clone_repo(repo_name)
            previous_repo_name = repo_name

        repo_url = f'https://test:test@github.com/{repo_name}.git'  # using test:test as git login to skip private repos during clone
        fix_commit = commit['Target Commit SHA']

        fix_commit_target = commit['Target Commit SHA']
        if fix_commit_target is None:
            fix_commit_target = ''.join(random.choices('0123456789abcdef', k=40))

        fix_commit_closest = commit['Closest Commit SHA']
        if fix_commit_closest is None:
            fix_commit_closest = ''.join(random.choices('0123456789abcdef', k=40)) 

        issue_date = None
        if conf.get('issue_date_filter', None):
            issue_date = parse_issue_date(commit)
        
        szz_name = conf['szz_name']
        if szz_name == 'b':
            b_szz = BaseSZZ(repo_full_name=repo_name, repo_url=repo_url, repos_dir=repos_dir)
            imp_files = b_szz.get_impacted_files(fix_commit_hash=fix_commit, file_ext_to_parse=conf.get('file_ext_to_parse'), only_deleted_lines=True)
            bug_inducing_commits = b_szz.find_bic(fix_commit_hash=fix_commit,
                                        impacted_files=imp_files,
                                        issue_date_filter=conf.get('issue_date_filter'),
                                        issue_date=issue_date)
        elif szz_name == 'ag':
            ag_szz = AGSZZ(repo_full_name=repo_name, repo_url=repo_url, repos_dir=repos_dir)
            imp_files = ag_szz.get_impacted_files(fix_commit_hash=fix_commit, file_ext_to_parse=conf.get('file_ext_to_parse'), only_deleted_lines=True)
            bug_inducing_commits = ag_szz.find_bic(fix_commit_hash=fix_commit,
                                        impacted_files=imp_files,
                                        max_change_size=conf.get('max_change_size'),
                                        issue_date_filter=conf.get('issue_date_filter'),
                                        issue_date=issue_date)
        elif szz_name == 'ma':
            ma_szz = MASZZ(repo_full_name=repo_name, repo_url=repo_url, repos_dir=repos_dir)
            imp_files = ma_szz.get_impacted_files(fix_commit_hash=fix_commit, file_ext_to_parse=conf.get('file_ext_to_parse'), only_deleted_lines=True)
            bug_inducing_commits = ma_szz.find_bic(fix_commit_hash=fix_commit,
                                        impacted_files=imp_files,
                                        max_change_size=conf.get('max_change_size'),
                                        detect_move_from_other_files=DetectLineMoved(conf.get('detect_move_from_other_files')),
                                        issue_date_filter=conf.get('issue_date_filter'),
                                        issue_date=issue_date,
                                        filter_revert_commits=conf.get('filter_revert_commits', False))
        elif szz_name == 'r':
            r_szz = RSZZ(repo_full_name=repo_name, repo_url=repo_url, repos_dir=repos_dir)
            

            imp_files_target = r_szz.get_impacted_files(fix_commit_hash=fix_commit_target, file_ext_to_parse=conf.get('file_ext_to_parse'), only_deleted_lines=True)
            imp_files_closest = r_szz.get_impacted_files(fix_commit_hash=fix_commit_closest, file_ext_to_parse=conf.get('file_ext_to_parse'), only_deleted_lines=True)
            if imp_files == [] and imp_files_closest == []:
                bug_inducing_commits_target = '-'
                bug_inducing_commits_closest = '-'
            else:
                if imp_files_target == [] and imp_files_closest != []:
                    bug_inducing_commits_target = '-'
                    bug_inducing_commits_closest = r_szz.find_bic(fix_commit_hash=fix_commit_closest,
                                        impacted_files=imp_files_closest,
                                        max_change_size=conf.get('max_change_size'),
                                        detect_move_from_other_files=DetectLineMoved(conf.get('detect_move_from_other_files')),
                                        issue_date_filter=conf.get('issue_date_filter'),
                                        issue_date=issue_date,
                                        filter_revert_commits=conf.get('filter_revert_commits', False))
                elif imp_files_target != [] and imp_files_closest == []:
                    bug_inducing_commits_target = r_szz.find_bic(fix_commit_hash=fix_commit_target,
                                        impacted_files=imp_files_target,
                                        max_change_size=conf.get('max_change_size'),
                                        detect_move_from_other_files=DetectLineMoved(conf.get('detect_move_from_other_files')),
                                        issue_date_filter=conf.get('issue_date_filter'),
                                        issue_date=issue_date,
                                        filter_revert_commits=conf.get('filter_revert_commits', False))
                    bug_inducing_commits_closest = '-'
        elif szz_name == 'l':
            l_szz = LSZZ(repo_full_name=repo_name, repo_url=repo_url, repos_dir=repos_dir)
            imp_files = l_szz.get_impacted_files(fix_commit_hash=fix_commit, file_ext_to_parse=conf.get('file_ext_to_parse'), only_deleted_lines=True)
            bug_inducing_commits = l_szz.find_bic(fix_commit_hash=fix_commit,
                                        impacted_files=imp_files,
                                        max_change_size=conf.get('max_change_size'),
                                        detect_move_from_other_files=DetectLineMoved(conf.get('detect_move_from_other_files')),
                                        issue_date_filter=conf.get('issue_date_filter'),
                                        issue_date=issue_date,
                                        filter_revert_commits=conf.get('filter_revert_commits', False))
        elif szz_name == 'ra':
            ra_szz = RASZZ(repo_full_name=repo_name, repo_url=repo_url, repos_dir=repos_dir)
            imp_files = ra_szz.get_impacted_files(fix_commit_hash=fix_commit, file_ext_to_parse=conf.get('file_ext_to_parse'), only_deleted_lines=True)
            bug_inducing_commits = ra_szz.find_bic(fix_commit_hash=fix_commit,
                                        impacted_files=imp_files,
                                        max_change_size=conf.get('max_change_size'),
                                        detect_move_from_other_files=DetectLineMoved(conf.get('detect_move_from_other_files')),
                                        issue_date_filter=conf.get('issue_date_filter'),
                                        issue_date=issue_date,
                                        filter_revert_commits=conf.get('filter_revert_commits', False))
        elif szz_name == 'pd':
            pd_szz = PyDrillerSZZ(repo_full_name=repo_name, repo_url=repo_url, repos_dir=repos_dir)
            imp_files = pd_szz.get_impacted_files(fix_commit_hash=fix_commit, file_ext_to_parse=conf.get('file_ext_to_parse'), only_deleted_lines=True)
            bug_inducing_commits = pd_szz.find_bic(fix_commit_hash=fix_commit,
                                                   impacted_files=imp_files,
                                                   issue_date_filter=conf.get('issue_date_filter'),
                                                   issue_date=issue_date)
        elif szz_name == 'a':
            a_szz = ASZZ(repo_full_name=repo_name, repo_url=repo_url, repos_dir=repos_dir)
            bug_inducing_commits = a_szz.start(fix_commit_hash=fix_commit, commit_issue_date=issue_date, **conf)

        elif szz_name == 'df':
            df_szz = DFSZZ(repo_full_name=repo_name, repo_url=repo_url, repos_dir=repos_dir)
            bug_inducing_commits = df_szz.start(fix_commit_hash=fix_commit, commit_issue_date=issue_date, **conf)

        else:
            log.info(f'SZZ implementation not found: {szz_name}')
            exit(-3)

        log.info(f"result: {bug_inducing_commits}")

        if bug_inducing_commits_target == '-':
            bugfix_commits[i]["target_inducing_commit_hash_pyszz"] = '-'
            bugfix_commits[i]["target_inducing_commit_hash_pyszz"] = [bic.hexsha for bic in bug_inducing_commits if bic]

        if bug_inducing_commits_closest == '-':
            bugfix_commits[i]["closest_inducing_commit_hash_pyszz"] = '-'
            bugfix_commits[i]["closest_inducing_commit_hash_pyszz"] = [bic.hexsha for bic in bug_inducing_commits if bic]
            
    with open(out_json, 'w') as out:
        json.dump(bugfix_commits, out)

    log.info(f"results saved in {out_json}")
    log.info("+++ DONE +++")


if __name__ == "__main__":
    check_requirements()

    parser = argparse.ArgumentParser(description='USAGE: python main.py <bugfix_commits.json> <conf_file path> <repos_directory(optional)>\n* If <repos_directory> is not set, pyszz will download each repository')
    parser.add_argument('input_json', type=str, help='/path/to/bug-fixes.json')
    parser.add_argument('conf_file', type=str, help='/path/to/configuration-file.yml')
    parser.add_argument('repos_dir', type=str, nargs='?', help='/path/to/repo-directory')
    args = parser.parse_args()

    if not os.path.isfile(args.input_json):
        print(args.input_json)
        os.system("pwd")
        log.error('invalid input json')
        exit(-2)
    if not os.path.isfile(args.conf_file):
        log.error('invalid conf file')
        exit(-2)

    with open(args.conf_file, 'r') as f:
        conf = yaml.safe_load(f)

    log.info(f"parsed conf yml '{args.conf_file}': {conf}")
    szz_name = conf['szz_name']

    out_dir = 'out'
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    conf_file_name = Path(args.conf_file).name.split('.')[0]
    out_json = os.path.join(out_dir, 'bics.json')

    if not szz_name:
        log.error('The configuration file does not define the SZZ name. Please, fix.')
        exit(-3)

    log.info(f'Launching {szz_name}-szz')

    main(args.input_json, out_json, conf, args.repos_dir)
