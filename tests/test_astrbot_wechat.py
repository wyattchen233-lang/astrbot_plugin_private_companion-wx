"""WeChat routing, liveness, isolation and full mocked host delivery."""

from types import SimpleNamespace as NS
import unittest

from tests import test_astrbot_qq_official as official
from astrbot_host.binding import event_identity
from companion_v2.adapters.astrbot.group import group_event_route
from companion_v2.adapters.astrbot.native import (
    event_account_id, native_client_connected, native_user_subject_id,
    supported_platform_name,
)


def wechat_platform(platform):
    platform.metadata.name = "agent_wechat_trial"
    platform.client = platform
    platform.running = True
    platform.closed = False
    platform.health = {"auth_status": "logged_in"}
    return platform


class WeChatRoutingTests(unittest.TestCase):
    def setUp(self):
        self.platform = wechat_platform(official.OfficialPlatform())

    def event(self, *, group=False):
        event = official.OfficialEvent(self.platform, sender="wxid_member_1", group=group)
        event.message_obj.self_id = "wechat-trial-self"
        if group:
            room = "58824897974@chatroom"
            event.message_obj.group_id = event.message_obj.session_id = room
            event.session.session_id = room
            event.unified_msg_origin = f"{official.ACCOUNT}:GroupMessage:{room}"
        return event

    def test_private_account_and_setup_binding_agree(self):
        event = self.event()
        self.assertEqual(event_account_id(event), official.ACCOUNT)
        self.assertEqual(event_identity(event)["account_id"], official.ACCOUNT)
        self.assertEqual(native_user_subject_id("agent_wechat_trial", "wxid_member_1"),
                         "wechat-user:wxid_member_1")
        self.assertNotEqual(native_user_subject_id("qq_official", "wxid_member_1"),
                            native_user_subject_id("agent_wechat_trial", "wxid_member_1"))

    def test_group_keeps_room_and_member_as_different_identities(self):
        route = group_event_route(self.event(group=True))
        self.assertEqual(route.account_id, official.ACCOUNT)
        self.assertEqual(route.group_id, "58824897974@chatroom")
        self.assertEqual(route.sender_id, "wxid_member_1")

    def test_changed_session_cannot_claim_another_room(self):
        event = self.event(group=True)
        event.session.session_id = "another@chatroom"
        with self.assertRaises(Exception):
            group_event_route(event)

    def test_liveness_requires_current_client_login_and_running_adapter(self):
        self.assertTrue(native_client_connected(self.platform, official.ACCOUNT))
        self.assertFalse(native_client_connected(self.platform, "another-account"))
        self.assertFalse(native_client_connected(self.platform, official.ACCOUNT, NS()))
        self.platform.health["auth_status"] = "logged_out"
        self.assertFalse(native_client_connected(self.platform, official.ACCOUNT))
        self.platform.health["auth_status"] = "logged_in"
        self.platform.closed = True
        self.assertFalse(native_client_connected(self.platform, official.ACCOUNT))
        self.platform.closed = False
        self.platform.running = False
        self.assertFalse(native_client_connected(self.platform, official.ACCOUNT))

    def test_unknown_adapter_is_still_rejected(self):
        self.assertFalse(supported_platform_name("random_wechat"))
        self.assertFalse(supported_platform_name("wechat"))


class WeChatMultiHostTests(official.OfficialMultiHostTests):
    """Run the original multi-host/private/group sender acceptance on WeChat."""

    def setUp(self):
        super().setUp()
        wechat_platform(self.native.platform)

    async def test_official_account_directory_reports_adapter_family_for_ui_labels(self):
        accounts = self.controller.session_topology.accounts()
        account = next(row for row in accounts if row["platform_id"] == official.ACCOUNT)
        self.assertEqual(account["platform_name"], "agent_wechat_trial")
        self.assertEqual(account["account_id"], official.ACCOUNT)
