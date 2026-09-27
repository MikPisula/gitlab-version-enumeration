import re
import urllib.request
import argparse
import ssl
import json
from pathlib import Path

link_regex = re.compile(r'<link(.+)href="([/A-Za-z0-9\-_\.]+)"(.*)>')
script_regex = re.compile(r'<script(.+)src="([/A-Za-z0-9\-_\.]+)"(.*)>')

file_regexes = [link_regex, script_regex]

file_blacklist = [
    "opensearch.xml",
    "manifest.json"
]

def find_hashed_strings(sign_in_page):
    found_hashed_strings = []

    for file_regex in file_regexes:
        matches = file_regex.finditer(sign_in_page)

        for match in matches:
            path_group = match.group(2)
            filename = path_group.split("/")[-1]

            if not filename in file_blacklist:
                found_hashed_strings.append(filename)

    return found_hashed_strings

def main():
    parser = argparse.ArgumentParser(description='Identifies remote GitLab CE version based on sign in page hashed resource strings')
    parser.add_argument("server", help="Remote GitLab server host")
    parser.add_argument("-k", "--insecure", action='store_true')
    parser.add_argument('-v', "--verbose", action='store_true')

    args = parser.parse_args()

    stripped_server = args.server.rstrip("/")

    if stripped_server.endswith("/users/sign_in"):
        server = stripped_server
    else:
        server = f'{stripped_server}/users/sign_in'

    # default to http:// unless specified in url
    if not args.server.startswith("http"):
        server = f"http://{server}"

    if args.insecure:
        ssl_context = ssl._create_unverified_context()
    else:
        ssl_context = ssl.create_default_context()

    print("Gitlab CE Version enumeration script")

    print(f"[+] Fetching '{server}'")

    try:
        with urllib.request.urlopen(server, context=ssl_context) as sign_in_response:
            status_code = sign_in_response.getcode()

            if status_code == 200:
                print(f'[+] Received status code 200')
            else:
                print(f"[-] Received status code {status_code}")
                exit(1)

            sign_in_page = sign_in_response.read().decode('utf-8')

    except urllib.error.HTTPError as e:
        print(f"[-] Received status code {e.code}")
        exit(1)
    except Exception as e:
        print(f'[-] Failed to fetch server sign in page: {e}')
        exit(1)

    hashed_strings = find_hashed_strings(sign_in_page)
    print(f"[+] Found {len(hashed_strings)} hashed asset strings in response")

    if args.verbose:
        print(f"[*] Hashed strings:\n - {'\n - '.join(hashed_strings)}")

    parent_dir = Path(__file__).parent

    candidate_known_hashes = [
        parent_dir / "gitlab-file-hashes.json",
        parent_dir / "data" / "gitlab-file-hashes.json"
    ]

    known_file_hashes_path = None

    for candidate in candidate_known_hashes:
        if candidate.exists():
            known_file_hashes_path = candidate
            break

    if known_file_hashes_path is None:
        print("[-] Failed to find 'gitlab-file-hashes.json'. Please ensure to download it from https://raw.githubusercontent.com/MikPisula/gitlab-version-enumeration/main/data/gitlab-file-hashes.json")
        exit(1)

    with known_file_hashes_path.open('r') as known_file_hashes_fp:
        known_file_hashes = json.load(known_file_hashes_fp)

    print("[+] Loaded known resource hash file")

    # matching_files: gitlab_version
    candidate_releases = {}
    
    for gitlab_release, gitlab_release_hashes in known_file_hashes.items():
        release_matches = 0

        for hashed_string in hashed_strings:
            if hashed_string in gitlab_release_hashes:
                release_matches += 1

        if release_matches in candidate_releases:
            candidate_releases[release_matches].append(gitlab_release)
        else:
            candidate_releases[release_matches] = [gitlab_release]

    sorted_candidate_releases = {k: v for k, v in sorted(candidate_releases.items(), key=lambda item: item[0], reverse=True)}
    (match_count, matching_releases), *irrelevant = sorted_candidate_releases.items()

    if match_count == 0:
        print("[-] Did not find any matching GitLab CE release")
        exit(1)

    if len(matching_releases) == 1:
        print(f"[+] Found a single matching Gitlab CE release: {matching_releases[0]}")
    else:
        print(f"[+] Found multiple matching GitLab CE releases: {', '.join(matching_releases)}")

    if args.verbose:
        print(f"[*] Matching release hashed strings:\n - {'\n - '.join(known_file_hashes[matching_releases[0]])}")

if __name__ == "__main__":
    main()
