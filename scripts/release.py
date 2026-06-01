import os
import json
import requests
import glob
import hashlib
import subprocess
from datetime import datetime, timedelta
from dataclasses import dataclass

GITHUB_TOKEN=os.environ.get("GITHUB_TOKEN")
GITHUB_REPO=os.environ.get("GITHUB_REPOSITORY", "stasel/WebRTC")
RELEASE_ARTIFACT_DIR=os.environ.get("RELEASE_ARTIFACT_DIR")

@dataclass
class NextReleaseResult:
    version: int
    releaseDate: datetime
    branch: str

@dataclass
class BuildMetadata:
    filename: str
    checksum: str
    commit: str
    branch: str

def getStableMilestone():
    """Find the current stable milestone from the Chromium Dashboard."""
    try:
        response = requests.get("https://chromiumdash.appspot.com/fetch_milestones")
        response.raise_for_status()
        milestones = response.json()
        stable = [m for m in milestones if m.get("schedule_phase") == "stable"]
        if stable:
            return int(max(stable, key=lambda m: m["milestone"])["milestone"])
        print("Warning: no milestone with schedule_phase 'stable' found")
    except (requests.RequestException, KeyError, ValueError, TypeError) as e:
        print(f"Warning: failed to fetch stable milestone: {e}")
    return None

def getNextRelease():
    # Get current version
    releases = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/releases", headers={'Authorization': f"token {GITHUB_TOKEN}"}).json()
    print(releases)
    latestReleaseVersion, latestReleaseDate = getLatestRelease(releases)
    print(f"Latest release: version {latestReleaseVersion}, date: {latestReleaseDate}")

    # Get the current stable milestone
    stableMilestone = getStableMilestone()
    if not stableMilestone:
        print("❌ Could not determine current stable milestone")
        os._exit(os.EX_SOFTWARE)

    nextReleaseVersion = max(latestReleaseVersion + 1, stableMilestone)
    if nextReleaseVersion > latestReleaseVersion + 1:
        print(f"Current stable milestone is M{stableMilestone}, skipping ahead from M{latestReleaseVersion + 1}")

    milestones = requests.get(f"https://chromiumdash.appspot.com/fetch_milestone_schedule?mstone={nextReleaseVersion}").json()
    nextReleaseDate = datetime.fromisoformat(milestones["mstones"][0]["stable_date"])
    print(f"Next release:   version {nextReleaseVersion}, date: {nextReleaseDate}")

    # Get next version branch
    releases = requests.get(f"https://chromiumdash.appspot.com/fetch_milestones?mstone={nextReleaseVersion}").json()
    nextReleaseBranch = "branch-heads/" + releases[0]["webrtc_branch"]

    return NextReleaseResult(version = nextReleaseVersion, releaseDate = nextReleaseDate, branch = nextReleaseBranch)

def getLatestRelease(releases):
    for release in releases:
        releaseDate = release.get("published_at") or release.get("created_at")
        tagName = release.get("tag_name")
        if not tagName or not releaseDate:
            continue
        return int(tagName.split(".")[0]), datetime.fromisoformat(releaseDate.replace("Z", ""))

    tags = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/tags", headers={'Authorization': f"token {GITHUB_TOKEN}"}).json()
    versions = [
        int(tag["name"].split(".")[0])
        for tag in tags
        if tag.get("name", "").split(".")[0].isdigit()
    ]
    if versions:
        return max(versions), datetime.min

    print("❌ Could not determine latest release or tag")
    os._exit(os.EX_SOFTWARE)

def isReleaseAvailable(release):
    return datetime.today() >= (release.releaseDate + timedelta(days=1))

def buildWebRTC(branch):
    os.environ["BRANCH"] = branch
    os.environ["IOS"] = "true"
    os.environ["MACOS"] = "true"
    os.environ["MAC_CATALYST"] = "true"

    return os.system('sh scripts/build.sh') == 0

