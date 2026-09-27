import json
import subprocess
import time
from pathlib import Path

import requests

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RELEASES_PATH = DATA_DIR / "relevant-gitlab-ce-tags.json"
OUT_DIR = DATA_DIR / "sign_in_pages"
MANIFEST_PATH = DATA_DIR / "sign_in_pages_manifest.json"

CONTAINER_NAME = "gitlab-version-probe"
SIGN_IN_URL = "http://localhost:80/users/sign_in"
POLL_INTERVAL_SECONDS = 5
READY_TIMEOUT_SECONDS = 600
DELETE_IMAGE_AFTER_USE = True

OUT_DIR.mkdir(parents=True, exist_ok=True)


def release_sort_key(release: str) -> tuple[int, ...]:
    return tuple(int(part) for part in release.split("."))


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def remove_existing_container() -> None:
    run(["docker", "rm", "-f", CONTAINER_NAME])


def container_is_running() -> bool:
    result = run(
        ["docker", "inspect", "-f", "{{.State.Running}}", CONTAINER_NAME]
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def container_logs_tail(chars: int = 4000) -> str:
    result = run(["docker", "logs", "--tail", "200", CONTAINER_NAME])
    combined = (result.stdout or "") + (result.stderr or "")
    return combined[-chars:]


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text())
    return {}


def save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))


def process_release(release: str, tag: str, manifest: dict) -> None:
    out_file = OUT_DIR / f"{release}.html"
    if out_file.exists():
        print(f"[{release}] already captured, skipping")
        return

    image = f"gitlab/gitlab-ce:{tag}"
    print(f"[{release}] pulling {image}")
    started_at = time.time()
    entry = {"tag": tag, "image": image}

    pull = run(["docker", "pull", image])
    if pull.returncode != 0:
        entry.update(status="failed", error="pull failed", detail=pull.stderr[-2000:])
        manifest[release] = entry
        save_manifest(manifest)
        print(f"[{release}] pull failed")
        return

    remove_existing_container()
    try:
        run_result = run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                CONTAINER_NAME,
                "--shm-size",
                "256m",
                "-p",
                "80:80",
                "-e",
                "GITLAB_OMNIBUS_CONFIG=external_url 'http://localhost'",
                image,
            ]
        )
        if run_result.returncode != 0:
            entry.update(
                status="failed", error="run failed", detail=run_result.stderr[-2000:]
            )
            manifest[release] = entry
            save_manifest(manifest)
            print(f"[{release}] container failed to start")
            return

        print(f"[{release}] waiting for /users/sign_in to come up (timeout {READY_TIMEOUT_SECONDS}s)")
        deadline = time.time() + READY_TIMEOUT_SECONDS
        status = "timeout"
        http_status = None
        while time.time() < deadline:
            if not container_is_running():
                status = "container_exited"
                entry["detail"] = container_logs_tail()
                break
            try:
                resp = requests.get(SIGN_IN_URL, timeout=5)
                http_status = resp.status_code
                if resp.status_code == 200:
                    out_file.write_text(resp.text)
                    status = "ok"
                    break
            except requests.RequestException:
                pass
            time.sleep(POLL_INTERVAL_SECONDS)

        elapsed = round(time.time() - started_at, 1)
        entry.update(status=status, http_status=http_status, elapsed_seconds=elapsed)
        manifest[release] = entry
        save_manifest(manifest)
        print(f"[{release}] {status} ({elapsed}s)")
    finally:
        cleanup(image)


def cleanup(image: str) -> None:
    run(["docker", "stop", CONTAINER_NAME])
    run(["docker", "rm", CONTAINER_NAME])
    if DELETE_IMAGE_AFTER_USE:
        run(["docker", "rmi", image])


def main() -> None:
    releases = json.loads(RELEASES_PATH.read_text())
    manifest = load_manifest()

    try:
        for release in sorted(releases, key=release_sort_key):
            process_release(release, releases[release], manifest)
    except KeyboardInterrupt:
        print("\ninterrupted — docker container/image for the in-progress release cleaned up")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
