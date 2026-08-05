"""Convert parsed Mermaid diagrams into blockbom projects."""

from .models import ParsedDiagram, PartMetadata, Subgraph
from .project import Component, Connection, Part, Project


def diagram_to_project(
    diagram: ParsedDiagram,
    metadata: dict[str, PartMetadata] | None = None,
    name: str = "Imported Project",
) -> Project:
    """Build a Project from a parsed Mermaid diagram.

    Subgraphs become components with children, nodes become leaf components,
    and edges become connections. Metadata entries with a part_number are
    collected into the parts library; entries without one become inline
    component fields.
    """
    metadata = metadata or {}
    parts: dict[str, Part] = {}

    def make_component(
        component_id: str,
        component_name: str,
        children: list[Component] | None = None,
    ) -> Component:
        meta = metadata.get(component_id)
        part_ref: str | None = None
        cost: float | None = None
        link: str | None = None
        if meta is not None:
            if meta.part_number:
                part_ref = meta.part_number
                if part_ref not in parts:
                    parts[part_ref] = Part(
                        description=component_name,
                        link=meta.link,
                        cost=meta.cost,
                    )
            else:
                cost = meta.cost
                link = meta.link
        return Component(
            id=component_id,
            name=component_name,
            part=part_ref,
            cost=cost,
            link=link,
            children=children or [],
        )

    def convert_subgraph(subgraph: Subgraph) -> Component:
        children = [
            make_component(node_id, _node_label(diagram, node_id)) for node_id in subgraph.node_ids
        ]
        children.extend(convert_subgraph(child) for child in subgraph.children)
        return make_component(subgraph.id, subgraph.title, children)

    components = [convert_subgraph(sg) for sg in diagram.subgraphs if sg.parent_id is None]
    components.extend(
        make_component(node_id, _node_label(diagram, node_id)) for node_id in diagram.root_node_ids
    )

    # Edge endpoints never defined as nodes still belong in the diagram
    known_ids = {c.id for component in components for c in component.walk()}
    for edge in diagram.edges:
        for endpoint in (edge.source_id, edge.target_id):
            if endpoint not in known_ids:
                components.append(make_component(endpoint, endpoint))
                known_ids.add(endpoint)

    connections = [
        Connection.model_validate(
            {"from": edge.source_id, "to": edge.target_id, "label": edge.label}
        )
        for edge in diagram.edges
    ]

    return Project(name=name, components=components, connections=connections, parts=parts)


def _node_label(diagram: ParsedDiagram, node_id: str) -> str:
    node = diagram.nodes.get(node_id)
    return node.label if node is not None else node_id
