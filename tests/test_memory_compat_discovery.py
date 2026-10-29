from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from astrbot_host import memory_compat as compat


class MemoryCompatDiscoveryTests(unittest.TestCase):
    def plugin(self):
        return NS(extension_api=NS(), staging=NS(_terminated=False, context=NS(),
            session=NS(application=NS(state="running"))))

    def tearDown(self):
        if compat._active_plugin is not None:
            compat.deactivate(compat._active_plugin)

    def test_accessor_returns_the_real_facade_and_live_producer(self):
        plugin = self.plugin()
        compat.activate(plugin)
        self.assertIs(compat.current_api(), plugin.extension_api)
        self.assertIs(compat.current_api()._plugin, plugin)
        plugin.staging._terminated = True
        self.assertIsNone(compat.current_api())

    def test_old_unload_cannot_clear_a_reloaded_plugin(self):
        old, new = self.plugin(), self.plugin()
        compat.activate(old)
        compat.activate(new)
        compat.deactivate(old)
        self.assertIs(compat.current_api(), new.extension_api)
        compat.deactivate(new)
        self.assertIsNone(compat.current_api())

    def test_coordination_requires_real_owner_and_running_host(self):
        plugin = self.plugin()
        owner = NS(ownership=NS(delegated=True, reason="external_active"))
        with patch.object(compat, "read_memory_owner", return_value=owner):
            self.assertTrue(compat.coordination_status(plugin)["available"])
            plugin.staging.session.application.state = "stopped"
            self.assertFalse(compat.coordination_status(plugin)["available"])
            plugin.staging.session.application.state = "running"
            owner.ownership.delegated = False
            self.assertFalse(compat.coordination_status(plugin)["available"])
