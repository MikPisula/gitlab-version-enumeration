import json
from pathlib import Path

data_path = Path(__file__).parent.parent.joinpath("data")
tags_path = data_path.joinpath("gitlab-ce-tags.json")

with tags_path.open('r') as tags_fp:
    data = json.load(tags_fp)

relevant_releases = {}

for tag in data:
    tag_name = tag['name']

    if not 'rc' in tag_name and not tag_name in ('latest', 'nightly'):
        major,minor,fix = tag_name.split("-ce")[0].split('.')

        if int(major) >= 16:
            release = f"{major}.{minor}.{fix}"
        else:
            release = f"{major}.{minor}"

        if not release in relevant_releases:
            relevant_releases[release] = tag_name


print(f"Filtered all gitlab-ce tags down to: {len(relevant_releases)}")
relevant_releases_path = data_path.joinpath("relevant-gitlab-ce-tags.json")

with relevant_releases_path.open('w') as relevant_releases_fp:
    json.dump(relevant_releases, relevant_releases_fp, indent=4)

print(f"Saved to {relevant_releases_path}")