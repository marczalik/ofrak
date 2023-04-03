from dataclasses import dataclass, field
from enum import IntEnum
import logging
import re
import os
from typing import Any, Dict, List, Optional, Tuple
from ofrak.model.resource_model import ResourceIndexedAttribute
from ofrak.resource import Resource
from ofrak.core.dtb import DtbNode, DtbProperty
from ofrak.core import Addressable
from ofrak.core.filesystem import FilesystemEntry
from ofrak.model.resource_model import Data
from ofrak.service.resource_service_i import ResourceAttributeValueFilter, ResourceFilter
from black import format_str, FileMode


LOGGER = logging.getLogger(__name__)


class SelectableAttributesError(Exception):
    """
    Prompt the user for an attribute to select with
    """


class ActionType(IntEnum):
    UNPACK = 0
    MOD = 1
    PACK = 2
    UNDEF = 3


@dataclass(frozen=True)
class ScriptAction:
    """
    Encapsulates the structure of a single action within the script, which consists of the string
    representation of the code for that action and the action's type.
    """

    action_type: ActionType
    action: str


@dataclass
class ScriptSession:
    """
    A script, consisting of an ordered sequence of script actions and a mapping between resources
    and their autogenerated variable names.
    """

    actions_queue: List[ScriptAction] = field(default_factory=list)
    actions: List[ScriptAction] = field(default_factory=list)
    resource_variable_names: Dict[bytes, str] = field(default_factory=dict)
    resource_variable_names_queue: Dict[bytes, str] = field(default_factory=dict)

    boilerplate_header: str = r"""
    from ofrak import *
    from ofrak.core import *

    async def main(ofrak_context: OFRAKContext):"""
    # TODO: Replace with backend in use by OFRAK instance used to create the script.
    boilerplate_footer: str = r"""
    if __name__ == "__main__":
        if False:
            import ofrak_angr
            import ofrak_capstone
            ofrak.discover(ofrak_capstone)
            ofrak.discover(ofrak_angr)

        if False:
            import ofrak_binary_ninja
            import ofrak_capstone
            ofrak.discover(ofrak_capstone)
            ofrak.discover(ofrak_binary_ninja)

        if False:
            import ofrak_ghidra
            ofrak.discover(ofrak_ghidra)

        ofrak = OFRAK()
        ofrak.run(main)
    """

    def get_var_name(self, id):
        if id in self.resource_variable_names:
            return self.resource_variable_names[id]
        elif id in self.resource_variable_names_queue:
            return self.resource_variable_names_queue[id]
        else:
            raise ValueError(f"No variable name for resource ID {id}")


