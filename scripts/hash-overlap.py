import json
from itertools import combinations
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HASHES_PATH = DATA_DIR / "gitlab-file-hashes.json"


def version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def jaccard(a: set, b: set) -> float:
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def main() -> None:
    raw = json.loads(HASHES_PATH.read_text())
    file_sets = {version: set(files) for version, files in raw.items()}
    versions = sorted(file_sets, key=version_key)

    print(f"{len(versions)} versions loaded from {HASHES_PATH.name}\n")

    print("adjacent-version overlap (sorted by version)")
    print(f"{'from':<10} {'to':<10} {'jaccard':>8} {'shared':>7} {'new':>5} {'gone':>5}")
    adjacent_scores = []
    for prev, curr in zip(versions, versions[1:]):
        a, b = file_sets[prev], file_sets[curr]
        score = jaccard(a, b)
        adjacent_scores.append(score)
        print(
            f"{prev:<10} {curr:<10} {score:>7.1%} {len(a & b):>7} "
            f"{len(b - a):>5} {len(a - b):>5}"
        )

    if adjacent_scores:
        avg = sum(adjacent_scores) / len(adjacent_scores)
        print(f"\naverage adjacent jaccard: {avg:.1%}")
        print(f"min: {min(adjacent_scores):.1%}   max: {max(adjacent_scores):.1%}")

    # Global duplicate detection: versions with byte-identical fingerprint sets
    # anywhere in the dataset, not just neighbors.
    signature_groups: dict[frozenset, list[str]] = {}
    for version, files in file_sets.items():
        signature_groups.setdefault(frozenset(files), []).append(version)

    duplicate_clusters = [vs for vs in signature_groups.values() if len(vs) > 1]
    print(f"\ndistinct fingerprints: {len(signature_groups)} across {len(versions)} versions")
    if duplicate_clusters:
        print("versions sharing an identical fingerprint (fully indistinguishable):")
        for cluster in duplicate_clusters:
            print(f"  {sorted(cluster, key=version_key)}")
    else:
        print("no two versions share a fully identical fingerprint")

    # Highest-similarity non-adjacent pairs, in case near-duplicates exist
    # outside of consecutive versions too.
    near_duplicates = []
    for v1, v2 in combinations(versions, 2):
        score = jaccard(file_sets[v1], file_sets[v2])
        if score >= 0.9:
            near_duplicates.append((score, v1, v2))
    near_duplicates.sort(reverse=True)
    if near_duplicates:
        print(f"\npairs with >=90% overlap ({len(near_duplicates)} total):")
        for score, v1, v2 in near_duplicates[:20]:
            print(f"  {v1:<10} {v2:<10} {score:.1%}")


if __name__ == "__main__":
    main()
