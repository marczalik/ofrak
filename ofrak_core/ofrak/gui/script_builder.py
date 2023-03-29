from dataclasses import dataclass
from enum import IntEnum
import re
import os
from typing import Dict, List, Optional, Tuple
from ofrak.model.resource_model import ResourceIndexedAttribute
from ofrak.core.filesystem import FilesystemEntry
from ofrak.model.resource_model import Data
from ofrak.service.resource_service_i import ResourceAttributeValueFilter, ResourceFilter
from black import format_str, FileMode

from ofrak.resource import Resource


class SelectableAttributesError(Exception):
    """
    Prompt the user for an attribute to select with
    """


class ActionType(IntEnum):
    UNPACK = 0
    MOD = 1
    PACK = 2
    UNDEF = 3


@dataclass
class ScriptAction:
    """
    Encapsulates the structure of a single action within the script, which consists of the string
    representation of the code for that action and the action's type.
    """

    action_type: ActionType
    action: str


class ScriptSession:
    """
    A script, consisting of an ordered sequence of script actions and a mapping between resources
    and their autogenerated variable names.
    """

    actions: List[ScriptAction] = []
    resource_variable_names: Dict[bytes, str] = {}
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
            Data.Offset,
        ]

    async def add_action(
        self,
        resource: Resource,
        action: str,
        action_type: ActionType,
    ) -> None:
        """
        :param action:
        :param action_type:
        """
        var_name = await self.add_variable(resource)
        qualified_action = action.format(resource=var_name)
        await self._add_action_to_session(resource, qualified_action, action_type)

    async def add_variable(self, resource: Resource) -> bytes:
        if await self._var_exists(resource):
            return await self._get_variable_from_session(resource)

        root_resource = await self._get_root_resource(resource)
        if resource.get_id() == root_resource.get_id():
            await self._add_variable_to_session(resource, "root_resource")
            return "root_resource"

        parent = await resource.get_parent()
        if not await self._var_exists(parent):
            await self.add_variable(parent)

        selector = await self._get_selector(resource)
        name = await self._generate_name(resource)
        await self._add_action_to_session(
            resource,
            rf"""
        {name} = {selector}""",
            ActionType.UNDEF,
        )
        await self._add_variable_to_session(resource, name)
        return name

    async def delete_action(self, resource: Resource, action: str) -> None:
        """
        :param action:
        """
        root_resource = await self._get_root_resource(resource)
        session = self._get_session(root_resource.get_id())
        # TODO: do we really need to delete an action from the script?
        for idx, script_action in enumerate(session.actions):
            if script_action.action == action:
                session.actions.pop(idx)
                break

    async def get_script(self, resource: Resource) -> str:
        """
        :return script:
        """
        root_resource = await self._get_root_resource(resource)
        return self._get_script(root_resource.get_id())

    async def get_all_of_type(self, resource: Resource, target_type: ActionType) -> str:
        """
        :param target_type:
        :return script:
        """
        root_resource = await self._get_root_resource(resource)
        return self._get_script(root_resource.get_id(), target_type)

    async def _get_root_resource(self, resource: Resource) -> Resource:
        if resource.get_id() in self.root_cache:
            return self.root_cache[resource.get_id()]
        while len(list(await resource.get_ancestors())) != 0:
            resource = await resource.get_parent()
        self.root_cache[resource.get_id()] = resource
        return resource

    async def _get_variable_from_session(self, resource: Resource):
        root_resource = await self._get_root_resource(resource)
        return self.script_sessions[root_resource.get_id()].resource_variable_names[
            resource.get_id()
        ]

    async def _var_exists(self, resource: Resource):
        root_resource = await self._get_root_resource(resource)
        session = self._get_session(root_resource)
        return resource.get_id() in session.resource_variable_names

    async def _add_action_to_session(self, resource, action, action_type):
        root_resource = await self._get_root_resource(resource)
        session = self._get_session(root_resource.get_id())
        # TODO: actions are duplicated if page is refreshed, is this reasonable?
        session.actions.append(ScriptAction(action_type, action))

    async def _add_variable_to_session(self, resource: Resource, var_name: str):
        root_resource = await self._get_root_resource(resource)
        session = self._get_session(root_resource.get_id())
        session.resource_variable_names[resource.get_id()] = var_name

    async def _get_selector(self, resource: Resource) -> str:
        root_resource = await self._get_root_resource(resource)
        for ancestor in await resource.get_ancestors():
            if (
                ancestor.get_id()
                in self.script_sessions[root_resource.get_id()].resource_variable_names
            ):
                break
        attribute, attribute_value = await self._get_selectable_attribute(resource)
        try:
            result = await ancestor.get_only_descendant(
                r_filter=ResourceFilter(
                    tags=resource.get_most_specific_tags(),
                    attribute_filters=[
                        ResourceAttributeValueFilter(attribute=attribute, value=attribute_value)
                    ],
                )
            )
        except:
            raise SelectableAttributesError(
                f"Resource with ID {resource.get_id()} cannot be uniquely identified by attribute "
                f"{attribute.__name__} (resource has value {attribute_value})."
            )
        if isinstance(attribute_value, str) or isinstance(attribute_value, bytes):
            attribute_value = f'"{attribute_value}"'.rstrip()
        var_name = self.script_sessions[root_resource.get_id()].resource_variable_names[ancestor.get_id()]
        return f"""await {name}.get_only_child(
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

    async def _get_selectable_attribute(
        self, resource: Resource
    ) -> Tuple[ResourceIndexedAttribute, any]:
        attribute_collisions = {}
        for attribute in self.selectable_indexes:
            if resource.has_attributes(attribute.attributes_owner):
                attribute_value = attribute.get_value(resource.get_model())
                parent = await resource.get_parent()
                children = list(await parent.get_children(
                    r_filter=ResourceFilter(
                        tags=resource.get_most_specific_tags(),
                        attribute_filters=[ResourceAttributeValueFilter(
                            attribute=attribute,
                            value=attribute_value)
                        ])
                    ))
                if len(children) > 1:
                    attribute_collisions[attribute.__name__] = attribute_value
                    continue
                return attribute, attribute_value
        if len(attribute_collisions) == 0:
            raise SelectableAttributesError(
                f"Resource with ID {resource.get_id()} does not have a selectable attribute."
            )
        else:
            msg = []
            for collision, value in attribute_collisions.items(): 
                msg.append(f"Resource with ID {resource.get_id()} cannot be uniquely identified by attribute {attribute.__name__} (resource has value {attribute_value}).")
            raise SelectableAttributesError("\n".join(msg))

    async def _generate_name(self, resource: Resource) -> str:
        root_resource = await self._get_root_resource(resource)
        most_specific_tag = list(resource.get_most_specific_tags())[0].__name__.lower()
        _, selectable_attribute_value = await self._get_selectable_attribute(resource)
        name = f"{most_specific_tag}_{selectable_attribute_value}"
        name = re.sub(r"[^a-zA-Z0-9]", "_", name)
        if name in self.script_sessions[root_resource.get_id()].resource_variable_names.values():
            parent = await resource.get_parent()
            return f"{self.script_sessions[root_resource.get_id()].resource_variable_names[parent.get_id()]}_{name}"
        return name

    def _get_session(self, resource_id: bytes) -> ScriptSession:
        session = self.script_sessions.get(resource_id, None)
        if session is None:
            session = ScriptSession()
            self.script_sessions[resource_id] = session

        return session

    def _get_script(self, resource_id: bytes, target_type: Optional[ActionType] = None) -> str:
        script = []
        script.append(self.script_sessions[resource_id].boilerplate_header)
        for script_action in self.script_sessions[resource_id].actions:
            # Always include UNDEF actions like variable assignments
            if (
                target_type is None
                or script_action.action_type == target_type
                or script_action.action_type == ActionType.UNDEF
            ):
                script.append(script_action.action)
        script.append(self.script_sessions[resource_id].boilerplate_footer)
        script = "\n".join(script)
        script = self._dedent(script)
        res = format_str("\n".join(script), mode=FileMode())
        script = res.split("\n")
        return script

    def _dedent(self, s):
        split = list(s.splitlines())
        prefix = os.path.commonprefix([line for line in split if line])
        indent_matches = re.findall(r"^\s+", prefix)
        if not indent_matches:
            return s
        indent_end_index = len(indent_matches[0])
        return [line[indent_end_index:] if line and line.startswith(prefix) else "" for line in split]