class ScriptBuilder:
    """
    Builds and maintains runnable OFRAK scripts as sequences of actions, with each script tied to
    a session.
    """

    def __init__(self):
        self.root_cache: Dict[bytes, Resource] = {}
        self.script_sessions: Dict[bytes, ScriptSession] = {}
        self.selectable_indexes: List[ResourceIndexedAttribute] = [
            FilesystemEntry.Name,
            Addressable.VirtualAddress,
            Data.Offset,
            DtbNode.DtbNodeName,
            DtbProperty.DtbPropertyName,
        ]

    async def add_action(
        self,
        resource: Resource,
        action: str,
        action_type: ActionType,
    ) -> None:
        """
        Adds an action to the script session to which the selected resource belongs. An action is
        a string representing the code that is being run on the resource based on an action that
        has occurred in the GUI.

        :param resource: Resource upon which the action is being taken
        :param action: A string describing the code being run based on a GUI action
        :param action_type: An instance of `ActionType` categorizing the action
        """
        var_name = await self._add_variable(resource)
        qualified_action = action.format(resource=var_name)
        await self._add_action_to_session_queue(resource, qualified_action, action_type)

    async def get_script(self, resource: Resource) -> List[str]:
        """
        Returns the most up-to-date version of the script for the session to which the resource
        belongs.

        :param resource: Resource belonging to the session for which the script is to be returned

        :return: List of strings where each entry is a line in the script
        """
        root_resource = await self._get_root_resource(resource)
        return self._get_script(root_resource.get_id())

    async def commit_to_script(self, resource: Resource):
        root_resource = await self._get_root_resource(resource)
        session = self._get_session(root_resource.get_id())
        for id, name in session.resource_variable_names_queue.items():
            session.resource_variable_names[id] = name
        session.actions += session.actions_queue
        session.actions_queue = []
        session.resource_variable_names_queue = {}

    async def _add_variable(self, resource: Resource) -> str:
        """
        Replaces references to a particular resource selected in the GUI with a generated variable
        name based on uniquely identifying characteristics of the resource. This overcomes the issue
        of referencing the same resource across OFRAK contexts due to the randomly generated
        resource IDs changing.

        :param resource: Resource that needs to be uniquely identified in the script

        :return: a unique variable name
        """
        if await self._var_exists(resource):
            return await self._get_variable_from_session(resource)

        root_resource = await self._get_root_resource(resource)
        if resource.get_id() == root_resource.get_id():
            await self._add_variable_to_session_queue(resource, "root_resource")
            return "root_resource"

        parent = await resource.get_parent()
        if not await self._var_exists(parent):
            await self._add_variable(parent)

        name = ""
        # Cannot propagate exceptions to the server as this would interfere with user actions
        # regardless of whether they're interested in the script. Currently only _get_selector()
        # and _generate_name() can lead to exceptions raised within ScriptBuilder.
        try:
            selector = await self._get_selector(resource)
            name = await self._generate_name(resource)
            await self._add_action_to_session_queue(
                resource,
                rf"""
        {name} = {selector}""",
                ActionType.UNDEF,
            )
            await self._add_variable_to_session_queue(resource, name)
        except SelectableAttributesError as e:
            parent_name = await self._get_variable_from_session(parent)
            name = f"{parent_name}_MISSING_RESOURCE"
            await self._add_action_to_session_queue(
                resource,
                f"""
        # Resource with parent {parent_name} is missing, could not find selectable attributes.
        raise RuntimeError(\"{str(e)}\")""",
                ActionType.UNDEF,
            )
            await self._add_variable_to_session_queue(resource, name)
            LOGGER.exception("Could not find selectable attributes for resource")
        except:
            LOGGER.exception("Exception raised in add_variable")
        return name

    async def _get_root_resource(self, resource: Resource) -> Resource:
        """
        Maps a given resource to its root for efficient retrieval of the root resource because
        getting the root resource is likely the most performed operation in `ScriptBuilder`.
        """
        resource_id = resource.get_id()
        if resource_id in self.root_cache:
            return self.root_cache[resource_id]
        while len(list(await resource.get_ancestors())) != 0:
            resource = await resource.get_parent()
        self.root_cache[resource_id] = resource
        return resource

    async def _get_variable_from_session(self, resource: Resource) -> str:
        root_resource = await self._get_root_resource(resource)
        session = self._get_session(root_resource.get_id())
        return session.get_var_name(resource.get_id())

    async def _var_exists(self, resource: Resource):
        root_resource = await self._get_root_resource(resource)
        session = self._get_session(root_resource.get_id())
        return (
            resource.get_id() in session.resource_variable_names
            or resource.get_id() in session.resource_variable_names_queue
        )

    async def _add_action_to_session_queue(self, resource, action, action_type):
        root_resource = await self._get_root_resource(resource)
        session = self._get_session(root_resource.get_id())
        session.actions_queue.append(ScriptAction(action_type, action))

    async def _add_variable_to_session_queue(self, resource: Resource, var_name: str) -> None:
        root_resource = await self._get_root_resource(resource)
        session = self._get_session(root_resource.get_id())
        session.resource_variable_names_queue[resource.get_id()] = var_name

    async def _test_selectable_attributes(self, ancestor, resource, attribute, attribute_value):
        try:
            result = await ancestor.get_only_child(
                r_filter=ResourceFilter(
                    attribute_filters=[
                        ResourceAttributeValueFilter(attribute=attribute, value=attribute_value)
                    ],
                )
            )
        except Exception as e:
            raise SelectableAttributesError(
                f"Resource with ID 0x{resource.get_id().hex()} cannot be uniquely identified by attribute "
                f"{attribute.__name__} (resource has value {attribute_value})."
            )

    async def _get_selector(self, resource: Resource) -> str:
        root_resource = await self._get_root_resource(resource)
        session = self._get_session(root_resource.get_id())
        parent = await resource.get_parent()
        attribute, attribute_value = await self._get_selectable_attribute(resource)
        await self._test_selectable_attributes(parent, resource, attribute, attribute_value)

        if isinstance(attribute_value, str) or isinstance(attribute_value, bytes):
            attribute_value = f'"{attribute_value!s}"'.rstrip()
        return f"""await {session.get_var_name(parent.get_id())}.get_only_child(
                    r_filter=ResourceFilter(
                        tags={resource.get_most_specific_tags()},
                        attribute_filters=[
                            ResourceAttributeValueFilter(
                                attribute={attribute.__name__}, 
                                value={attribute_value}
                            )
                        ]   
                    )
                )"""

    async def _get_self_and_siblings_matching_attribute(
        self, resource: Resource, attribute: ResourceIndexedAttribute, attribute_value: Any
    ) -> List[Resource]:
        parent = await resource.get_parent()
        children = list(
            await parent.get_children(
                r_filter=ResourceFilter(
                    attribute_filters=[
                        ResourceAttributeValueFilter(attribute=attribute, value=attribute_value)
                    ],
                )
            )
        )
        return children

    async def _get_selectable_attribute(
        self, resource: Resource
    ) -> Tuple[ResourceIndexedAttribute, Any]:
        attribute_collisions = {}
        for attribute in self.selectable_indexes:
            if attribute.attributes_owner and resource.has_attributes(attribute.attributes_owner):
                attribute_value = attribute.get_value(resource.get_model())
                children = await self._get_self_and_siblings_matching_attribute(
                    resource, attribute, attribute_value
                )
                if len(children) == 1:
                    return attribute, attribute_value
                elif len(children) > 1:
                    attribute_collisions[attribute.__name__] = attribute_value
                    continue
        if len(attribute_collisions) == 0:
            raise SelectableAttributesError(
                f"Resource with ID 0x{resource.get_id().hex()} does not have a selectable attribute."
            )
        else:
            msg = []
            for collision, value in attribute_collisions.items():
                msg.append(
                    f"Resource with ID 0x{resource.get_id().hex()} cannot be uniquely identified by attribute {collision} (resource has value {value})."
                )
            raise SelectableAttributesError("\n".join(msg))

    async def _generate_name(self, resource: Resource) -> str:
        root_resource = await self._get_root_resource(resource)
        session = self._get_session(root_resource.get_id())
        most_specific_tag = list(resource.get_most_specific_tags())[0].__name__.lower()
        _, selectable_attribute_value = await self._get_selectable_attribute(resource)
        if isinstance(selectable_attribute_value, int):
            selectable_attribute_value = hex(selectable_attribute_value)
        name = f"{most_specific_tag}_{selectable_attribute_value}"
        name = re.sub(r"[^a-zA-Z0-9]", "_", name)
        if name in session.resource_variable_names.values():
            parent = await resource.get_parent()
            return f"{session.get_var_name(parent.get_id())}_{name}"
        return name

    def _get_session(self, resource_id: bytes) -> ScriptSession:
        session = self.script_sessions.get(resource_id, None)
        if session is None:
            session = ScriptSession()
            self.script_sessions[resource_id] = session

        return session

    def _get_script(
        self, resource_id: bytes, target_type: Optional[ActionType] = None
    ) -> List[str]:
        script_list: List[str] = []
        script_list.append(self.script_sessions[resource_id].boilerplate_header)
        for script_action in self.script_sessions[resource_id].actions:
            # Always include UNDEF actions like variable assignments
            if (
                target_type is None
                or script_action.action_type == target_type
                or script_action.action_type == ActionType.UNDEF
            ):
                script_list.append(script_action.action)
        script_list.append(self.script_sessions[resource_id].boilerplate_footer)
        script_str = "\n".join(script_list)
        script_str = self._dedent(script_str)
        try:
            res = format_str(script_str, mode=FileMode())
            script_list = res.split("\n")
        except Exception as e:
            logging.exception("Black Formatting Error:")
            logging.exception(e)
            script_list = script_str.split("\n")
        return script_list

    def _dedent(self, s: str) -> str:
        split = list(s.splitlines())
        prefix = os.path.commonprefix([line for line in split if line])
        indent_matches = re.findall(r"^\s+", prefix)
        if not indent_matches:
            return s
        indent_end_index = len(indent_matches[0])
        dedented_strings = [
            line[indent_end_index:] if line and line.startswith(prefix) else "" for line in split
        ]
        return "\n".join(dedented_strings)