def getBuildMetadata(outputDir):
    with open(f"{outputDir}/metadata.json", 'r') as f:
        jsonData = json.loads(f.read())
        return BuildMetadata(filename = jsonData['file'], checksum = jsonData['checksum'], commit = jsonData['commit'], branch = jsonData['branch'])

def calculateChecksum(path):
    sha256 = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def getBranchCommit(branch):
    result = subprocess.run(
        ["git", "ls-remote", "https://webrtc.googlesource.com/src", f"refs/{branch}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.split()[0]

def getBuildMetadataFromArtifact(outputDir, release):
    metadataPath = os.path.join(outputDir, "metadata.json")
    if os.path.exists(metadataPath):
        metadata = getBuildMetadata(outputDir)
        if metadata.branch != release.branch:
            print(f"❌ Artifact branch {metadata.branch} does not match release branch {release.branch}")
            os._exit(os.EX_SOFTWARE)
        return metadata

    artifacts = glob.glob(os.path.join(outputDir, "WebRTC-*.xcframework.zip"))
    if len(artifacts) != 1:
        print(f"❌ Expected one WebRTC artifact zip in {outputDir}, found {len(artifacts)}")
        os._exit(os.EX_SOFTWARE)

    artifact = artifacts[0]
    print("⚠️  Artifact metadata.json was not found. Inferring checksum and commit from the release branch.")
    return BuildMetadata(
        filename = os.path.basename(artifact),
        checksum = calculateChecksum(artifact),
        commit = getBranchCommit(release.branch),
        branch = release.branch,
    )

def createReleaseDraft(release, buildMetadata):
    body = f"Release notes: https://webrtc.googlesource.com/src.git/+log/refs/{buildMetadata.branch}/\n"
    body += f"WebRTC Branch: [{buildMetadata.branch}](https://chromium.googlesource.com/external/webrtc/+log/{buildMetadata.branch})\n"
    body += f"WebRTC Commit: `{buildMetadata.commit}`\n"
    body += f"SHA 256 checksum: `{buildMetadata.checksum}`"

    fields = { 
        'name': f'M{release.version}',
        'tag_name': f'{release.version}.0.0',
        'draft': True,
        'body': body
    }
    headers = {'accept': 'application/vnd.github.v3+json', 'Authorization': f'token {GITHUB_TOKEN}'}
    response = requests.post(f"https://api.github.com/repos/{GITHUB_REPO}/releases", json = fields, headers = headers)
    if response.status_code != requests.codes.created:
        print(f"❌ Failed creating release draft: HTTP {response.status_code}")
        print(response.text)
        os._exit(os.EX_SOFTWARE)
    return response.json()

def uploadReleaseAsset(url, assetLocalPath, assetName):
    url = url.replace(u'{?name,label}','')
    fileToUpload = open(assetLocalPath, 'rb')  
    size = os.stat(assetLocalPath).st_size
    params = {'name': assetName}
    headers = {'Authorization': f'token {GITHUB_TOKEN}', 'Content-Length': str(size), 'Content-Type': 'Application/zip'}
    response = requests.post(url, params = params, data = fileToUpload, headers = headers)
    success = response.status_code == requests.codes.created
    if not success:
        print(f"❌ Failed uploading release asset: HTTP {response.status_code}")
        print(response.text)
    return success

def createPullRequest(release, head):
    headers = {'accept': 'application/vnd.github.v3+json', 'Authorization': f'token {GITHUB_TOKEN}'}
    body = { 
        'title': f'Release M{release.version}',
        'head': head,
        'base': 'latest',
        'body': f'Updated files for release M{release.version}.'
    }
    response = requests.post(f"https://api.github.com/repos/{GITHUB_REPO}/pulls", json = body, headers = headers)
    success = response.status_code == requests.codes.created
    if not success:
        print(f"❌ Failed creating pull request: HTTP {response.status_code}")
        print(response.text)
    return success

if __name__ == "__main__":
    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN environment variable is not provided")
        os._exit(os.EX_SOFTWARE)

    # Get next release details
    print("➡️ Fetching next release...")
    nextRelease = getNextRelease()

    # Check if it is time for a new reelease
    if not isReleaseAvailable(nextRelease):
        print("ℹ️  Next version is not out yet. Skipping build")
        os._exit(os.EX_OK)

    print(f"✅ {nextRelease}\n")
    print("✅ New Version is available to build")

    outputDir = RELEASE_ARTIFACT_DIR or "./out"
    if RELEASE_ARTIFACT_DIR:
        print(f"➡️ Using existing WebRTC artifact from {RELEASE_ARTIFACT_DIR}")
        buildMetadata = getBuildMetadataFromArtifact(outputDir, nextRelease)
    else:
        # Build WebRTC Frameworks
        print("➡️ Building WebRTC Library...")
        buildSuccess = buildWebRTC(nextRelease.branch)
        if not buildSuccess:
            print("❌ WebRTC Build Failed")
            os._exit(os.EX_SOFTWARE)

        print("✅ WebRTC build successful\n")

        # Get metadata build file - it has all the information needed about the build
        buildMetadata = getBuildMetadata(outputDir)
    print(buildMetadata)

    # Create new release draft
    print("➡️ Creating new release draft...")
    githubReleaseDraft = createReleaseDraft(nextRelease ,buildMetadata)

    # Upload asset to github
    print("➡️ Uploading asset to github...")
    assetName = f"WebRTC-M{nextRelease.version}.xcframework.zip"
    assetPath = os.path.join(outputDir, buildMetadata.filename)
    uploadURL = githubReleaseDraft['upload_url']
    uploadResult = uploadReleaseAsset(uploadURL, assetPath, assetName)

    if not uploadResult:
        print("❌ Failed uploading asset to github")
        os._exit(os.EX_SOFTWARE)

    print(f"✅ Successfully created new draft release in github: {githubReleaseDraft['url']}")

    # Create new branch with code changes
    print("➡️ Creating local branch...")
    releaseBranch = f'release-M{nextRelease.version}'
    os.system(f'git checkout -b {releaseBranch}')

    # Change code
    print("➡️ Applying code changes...")
    os.system(f"sed -i '' -E 's/[0-9]+\.[0-9]+\.[0-9]+\/WebRTC-M[0-9]+/{nextRelease.version}.0.0\/WebRTC-M{nextRelease.version}/g' Package.swift WebRTC-lib.podspec")
    os.system(f"sed -i '' -E 's/checksum: \"[0-9a-f]+\"/checksum: \"{buildMetadata.checksum}\"/g' Package.swift WebRTC-lib.podspec ")
    os.system(f"sed -i '' -E 's/.upToNextMajor\\(\"[0-9]+\.[0-9]+\.[0-9]+/.upToNextMajor\\(\"{nextRelease.version}.0.0/g' README.md")
    os.system(f"sed -i '' -E 's/spec.version      = \"[0-9]+\.[0-9]+\.[0-9]+\"/spec.version      = \"{nextRelease.version}.0.0\"/g' WebRTC-lib.podspec")
    cartageFile = open("WebRTC.json", 'r')

    cartageJSON = json.loads(cartageFile.read())
    cartageJSON[f'{nextRelease.version}.0.0'] = f'https://github.com/{GITHUB_REPO}/releases/download/{nextRelease.version}.0.0/WebRTC-M{nextRelease.version}.xcframework.zip'
    cartageFile.close()
    cartageJSONWrite = open("WebRTC.json", 'w')
    cartageJSONWrite.write(json.dumps(cartageJSON, indent=4, sort_keys=True))
    cartageJSONWrite.close()


    # Commit and push
    print("➡️ Commiting and pushing code to remote...")
    os.system(f'git add Package.swift WebRTC-lib.podspec README.md WebRTC.json')
    os.system(f'git commit -m "Updated files for release M{nextRelease.version}"')
    os.system(f'git push origin {releaseBranch}')

    # Create PR
    print("➡️ Creating pull request...")
    prResult = createPullRequest(nextRelease, releaseBranch)
    if not prResult:
        print("❌ Failed creating pull request in github")
        os._exit(os.EX_SOFTWARE)

    print(f"✅ Done")
