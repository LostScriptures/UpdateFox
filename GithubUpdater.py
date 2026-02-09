import requests
import subprocess

class GithubUpdater:
    def __init__(self, repo_owner: str, repo_name: str, branch: str, trigger: str, local_repo_path: str):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.branch = branch
        self.trigger = trigger
        self.local_repo_path = local_repo_path

    def check_and_update_repo(self, last_sha: str | None) -> tuple[str | None, bool]:
        updated = False
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/commits/{self.branch}"
        r = requests.get(url)
        r.raise_for_status()

        commit = r.json()
        sha = commit["sha"]
        msg = commit["commit"]["message"]

        if sha == last_sha:
            return last_sha, updated  # nothing new
 
        print(f"New commit found: {sha[:7]}")
        print(f"Message: {msg}")

        if self.trigger in msg:
            print("Trigger found, updating repo...")

            subprocess.run(["git", "fetch", "origin"], cwd=self.local_repo_path, check=True)
            subprocess.run(["git", "reset", "--hard", f"origin/{self.branch}"], cwd=self.local_repo_path, check=True)

            print("Repo updated!")
            updated = True

        return sha, updated