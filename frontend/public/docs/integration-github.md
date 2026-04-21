# GitHub Integration

83 tools for managing repositories, issues, pull requests, workflows, and more.

## Setup

GitHub uses a Personal Access Token (PAT) — no OAuth flow needed.

### 1. Create a Token

Go to GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens

Select the repositories and permissions your employee needs.

### 2. Add to Your Employee

```python
from worklone_employee import Employee, Github

github = Github(api_key="ghp_xxxxxxxxxxxxxxxxxxxx")

emp = Employee(name="Aria", owner_id="user_123")
for tool in github.all():
    emp.add_tool(tool)

emp.run("Create a GitHub issue titled 'Fix login bug' in the acme/backend repo.")
```

## Available Tools (Selected)

| Tool | Description |
|------|-------------|
| `github_create_issue` | Create a new issue |
| `github_update_issue` | Update an existing issue |
| `github_close_issue` | Close an issue |
| `github_list_issues` | List issues with filters |
| `github_get_issue` | Get issue details |
| `github_create_pr` | Create a pull request |
| `github_list_prs` | List pull requests |
| `github_merge_pr` | Merge a pull request |
| `github_create_comment` | Comment on an issue or PR |
| `github_get_file_content` | Read a file from a repo |
| `github_create_file` | Create a new file |
| `github_update_file` | Update an existing file |
| `github_search_code` | Search code across repos |
| `github_search_issues` | Search issues and PRs |
| `github_list_branches` | List branches |
| `github_create_branch` | Create a new branch |
| `github_list_workflow_runs` | List CI/CD workflow runs |
| `github_trigger_workflow` | Trigger a workflow |
| `github_create_release` | Create a release |
| `github_star_repo` | Star a repository |

83 tools total — full GitHub API coverage.

## Common Usage

```python
# Bug triage
emp.run("Search for open issues labeled 'bug' in acme/backend and summarize the top 5.")

# PR review
emp.run("List all open PRs in acme/frontend and tell me which ones need review.")

# Release management
emp.run("Create a release v2.1.0 in acme/backend with tag 'v2.1.0'.")

# Code search
emp.run("Search for 'TODO' comments in the acme/backend repo and list the files.")
```
