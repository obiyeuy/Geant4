from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MeshData:
    vertices: list[tuple[float, float, float]]
    faces: list[tuple[int, int, int]]
    solid_name: str


def load_tessellated_mesh(gdml_path: Path) -> MeshData | None:
    if not gdml_path.exists():
        return None

    root = ET.fromstring(gdml_path.read_text(encoding="utf-8"))
    define = root.find("define")
    solids = root.find("solids")
    if define is None or solids is None:
        return None

    positions: dict[str, tuple[float, float, float]] = {}
    for pos in define.findall("position"):
        name = pos.attrib.get("name", "")
        if not name:
            continue
        try:
            positions[name] = (
                float(pos.attrib.get("x", "0")),
                float(pos.attrib.get("y", "0")),
                float(pos.attrib.get("z", "0")),
            )
        except ValueError:
            continue

    tess = solids.find("tessellated")
    if tess is None:
        return None

    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    vertex_index: dict[tuple[float, float, float], int] = {}

    def _idx_for(v: tuple[float, float, float]) -> int:
        if v in vertex_index:
            return vertex_index[v]
        idx = len(vertices)
        vertices.append(v)
        vertex_index[v] = idx
        return idx

    for tri in tess.findall("triangular"):
        ref1 = tri.attrib.get("vertex1", "")
        ref2 = tri.attrib.get("vertex2", "")
        ref3 = tri.attrib.get("vertex3", "")
        if ref1 not in positions or ref2 not in positions or ref3 not in positions:
            continue
        i = _idx_for(positions[ref1])
        j = _idx_for(positions[ref2])
        k = _idx_for(positions[ref3])
        faces.append((i, j, k))

    if not vertices or not faces:
        return None

    return MeshData(vertices=vertices, faces=faces, solid_name=tess.attrib.get("name", "tessellated"))
