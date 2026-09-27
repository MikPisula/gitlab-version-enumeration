import re
import json
from pathlib import Path

data_path = Path(__file__).parent.parent.joinpath("data")
sign_in_pages = data_path.joinpath("sign_in_pages")

link_regex = re.compile(r'<link(.+)href="([/A-Za-z0-9\-_\.]+)"(.*)>')
script_regex = re.compile(r'<script(.+)src="([/A-Za-z0-9\-_\.]+)"(.*)>')

file_regexes = [link_regex, script_regex]

file_blacklist = [
    "opensearch.xml",
    "manifest.json"
]

def version_key(version):
    return tuple(int(part) for part in version.split('.'))

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
    gitlab_hash_set = {}

    for sign_in_page_path in sign_in_pages.glob("*.html"):
        gitlab_version = sign_in_page_path.stem

        with sign_in_page_path.open('r') as sign_in_page_fp:
            sign_in_page = sign_in_page_fp.read()

        gitlab_hash_set[gitlab_version] = find_hashed_strings(sign_in_page)

    gitlab_hash_set = dict(sorted(gitlab_hash_set.items(), key=lambda kv: version_key(kv[0])))

    hash_set_path = data_path.joinpath("gitlab-file-hashes.json")

    with hash_set_path.open('w') as hash_set_fp:
        json.dump(gitlab_hash_set, hash_set_fp, indent=4)

if __name__ == "__main__":
    main()