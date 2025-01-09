import dagmc
from pymoab import core, types
import numpy as np

mb = core.Core()
model = dagmc.DAGModel(mb)
volume = dagmc.Volume.create(model, 1)
# Step 1: Create vertices for a unit cube (x, y, z)
vertices_coords = np.array(
    [
        (0, 0, 0),  # Vertex 0
        (1, 0, 0),  # Vertex 1
        (1, 1, 0),  # Vertex 2
        (0, 1, 0),  # Vertex 3
        (0, 0, 1),  # Vertex 4
        (1, 0, 1),  # Vertex 5
        (1, 1, 1),  # Vertex 6
        (0, 1, 1),  # Vertex 7
    ],
    dtype="float64",
).flatten()

vertices = mb.create_vertices(vertices_coords)

# Step 2: Define triangular faces for the cube's 6 surfaces
# Each surface has two triangles
tri_faces = [
    # Bottom face (z = 0)
    (vertices[0], vertices[1], vertices[2]),
    (vertices[0], vertices[2], vertices[3]),
    # Top face (z = 1)
    (vertices[4], vertices[5], vertices[6]),
    (vertices[4], vertices[6], vertices[7]),
    # Front face (y = 0)
    (vertices[0], vertices[1], vertices[5]),
    (vertices[0], vertices[5], vertices[4]),
    # Back face (y = 1)
    (vertices[3], vertices[2], vertices[6]),
    (vertices[3], vertices[6], vertices[7]),
    # Left face (x = 0)
    (vertices[0], vertices[3], vertices[7]),
    (vertices[0], vertices[7], vertices[4]),
    # Right face (x = 1)
    (vertices[1], vertices[2], vertices[6]),
    (vertices[1], vertices[6], vertices[5]),
]

triangles = [mb.create_element(types.MBTRI, face) for face in tri_faces]

# Step 3: Group triangles into surface sets
surface_sets = []
surf_objs = []
for i in range(6):
    surface_set = mb.create_meshset()
    mb.add_entities(
        surface_set, triangles[i * 2 : i * 2 + 2]
    )  # Add 2 triangles per surface

    # Tag surface sets with GEOM_DIMENSION = 2
    geom_dim_tag = mb.tag_get_handle(
        "GEOM_DIMENSION",
        1,
        types.MB_TYPE_INTEGER,
        types.MB_TAG_DENSE,
        create_if_missing=True,
    )
    mb.tag_set_data(geom_dim_tag, surface_set, 2)

    surface_sets.append(surface_set)
    surface = dagmc.Surface.create(model, i + 1)
    surface.handle = surface_set
    surface.surf_sense = [volume, None]

print(model.surfaces)
# Link the surfaces as children of the volume
for surface in model.surfaces:
    mb.add_parent_child(volume.handle, surface.handle)

print(model.volumes)
print(model.surfaces)
model.write_file("example.vtk")
