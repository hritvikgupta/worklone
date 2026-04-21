"""
Slack integration for worklone-employee SDK.
"""
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
import httpx
from worklone_employee.integrations.base import OAuthIntegration, OAuthIntegration
from worklone_employee.tools.base import BaseTool

from worklone_employee.integrations.slack.add_reaction import SlackAddReactionTool
from worklone_employee.integrations.slack.canvas import SlackCanvasTool
from worklone_employee.integrations.slack.create_channel_canvas import SlackCreateChannelCanvasTool
from worklone_employee.integrations.slack.create_conversation import SlackCreateConversationTool
from worklone_employee.integrations.slack.delete_message import SlackDeleteMessageTool
from worklone_employee.integrations.slack.download import SlackDownloadTool
from worklone_employee.integrations.slack.edit_canvas import SlackEditCanvasTool
from worklone_employee.integrations.slack.ephemeral_message import SlackEphemeralMessageTool
from worklone_employee.integrations.slack.get_channel_info import SlackGetChannelInfoTool
from worklone_employee.integrations.slack.get_message import SlackGetMessageTool
from worklone_employee.integrations.slack.get_thread import SlackGetThreadTool
from worklone_employee.integrations.slack.get_user import SlackGetUserTool
from worklone_employee.integrations.slack.get_user_presence import SlackGetUserPresenceTool
from worklone_employee.integrations.slack.invite_to_conversation import SlackInviteToConversationTool
from worklone_employee.integrations.slack.list_channels import SlackListChannelsTool
from worklone_employee.integrations.slack.list_members import SlackListMembersTool
from worklone_employee.integrations.slack.list_users import SlackListUsersTool
from worklone_employee.integrations.slack.message import SlackMessageTool
from worklone_employee.integrations.slack.message_reader import SlackMessageReaderTool
from worklone_employee.integrations.slack.open_view import SlackOpenViewTool
from worklone_employee.integrations.slack.publish_view import SlackPublishViewTool
from worklone_employee.integrations.slack.push_view import SlackPushViewTool
from worklone_employee.integrations.slack.remove_reaction import SlackRemoveReactionTool
from worklone_employee.integrations.slack.update_message import SlackUpdateMessageTool
from worklone_employee.integrations.slack.update_view import SlackUpdateViewTool

_TOOL_CLASSES = [
    SlackAddReactionTool, SlackCanvasTool, SlackCreateChannelCanvasTool, SlackCreateConversationTool, SlackDeleteMessageTool, SlackDownloadTool, SlackEditCanvasTool, SlackEphemeralMessageTool, SlackGetChannelInfoTool, SlackGetMessageTool, SlackGetThreadTool, SlackGetUserTool, SlackGetUserPresenceTool, SlackInviteToConversationTool, SlackListChannelsTool, SlackListMembersTool, SlackListUsersTool, SlackMessageTool, SlackMessageReaderTool, SlackOpenViewTool, SlackPublishViewTool, SlackPushViewTool, SlackRemoveReactionTool, SlackUpdateMessageTool, SlackUpdateViewTool,
]

def _wire(tool: BaseTool, integration) -> BaseTool:
    async def _resolve_access_token(context=None):
        user_id = (context or {}).get("user_id") or (context or {}).get("owner_id")
        if not user_id:
            raise ValueError("user_id missing from context — pass user_id when calling emp.run()")
        return await integration._get_token(user_id)
    tool._resolve_access_token = _resolve_access_token
    return tool


class Slack(OAuthIntegration):
    PROVIDER = "slack"
    """Pass a bot token (xoxb-...) or user OAuth token as access_token."""

    def __init__(self, client_id: str, client_secret: str, token_store: "TokenStore"):
        super().__init__(client_id, client_secret, token_store)


    def all(self) -> List[BaseTool]:
        return [_wire(cls(), self) for cls in _TOOL_CLASSES]

    @property
    def add_reaction(self): return _wire(SlackAddReactionTool(), self)
    @property
    def canvas(self): return _wire(SlackCanvasTool(), self)
    @property
    def create_channel_canvas(self): return _wire(SlackCreateChannelCanvasTool(), self)
    @property
    def create_conversation(self): return _wire(SlackCreateConversationTool(), self)
    @property
    def delete_message(self): return _wire(SlackDeleteMessageTool(), self)
    @property
    def download(self): return _wire(SlackDownloadTool(), self)
    @property
    def edit_canvas(self): return _wire(SlackEditCanvasTool(), self)
    @property
    def ephemeral_message(self): return _wire(SlackEphemeralMessageTool(), self)
    @property
    def get_channel_info(self): return _wire(SlackGetChannelInfoTool(), self)
    @property
    def get_message(self): return _wire(SlackGetMessageTool(), self)
    @property
    def get_thread(self): return _wire(SlackGetThreadTool(), self)
    @property
    def get_user(self): return _wire(SlackGetUserTool(), self)
    @property
    def get_user_presence(self): return _wire(SlackGetUserPresenceTool(), self)
    @property
    def invite_to_conversation(self): return _wire(SlackInviteToConversationTool(), self)
    @property
    def list_channels(self): return _wire(SlackListChannelsTool(), self)
    @property
    def list_members(self): return _wire(SlackListMembersTool(), self)
    @property
    def list_users(self): return _wire(SlackListUsersTool(), self)
    @property
    def message(self): return _wire(SlackMessageTool(), self)
    @property
    def message_reader(self): return _wire(SlackMessageReaderTool(), self)
    @property
    def open_view(self): return _wire(SlackOpenViewTool(), self)
    @property
    def publish_view(self): return _wire(SlackPublishViewTool(), self)
    @property
    def push_view(self): return _wire(SlackPushViewTool(), self)
    @property
    def remove_reaction(self): return _wire(SlackRemoveReactionTool(), self)
    @property
    def update_message(self): return _wire(SlackUpdateMessageTool(), self)
    @property
    def update_view(self): return _wire(SlackUpdateViewTool(), self)
