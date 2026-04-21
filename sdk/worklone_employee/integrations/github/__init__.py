"""
Github integration for worklone-employee SDK.
"""
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
import httpx
from worklone_employee.integrations.base import ApiKeyIntegration
from worklone_employee.tools.base import BaseTool

from worklone_employee.integrations.github.add_assignees import GitHubAddAssigneesTool
from worklone_employee.integrations.github.add_labels import GitHubAddLabelsTool
from worklone_employee.integrations.github.cancel_workflow_run import GitHubCancelWorkflowRunTool
from worklone_employee.integrations.github.check_star import GitHubCheckStarTool
from worklone_employee.integrations.github.close_issue import GitHubCloseIssueTool
from worklone_employee.integrations.github.close_pr import GitHubClosePRTool
from worklone_employee.integrations.github.comment import GitHubCommentTool
from worklone_employee.integrations.github.compare_commits import GitHubCompareCommitsTool
from worklone_employee.integrations.github.create_branch import GitHubCreateBranchTool
from worklone_employee.integrations.github.create_comment_reaction import GitHubCreateCommentReactionTool
from worklone_employee.integrations.github.create_file import GitHubCreateFileTool
from worklone_employee.integrations.github.create_gist import GitHubCreateGistTool
from worklone_employee.integrations.github.create_issue import GitHubCreateIssueTool
from worklone_employee.integrations.github.create_issue_reaction import GitHubCreateIssueReactionTool
from worklone_employee.integrations.github.create_milestone import GitHubCreateMilestoneTool
from worklone_employee.integrations.github.create_pr import GitHubCreatePRTool
from worklone_employee.integrations.github.create_project import GitHubCreateProjectTool
from worklone_employee.integrations.github.create_release import GitHubCreateReleaseTool
from worklone_employee.integrations.github.delete_branch import GitHubDeleteBranchTool
from worklone_employee.integrations.github.delete_comment import GitHubDeleteCommentTool
from worklone_employee.integrations.github.delete_comment_reaction import GitHubDeleteCommentReactionTool
from worklone_employee.integrations.github.delete_file import GitHubDeleteFileTool
from worklone_employee.integrations.github.delete_gist import GitHubDeleteGistTool
from worklone_employee.integrations.github.delete_issue_reaction import GitHubDeleteIssueReactionTool
from worklone_employee.integrations.github.delete_milestone import GitHubDeleteMilestoneTool
from worklone_employee.integrations.github.delete_project import GitHubDeleteProjectTool
from worklone_employee.integrations.github.delete_release import GitHubDeleteReleaseTool
from worklone_employee.integrations.github.fork_gist import GitHubForkGistTool
from worklone_employee.integrations.github.fork_repo import GitHubForkRepoTool
from worklone_employee.integrations.github.get_branch import GitHubGetBranchTool
from worklone_employee.integrations.github.get_branch_protection import GitHubGetBranchProtectionTool
from worklone_employee.integrations.github.get_commit import GitHubGetCommitTool
from worklone_employee.integrations.github.get_file_content import GitHubGetFileContentTool
from worklone_employee.integrations.github.get_gist import GithubGetGistTool
from worklone_employee.integrations.github.get_issue import GitHubGetIssueTool
from worklone_employee.integrations.github.get_milestone import GitHubGetMilestoneTool
from worklone_employee.integrations.github.get_pr_files import GitHubGetPRFilesTool
from worklone_employee.integrations.github.get_project import GitHubGetProjectTool
from worklone_employee.integrations.github.get_release import GitHubGetReleaseTool
from worklone_employee.integrations.github.get_tree import GitHubGetTreeTool
from worklone_employee.integrations.github.get_workflow import GitHubGetWorkflowTool
from worklone_employee.integrations.github.get_workflow_run import GitHubGetWorkflowRunTool
from worklone_employee.integrations.github.issue_comment import GithubIssueCommentTool
from worklone_employee.integrations.github.latest_commit import GithubLatestCommitTool
from worklone_employee.integrations.github.list_branches import GitHubListBranchesTool
from worklone_employee.integrations.github.list_commits import GitHubListCommitsTool
from worklone_employee.integrations.github.list_forks import GitHubListForksTool
from worklone_employee.integrations.github.list_gists import GitHubListGistsTool
from worklone_employee.integrations.github.list_issue_comments import GitHubListIssueCommentsTool
from worklone_employee.integrations.github.list_issues import GitHubListIssuesTool
from worklone_employee.integrations.github.list_milestones import GitHubListMilestonesTool
from worklone_employee.integrations.github.list_pr_comments import GitHubListPRCommentsTool
from worklone_employee.integrations.github.list_projects import GitHubListProjectsTool
from worklone_employee.integrations.github.list_prs import GitHubListPRsTool
from worklone_employee.integrations.github.list_releases import GitHubListReleasesTool
from worklone_employee.integrations.github.list_stargazers import GitHubListStargazersTool
from worklone_employee.integrations.github.list_workflow_runs import GitHubListWorkflowRunsTool
from worklone_employee.integrations.github.list_workflows import GithubListWorkflowsTool
from worklone_employee.integrations.github.merge_pr import GitHubMergePRTool
from worklone_employee.integrations.github.pr import GitHubPrTool
from worklone_employee.integrations.github.remove_label import GitHubRemoveLabelTool
from worklone_employee.integrations.github.repo_info import GitHubRepoInfoTool
from worklone_employee.integrations.github.request_reviewers import GitHubRequestReviewersTool
from worklone_employee.integrations.github.rerun_workflow import GitHubRerunWorkflowTool
from worklone_employee.integrations.github.search_code import GitHubSearchCodeTool
from worklone_employee.integrations.github.search_commits import GitHubSearchCommitsTool
from worklone_employee.integrations.github.search_issues import GitHubSearchIssuesTool
from worklone_employee.integrations.github.search_repos import GitHubSearchReposTool
from worklone_employee.integrations.github.search_users import GithubSearchUsersTool
from worklone_employee.integrations.github.star_gist import GithubStarGistTool
from worklone_employee.integrations.github.star_repo import GitHubStarRepoTool
from worklone_employee.integrations.github.trigger_workflow import GitHubTriggerWorkflowTool
from worklone_employee.integrations.github.unstar_gist import GithubUnstarGistTool
from worklone_employee.integrations.github.unstar_repo import GitHubUnstarRepoTool
from worklone_employee.integrations.github.update_branch_protection import GitHubUpdateBranchProtectionTool
from worklone_employee.integrations.github.update_comment import GitHubUpdateCommentTool
from worklone_employee.integrations.github.update_file import GitHubUpdateFileTool
from worklone_employee.integrations.github.update_gist import GitHubUpdateGistTool
from worklone_employee.integrations.github.update_issue import GitHubUpdateIssueTool
from worklone_employee.integrations.github.update_milestone import GitHubUpdateMilestoneTool
from worklone_employee.integrations.github.update_pr import GitHubUpdatePRTool
from worklone_employee.integrations.github.update_project import GitHubUpdateProjectTool
from worklone_employee.integrations.github.update_release import GitHubUpdateReleaseTool

