import json
from pathlib import Path

from dockerhub_api.auth import get_client

api = get_client()  # reads DOCKERHUB_URL / DOCKER_HUB_USER / DOCKER_HUB_TOKEN

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "gitlab-ce-tags.json"

tags = []
page = 1
while True:
    envelope = api.get_repository_tags(
        namespace="gitlab", repository="gitlab-ce", page=page, page_size=100
    )
    data = envelope["data"]
    results = data.get("results") or []
    if not results:
        break
    tags.extend(results)
    if not data.get("next"):
        break
    page += 1

tags.sort(key=lambda t: t.get("name") or "")

OUTPUT_PATH.write_text(json.dumps(tags, indent=2))
print(f"Wrote {len(tags)} tags to {OUTPUT_PATH}")
