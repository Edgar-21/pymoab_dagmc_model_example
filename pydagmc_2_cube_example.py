import dagmc
from pymoab import core, types
import numpy as np

mb = core.Core()

model = dagmc.DAGModel(mb)
iron_group = dagmc.Group.create(model, name="mat:iron", group_id=1)
w_group = dagmc.Group.create(model, name="mat:tungsten", group_id=2)
volume_1 = dagmc.Volume.create(model, 1)
volume_2 = dagmc.Volume.create(model, 2)
iron_group.add_set(volume_1)
w_group.add_set(volume_2)

cube_1_vertices_coords = (
    np.array(
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
    * 10
)

cube_2_vertices_coords = (
    np.array(
        [
            (1, 0, 0),  # Vertex 0
            (2, 0, 0),  # Vertex 1
            (2, 1, 0),  # Vertex 2
            (1, 1, 0),  # Vertex 3
            (1, 0, 1),  # Vertex 4
            (2, 0, 1),  # Vertex 5
            (2, 1, 1),  # Vertex 6
            (1, 1, 1),  # Vertex 7
        ],
        dtype="float64",
    ).flatten()
    * 10
)

cube_1_verts = mb.create_vertices(cube_1_vertices_coords)
cube_2_verts = mb.create_vertices(cube_2_vertices_coords)

# last surface is the shared one
surface_verts = [
    # bottom faces, 0,1
    [
        (cube_1_verts[0], cube_1_verts[2], cube_1_verts[1]),
        (cube_1_verts[0], cube_1_verts[3], cube_1_verts[2]),
    ],
    [
        (cube_2_verts[0], cube_2_verts[2], cube_2_verts[1]),
        (cube_2_verts[0], cube_2_verts[3], cube_2_verts[2]),
    ],
    # top faces, 2,3
    [
        (cube_1_verts[4], cube_1_verts[5], cube_1_verts[6]),
        (cube_1_verts[4], cube_1_verts[6], cube_1_verts[7]),
    ],
    [
        (cube_2_verts[4], cube_2_verts[5], cube_2_verts[6]),
        (cube_2_verts[4], cube_2_verts[6], cube_2_verts[7]),
    ],
    # front faces, 4,5
    [
        (cube_1_verts[0], cube_1_verts[1], cube_1_verts[5]),
        (cube_1_verts[0], cube_1_verts[5], cube_1_verts[4]),
    ],
    [
        (cube_2_verts[0], cube_2_verts[1], cube_2_verts[5]),
        (cube_2_verts[0], cube_2_verts[5], cube_2_verts[4]),
    ],
    # back faces, 6,7
    [
        (cube_1_verts[6], cube_1_verts[2], cube_1_verts[3]),
        (cube_1_verts[7], cube_1_verts[6], cube_1_verts[3]),
    ],
    [
        (cube_2_verts[6], cube_2_verts[2], cube_2_verts[3]),
        (cube_2_verts[7], cube_2_verts[6], cube_2_verts[3]),
    ],
    # outside faces 8,9
    [
        (cube_1_verts[0], cube_1_verts[7], cube_1_verts[3]),
        (cube_1_verts[0], cube_1_verts[4], cube_1_verts[7]),
    ],
    [
        (cube_2_verts[5], cube_2_verts[1], cube_2_verts[2]),
        (cube_2_verts[6], cube_2_verts[5], cube_2_verts[2]),
    ],
    # shared face 10
    [
        (cube_1_verts[5], cube_1_verts[1], cube_1_verts[2]),
        (cube_1_verts[6], cube_1_verts[5], cube_1_verts[2]),
    ],
]

# make moab tris and put them in dagmc surfaces
for i, verts in enumerate(surface_verts):
    triangles = [mb.create_element(types.MBTRI, face) for face in verts]
    surface = dagmc.Surface.create(model, i + 1)
    mb.add_entities(surface.handle, triangles)
    for j, tri in enumerate(verts):
        coords = [np.array(mb.get_coords([v])) for v in tri]
        v0, v1, v2 = coords
        normal = np.cross(v1 - v0, v2 - v0)
        centroid = (v0 + v1 + v2) / 3

        if np.dot(centroid, normal) < 0:
            print(i, j)

# assign surface senses to surfaces
for surf in model.surfaces:
    if surf.id in [1, 3, 5, 7, 9]:
        surf.surf_sense = [volume_1, None]
    if surf.id in [2, 4, 6, 8, 10]:
        surf.surf_sense = [volume_2, None]
    if surf.id == 11:
        surf.surf_sense = [volume_1, volume_2]
    print(surf, surf.surf_sense)

for vol in model.volumes:
    print(vol, vol.volume)

model.write_file("2_cube_example.vtk")
model.write_file("2_cube_example.h5m")