_TOOL_CLASSES = [
    GitHubAddAssigneesTool, GitHubAddLabelsTool, GitHubCancelWorkflowRunTool, GitHubCheckStarTool, GitHubCloseIssueTool, GitHubClosePRTool, GitHubCommentTool, GitHubCompareCommitsTool, GitHubCreateBranchTool, GitHubCreateCommentReactionTool, GitHubCreateFileTool, GitHubCreateGistTool, GitHubCreateIssueTool, GitHubCreateIssueReactionTool, GitHubCreateMilestoneTool, GitHubCreatePRTool, GitHubCreateProjectTool, GitHubCreateReleaseTool, GitHubDeleteBranchTool, GitHubDeleteCommentTool, GitHubDeleteCommentReactionTool, GitHubDeleteFileTool, GitHubDeleteGistTool, GitHubDeleteIssueReactionTool, GitHubDeleteMilestoneTool, GitHubDeleteProjectTool, GitHubDeleteReleaseTool, GitHubForkGistTool, GitHubForkRepoTool, GitHubGetBranchTool, GitHubGetBranchProtectionTool, GitHubGetCommitTool, GitHubGetFileContentTool, GithubGetGistTool, GitHubGetIssueTool, GitHubGetMilestoneTool, GitHubGetPRFilesTool, GitHubGetProjectTool, GitHubGetReleaseTool, GitHubGetTreeTool, GitHubGetWorkflowTool, GitHubGetWorkflowRunTool, GithubIssueCommentTool, GithubLatestCommitTool, GitHubListBranchesTool, GitHubListCommitsTool, GitHubListForksTool, GitHubListGistsTool, GitHubListIssueCommentsTool, GitHubListIssuesTool, GitHubListMilestonesTool, GitHubListPRCommentsTool, GitHubListProjectsTool, GitHubListPRsTool, GitHubListReleasesTool, GitHubListStargazersTool, GitHubListWorkflowRunsTool, GithubListWorkflowsTool, GitHubMergePRTool, GitHubPrTool, GitHubRemoveLabelTool, GitHubRepoInfoTool, GitHubRequestReviewersTool, GitHubRerunWorkflowTool, GitHubSearchCodeTool, GitHubSearchCommitsTool, GitHubSearchIssuesTool, GitHubSearchReposTool, GithubSearchUsersTool, GithubStarGistTool, GitHubStarRepoTool, GitHubTriggerWorkflowTool, GithubUnstarGistTool, GitHubUnstarRepoTool, GitHubUpdateBranchProtectionTool, GitHubUpdateCommentTool, GitHubUpdateFileTool, GitHubUpdateGistTool, GitHubUpdateIssueTool, GitHubUpdateMilestoneTool, GitHubUpdatePRTool, GitHubUpdateProjectTool, GitHubUpdateReleaseTool,
]

