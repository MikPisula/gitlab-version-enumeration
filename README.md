# Gitlab Version Enumeration

This repository contains code that allows cybersecurity professionals to identify the GitLab CE version running on a remote host based only on the
frontend stylesheet/javascript/image hashes contained in the GitLab sign-in page.

This code is released under the 0BSD license, and can be used/copied freely without any major restrictions. As such, even attribution is not required (although it would be appreciated).

## Quick start
```bash
# download script itself alongside the known hash dataset
wget https://raw.githubusercontent.com/MikPisula/gitlab-version-enumeration/main/enumerate-gitlab-version.py
wget https://raw.githubusercontent.com/MikPisula/gitlab-version-enumeration/main/data/gitlab-file-hashes.json

# script fetches sign-in page on its own
python enumerate-gitlab-version.py --server http://localhost:80/

# script uses pre-downloaded sign-in page (useful for WAF/CDN bypassing)
python enumerate-gitlab-version.py --file sign_in.html
```

## How this works

The GitLab sign-in page contains hashed resource files, which is rather common in most modern web frameworks:

```html
<link rel="apple-touch-icon" type="image/x-icon" href="/assets/touch-icon-iphone-5a9cee0e8a51212e70b90c87c12f382c428870c0ff67d1eb034d884b78d2dae7.png" />
<link rel="apple-touch-icon" type="image/x-icon" href="/assets/touch-icon-ipad-a6eec6aeb9da138e507593b464fdac213047e49d3093fc30e90d9a995df83ba3.png" sizes="76x76" />
<link rel="apple-touch-icon" type="image/x-icon" href="/assets/touch-icon-iphone-retina-72e2aadf86513a56e050e7f0f2355deaa19cc17ed97bbe5147847f2748e5a3e3.png" sizes="120x120" />
<link rel="apple-touch-icon" type="image/x-icon" href="/assets/touch-icon-ipad-retina-8ebe416f5313483d9c1bc772b5bbe03ecad52a54eba443e5215a22caed2a16a2.png" sizes="152x152" />
<link color="rgb(226, 67, 41)" href="/assets/logo-d36b5212042cebc89b96df4bf6ac24e43db316143e89926c0db839ff694d2de4.svg" rel="mask-icon">
<meta content="/assets/msapplication-tile-1196ec67452f618d39cdd85e2e3a542f76574c071051ae7effbfde01710eb17d.png" name="msapplication-TileImage">
```

The way that this tool works is as follows:

1. Fetch the sign-in page from a remote GitLab server
2. Identify all hashed resources in the response
3. Cross-reference with known resource hashes (compiled by me using Docker containers)
4. All matching GitLab versions based on frontend file hashes are returned by the tool.

## Why did I create this

I created this because during the recent GitLab vulnerability announcements, as a blue-teamer, I was unable to check the GitLab version
running on linux machines in our enterprise environment. Therefore, for every single GitLab instance running in our environment, we had
to identify the maintainers of that specific host, reach out to them, just to check what version is running.

Most modern tools will simply include the version in a banner in the footer of the page, or expose an endpoint that allows people
to identify the running version. However, GitLab appears to practice security through obscurity, and as such only the administrator/logged-in users
of the service can know what version is running. Of course this doesn't really matter to bad actors, as they simply blast PoCs against the running GitLab instances, while blue-teamers avoid doing so to not trip up their own security.

Security through obscurity does not work.

## WAF/CDN restrictions

If the GitLab instance you're interested in is behind a bot protection mechanism, you can simply download the sign-in page locally, and run the script with the `--file` parameter.

## Overlapping hashes and accuracy

Currently, only releases above 16.x.x are fully mapped throughout major.minor.patch releases. All previous releases only have major.minor hashes recorded. In practice, this means that patch releases between those major.minor releases may not be identified by the script correctly. Additionally, some 8.x releases are missing as they did not deploy correctly in Docker due to having outdated manifests.

Since a release's fingerprint is just the set of hashed asset filenames on its sign-in page, two different
GitLab releases produce an *identical* fingerprint whenever neither one touched a single compiled
frontend asset between them - which happens often, since GitLab ships a lot of patch releases that are
purely backend/security fixes. When that happens, this tool can only narrow a target down to a group of
candidate versions rather than a single exact one.

Current stats, generated from `data/gitlab-file-hashes.json` (418 captured CE releases):

| Metric | Value |
|---|---|
| Releases fingerprinted | 418 |
| Distinct fingerprints | 254 |
| Releases uniquely identifiable | 172 (41.1%) |
| Releases that tie with at least one other release | 246 (58.9%) |
| Duplicate-fingerprint clusters | 82 |
| Clusters that span more than one minor version | **0** |
| Distinct minor-version groups (e.g. `17.4`, `18.2`) | 118 |
| Average asset overlap between adjacent releases | 74.6% |

The one finding that matters most for how much to trust a result: **no duplicate cluster ever crosses a
minor-version boundary.** Every ambiguous match is confined to patch releases within the same minor
series - a `17.4.x` instance never gets confused for a `17.5.x` one. So while this tool can't always pin
an exact patch version, it reliably identifies the *minor* version, which is the same granularity most
GitLab security advisories use to describe affected/fixed ranges in the first place.

The most extreme duplicate clusters found so far, all within the 16.x series:

| Cluster | Versions | Size |
|---|---|---|
| 16.7 | `16.7.0`, `16.7.2`–`16.7.10` | 10 |
| 16.0 | `16.0.0`–`16.0.7` | 8 |
| 16.5 | `16.5.3`–`16.5.10` | 7 |
| 16.1 | `16.1.3`–`16.1.8` | 6 |
| 16.8 | `16.8.0`–`16.8.5` | 6 |

In practice, when the tool reports multiple matching releases, treat it the same way you'd treat a CVE
advisory scoped to a version range - you know the minor version for certain, and the result narrows the
patch level down to a small, explicit set of candidates instead of leaving you with nothing.

## Will GitLab EE also be included

I've currently created this tool to gauge if there is significant interest in this area. If it proves to be something that others would also find helpful,
I will also generate relevant tag information for GitLab EE.
