"""Group the DIRIGERA hub's per-function 'devices' into one HA device per physical product.

The hub exposes a multi-function product (e.g. an air quality sensor, a multi-button
remote, a plug with energy metering) as several devices, each with its own `id`.
All parts of the same physical product share a `relationId`, so we use that as the
Home Assistant device identifier instead of the per-function id.
"""
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

# group id -> {hub device id -> owner object exposing a live `_json_data`}
_groups: dict[str, dict[str, object]] = {}


def group_id(json_data) -> str:
    """HA device identifier for a hub device: its relationId if it has one, else its id."""
    relation_id = getattr(json_data, "relation_id", None)
    return relation_id if relation_id else json_data.id


def register(owner) -> None:
    """Register an object holding `_json_data` (kept live, so renames are picked up)."""
    json_data = owner._json_data
    _groups.setdefault(group_id(json_data), {})[json_data.id] = owner


def group_id_for_hub_id(hub_id: str) -> str:
    for gid, members in _groups.items():
        if hub_id in members:
            return gid
    return hub_id


def is_grouped_member(hub_id: str) -> bool:
    """True if this hub id is merged into a device identified by something else."""
    return group_id_for_hub_id(hub_id) != hub_id


def _primary(json_data):
    """Deterministically pick the member whose name/metadata represents the device."""
    members = _groups.get(group_id(json_data))
    if not members:
        return json_data
    ordered = [members[k]._json_data for k in sorted(members)]
    for member in ordered:
        if member.attributes.custom_name:
            return member
    return ordered[0]


def device_name(json_data) -> str:
    primary = _primary(json_data)
    return primary.attributes.custom_name or primary.id


def device_info(json_data) -> DeviceInfo:
    primary = _primary(json_data)
    return DeviceInfo(
        identifiers={(DOMAIN, group_id(json_data))},
        name=device_name(json_data),
        manufacturer=primary.attributes.manufacturer,
        model=primary.attributes.model,
        sw_version=primary.attributes.firmware_version,
        serial_number=primary.attributes.serial_number,
        suggested_area=primary.room.name if primary.room is not None else None,
    )
