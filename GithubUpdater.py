import requests
import subprocess

class GithubUpdater:
    """Class responsible for checking a GitHub repository for new commits and updating a local repository if a specified trigger is found in the commit message."""
    def __init__(self, repo_owner: str, repo_name: str, branch: str, local_repo_path: str):
        """Initializes the GithubUpdater with repository details and trigger information."""
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.branch = branch
        self.local_repo_path = local_repo_path

    def get_repo(self) -> dict:
        """Fetches the latest commit information from the GitHub repository."""
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/commits/{self.branch}"
        r = requests.get(url)
        r.raise_for_status()

        return r.json()

    def do_update(self) -> None:
        """Performs a git fetch and reset to update the local repository to match the latest commit on the specified branch."""
        print("Updating repo...")

        subprocess.run(["git", "fetch", "origin"], cwd=self.local_repo_path, check=True)
        subprocess.run(["git", "reset", "--hard", f"origin/{self.branch}"], cwd=self.local_repo_path, check=True)

        print("Repo updated!")

    def check_repo(self, last_sha: str) -> tuple[str, bool]:
        """Checks the GitHub repository for new commits and returns the sha and if an update is needed."""
        do_update = False
        
        commit = self.get_repo()
        sha = commit["sha"]
        msg = commit["commit"]["message"]

        if sha == last_sha:
            return sha, do_update  # nothing new
 
        print(f"New commit found: {sha}")
        print(f"Message: {msg}")

        return sha, True