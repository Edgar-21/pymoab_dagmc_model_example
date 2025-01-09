import dagmc
from pymoab import core, types
import numpy as np

mb = core.Core()
model = dagmc.DAGModel(mb)
group = dagmc.Group.create(model, name="iron", group_id=1)
volume = dagmc.Volume.create(model, 1)
group.add_set(volume)

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
    (vertices[3], vertices[2], vertices[0]),
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

# Create triangles with proper orientation, not best method for multiple volumes
triangles = []
for face in tri_faces:
    tri = mb.create_element(types.MBTRI, face)
    area = mb.get_measure(
        tri
    )  # This gives you signed area; negative means inward normal
    if area < 0:
        mb.set_connectivity(tri, [face[0], face[2], face[1]])  # Reverse orientation
    triangles.append(tri)

# Assign triangles to surfaces
for i in range(6):
    surface = dagmc.Surface.create(model, i + 1, sense=[volume, None])
    mb.add_entities(surface.handle, triangles[i * 2 : i * 2 + 2])

for surface in model.surfaces:
    mb.add_parent_child(volume.handle, surface.handle)

# Output and verification
print(model.volumes)
print(model.surfaces)
model.write_file("example.vtk")
model.write_file("example.stl")
model.write_file("example.h5m")

# Check and print the calculated volume
print("Calculated volume:", model.volumes[0].volume)
print("All surfaces have sense set:", all(surf.surf_sense for surf in model.surfaces))
print("Groups:", model.groups)
