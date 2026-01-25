# tests/conftest.py
import pytest


def pytest_collection_modifyitems(config, items):
    """Ensure OPC UA tests run first."""
    # Sort by marker priority
    marker_priority = {"first": 0, "second": 1, "third": 2}

    def get_priority(item):
        for marker in item.iter_markers():
            if marker.name in marker_priority:
                return marker_priority[marker.name]
        return 999  # Default low priority

    items.sort(key=get_priority)

    # Also sort OPC UA tests to the front even without markers
    opcua_items = []
    other_items = []

    for item in items:
        if "opcua" in item.nodeid.lower():
            opcua_items.append(item)
        else:
            other_items.append(item)

    items[:] = opcua_items + other_items