def _wire(tool: BaseTool, integration) -> BaseTool:
    async def _resolve_access_token(context=None):
        return integration._get_token()
    tool._resolve_access_token = _resolve_access_token
    return tool


class Github(ApiKeyIntegration):
    """Pass a GitHub Personal Access Token (ghp_...) or fine-grained token."""

    def __init__(self, api_key: str):
        super().__init__(api_key)


    def all(self) -> List[BaseTool]:
        return [_wire(cls(), self) for cls in _TOOL_CLASSES]

    @property
    def git_hub_add_assignees(self): return _wire(GitHubAddAssigneesTool(), self)
    @property
    def git_hub_add_labels(self): return _wire(GitHubAddLabelsTool(), self)
    @property
    def git_hub_cancel_workflow_run(self): return _wire(GitHubCancelWorkflowRunTool(), self)
    @property
    def git_hub_check_star(self): return _wire(GitHubCheckStarTool(), self)
    @property
    def git_hub_close_issue(self): return _wire(GitHubCloseIssueTool(), self)
    @property
    def git_hub_close_p_r(self): return _wire(GitHubClosePRTool(), self)
    @property
    def git_hub_comment(self): return _wire(GitHubCommentTool(), self)
    @property
    def git_hub_compare_commits(self): return _wire(GitHubCompareCommitsTool(), self)
    @property
    def git_hub_create_branch(self): return _wire(GitHubCreateBranchTool(), self)
    @property
    def git_hub_create_comment_reaction(self): return _wire(GitHubCreateCommentReactionTool(), self)
    @property
    def git_hub_create_file(self): return _wire(GitHubCreateFileTool(), self)
    @property
    def git_hub_create_gist(self): return _wire(GitHubCreateGistTool(), self)
    @property
    def git_hub_create_issue(self): return _wire(GitHubCreateIssueTool(), self)
    @property
    def git_hub_create_issue_reaction(self): return _wire(GitHubCreateIssueReactionTool(), self)
    @property
    def git_hub_create_milestone(self): return _wire(GitHubCreateMilestoneTool(), self)
    @property
    def git_hub_create_p_r(self): return _wire(GitHubCreatePRTool(), self)
    @property
    def git_hub_create_project(self): return _wire(GitHubCreateProjectTool(), self)
    @property
    def git_hub_create_release(self): return _wire(GitHubCreateReleaseTool(), self)
    @property
    def git_hub_delete_branch(self): return _wire(GitHubDeleteBranchTool(), self)
    @property
    def git_hub_delete_comment(self): return _wire(GitHubDeleteCommentTool(), self)
    @property
    def git_hub_delete_comment_reaction(self): return _wire(GitHubDeleteCommentReactionTool(), self)
    @property
    def git_hub_delete_file(self): return _wire(GitHubDeleteFileTool(), self)
    @property
    def git_hub_delete_gist(self): return _wire(GitHubDeleteGistTool(), self)
    @property
    def git_hub_delete_issue_reaction(self): return _wire(GitHubDeleteIssueReactionTool(), self)
    @property
    def git_hub_delete_milestone(self): return _wire(GitHubDeleteMilestoneTool(), self)
    @property
    def git_hub_delete_project(self): return _wire(GitHubDeleteProjectTool(), self)
    @property
    def git_hub_delete_release(self): return _wire(GitHubDeleteReleaseTool(), self)
    @property
    def git_hub_fork_gist(self): return _wire(GitHubForkGistTool(), self)
    @property
    def git_hub_fork_repo(self): return _wire(GitHubForkRepoTool(), self)
    @property
    def git_hub_get_branch(self): return _wire(GitHubGetBranchTool(), self)
    @property
    def git_hub_get_branch_protection(self): return _wire(GitHubGetBranchProtectionTool(), self)
    @property
    def git_hub_get_commit(self): return _wire(GitHubGetCommitTool(), self)
    @property
    def git_hub_get_file_content(self): return _wire(GitHubGetFileContentTool(), self)
    @property
    def get_gist(self): return _wire(GithubGetGistTool(), self)
    @property
    def git_hub_get_issue(self): return _wire(GitHubGetIssueTool(), self)
    @property
    def git_hub_get_milestone(self): return _wire(GitHubGetMilestoneTool(), self)
    @property
    def git_hub_get_p_r_files(self): return _wire(GitHubGetPRFilesTool(), self)
    @property
    def git_hub_get_project(self): return _wire(GitHubGetProjectTool(), self)
    @property
    def git_hub_get_release(self): return _wire(GitHubGetReleaseTool(), self)
    @property
    def git_hub_get_tree(self): return _wire(GitHubGetTreeTool(), self)
    @property
    def git_hub_get_workflow(self): return _wire(GitHubGetWorkflowTool(), self)
    @property
    def git_hub_get_workflow_run(self): return _wire(GitHubGetWorkflowRunTool(), self)
    @property
    def issue_comment(self): return _wire(GithubIssueCommentTool(), self)
    @property
    def latest_commit(self): return _wire(GithubLatestCommitTool(), self)
    @property
    def git_hub_list_branches(self): return _wire(GitHubListBranchesTool(), self)
    @property
    def git_hub_list_commits(self): return _wire(GitHubListCommitsTool(), self)
    @property
    def git_hub_list_forks(self): return _wire(GitHubListForksTool(), self)
    @property
    def git_hub_list_gists(self): return _wire(GitHubListGistsTool(), self)
    @property
    def git_hub_list_issue_comments(self): return _wire(GitHubListIssueCommentsTool(), self)
    @property
    def git_hub_list_issues(self): return _wire(GitHubListIssuesTool(), self)
    @property
    def git_hub_list_milestones(self): return _wire(GitHubListMilestonesTool(), self)
    @property
    def git_hub_list_p_r_comments(self): return _wire(GitHubListPRCommentsTool(), self)
    @property
    def git_hub_list_projects(self): return _wire(GitHubListProjectsTool(), self)
    @property
    def git_hub_list_p_rs(self): return _wire(GitHubListPRsTool(), self)
    @property
    def git_hub_list_releases(self): return _wire(GitHubListReleasesTool(), self)
    @property
    def git_hub_list_stargazers(self): return _wire(GitHubListStargazersTool(), self)
    @property
    def git_hub_list_workflow_runs(self): return _wire(GitHubListWorkflowRunsTool(), self)
    @property
    def list_workflows(self): return _wire(GithubListWorkflowsTool(), self)
    @property
    def git_hub_merge_p_r(self): return _wire(GitHubMergePRTool(), self)
    @property
    def git_hub_pr(self): return _wire(GitHubPrTool(), self)
    @property
    def git_hub_remove_label(self): return _wire(GitHubRemoveLabelTool(), self)
    @property
    def git_hub_repo_info(self): return _wire(GitHubRepoInfoTool(), self)
    @property
    def git_hub_request_reviewers(self): return _wire(GitHubRequestReviewersTool(), self)
    @property
    def git_hub_rerun_workflow(self): return _wire(GitHubRerunWorkflowTool(), self)
    @property
    def git_hub_search_code(self): return _wire(GitHubSearchCodeTool(), self)
    @property
    def git_hub_search_commits(self): return _wire(GitHubSearchCommitsTool(), self)
    @property
    def git_hub_search_issues(self): return _wire(GitHubSearchIssuesTool(), self)
    @property
    def git_hub_search_repos(self): return _wire(GitHubSearchReposTool(), self)
    @property
    def search_users(self): return _wire(GithubSearchUsersTool(), self)
    @property
    def star_gist(self): return _wire(GithubStarGistTool(), self)
    @property
    def git_hub_star_repo(self): return _wire(GitHubStarRepoTool(), self)
    @property
    def git_hub_trigger_workflow(self): return _wire(GitHubTriggerWorkflowTool(), self)
    @property
    def unstar_gist(self): return _wire(GithubUnstarGistTool(), self)
    @property
    def git_hub_unstar_repo(self): return _wire(GitHubUnstarRepoTool(), self)
    @property
    def git_hub_update_branch_protection(self): return _wire(GitHubUpdateBranchProtectionTool(), self)
    @property
    def git_hub_update_comment(self): return _wire(GitHubUpdateCommentTool(), self)
    @property
    def git_hub_update_file(self): return _wire(GitHubUpdateFileTool(), self)
    @property
    def git_hub_update_gist(self): return _wire(GitHubUpdateGistTool(), self)
    @property
    def git_hub_update_issue(self): return _wire(GitHubUpdateIssueTool(), self)
    @property
    def git_hub_update_milestone(self): return _wire(GitHubUpdateMilestoneTool(), self)
    @property
    def git_hub_update_p_r(self): return _wire(GitHubUpdatePRTool(), self)
    @property
    def git_hub_update_project(self): return _wire(GitHubUpdateProjectTool(), self)
    @property
    def git_hub_update_release(self): return _wire(GitHubUpdateReleaseTool(), self)
