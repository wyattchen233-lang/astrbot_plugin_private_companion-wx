"""Expose the existing V2 read-only facade to MemoryCompanion 1.10.x.

This restores discovery only. It does not fabricate V1 internals, relationship
scores, snapshots, grants or successful writes that V2 does not provide.
"""

from companion_v2.adapters.astrbot.memory_owner import read_memory_owner

_active_plugin = None


def activate(plugin):
    global _active_plugin
    plugin.extension_api._plugin = plugin
    _active_plugin = plugin


def deactivate(plugin):
    global _active_plugin
    if _active_plugin is plugin:
        _active_plugin = None


def current_api():
    plugin = _active_plugin
    if plugin is None or getattr(plugin.staging, "_terminated", True):
        return None
    return plugin.extension_api


def coordination_status(plugin):
    staging = plugin.staging
    owner = read_memory_owner(staging.context).ownership
    session = getattr(staging, "session", None)
    running = (not staging._terminated and session is not None
               and session.application.state == "running")
    ready = bool(running and owner.delegated)
    return {"available": ready, "state": "ready" if ready else "degraded",
            "degraded": not ready,
            "reason": "" if ready else ("host_not_running" if not running else owner.reason)}
