# This module implements the functionality of docstring inheritance.
# Todo: Inheritance from method.
from typing import Dict, Iterator, List, Tuple

from mkapi.core.base import Item, Section, Type
from mkapi.core.node import Node, get_node


def get_params(node: Node, name: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    section = node.docstring[name]
    if section is None:
        docstring_params = {}
    else:
        docstring_params = {item.name: item.type.name for item in section.items}
    signature_params = node.object.signature[name]
    return docstring_params, signature_params


def is_complete(node: Node, name: str = "") -> bool:
    if not name:
        return all(is_complete(node, name) for name in ["Parameters", "Attributes"])

    docstring_params, signature_params = get_params(node, name)
    for param in signature_params:
        if param not in docstring_params:
            return False
    return True


def inherit_base(node: Node, base: Node, name: str = ""):
    if not name:
        for name in ["Parameters", "Attributes"]:
            inherit_base(node, base, name)
        return

    base_section = base.docstring[name]
    if base_section is None:
        return
    _, node_params = get_params(node, name)
    _, base_params = get_params(base, name)
    node_section = node.docstring[name]
    items = []
    for item in base_section:
        if node_section is None or item.name not in node_section:
            if (
                item.name in node_params
                and node_params[item.name] == base_params[item.name]
            ):
                items.append(item)
    if node_section is not None:
        for item in node_section.items:
            if item not in items:
                items.append(item)
    node.docstring[name] = Section(name, items=items)  # type:ignore


def inherit_signature(node: Node, name: str = ""):
    if not name:
        for name in ["Parameters", "Attributes"]:
            inherit_signature(node, name)
        return

    _, params = get_params(node, name)
    if not params:
        return

    node_section = node.docstring[name]
    items = []
    for item_name, type in params.items():
        if node_section is None or item_name not in node_section:
            item = Item(item_name, markdown="", type=Type(type))
        else:
            item = node_section[item_name]  # type:ignore
        items.append(item)
    node.docstring[name] = Section(name, items=items)


def inherit(node: Node, strict: bool = False):
    for node, bases in get_bases(node):
        if is_complete(node):
            continue
        for base in bases:
            inherit_base(node, base)
            if is_complete(node):
                break
        if strict:
            inherit_signature(node)


def get_bases(node: Node) -> Iterator[Tuple[Node, Iterator[Node]]]:
    bases = node.obj.mro()[:-1]
    yield node, (get_node(base) for base in bases)
    for member in node.members:
        name = member.object.name

        def gen(name=name):
            for base in bases:
                if hasattr(base, name):
                    yield get_node(getattr(base, name))

        yield member, gen()


def inherit_by_filters(node: Node, filters: List[str]):
    if node.object.kind in ["class", "dataclass"]:
        if "inherit" in filters:
            inherit(node)
        elif "strict" in filters:
            inherit(node, strict=True)