import dagmc
from pymoab import core, types


def duplicate_vertices(src_mb, dst_mb, vertices):
    coords = src_mb.get_coords(vertices)
    new_vertices = dst_mb.create_vertices(coords)
    return new_vertices


mbc = core.Core()

origin_cube = dagmc.DAGModel("origin_cube.h5m")
shifted_cube = dagmc.DAGModel("two_cubes_shifted.h5m")
print(shifted_cube.groups)
merged_model = dagmc.DAGModel(mbc)

all_models = [origin_cube, shifted_cube]
vert_index = 0

vertex_mapping = {}
new_vertices = []
for model in all_models:
    vertex_mapping[model] = {}
    # pymoab range of vertex handles
    all_vertices = model.mb.get_entities_by_type(
        model.mb.get_root_set(), types.MBVERTEX
    )
    indices = list(range(vert_index, vert_index + len(all_vertices)))
    vertex_mapping[model]["verts"] = all_vertices
    vertex_mapping[model]["indices"] = indices
    vertex_mapping[model]["map"] = dict(zip(all_vertices, indices))
    vert_index += len(all_vertices)
    new_vertices.extend(
        duplicate_vertices(model.mb, merged_model.mb, all_vertices)
    )


# for each model
# add the surfaces to the new model
surface_mapping = {}
for surface in origin_cube.surfaces + shifted_cube.surfaces:
    new_surface = dagmc.Surface.create(merged_model)
    for tri in surface.triangle_handles:
        verts = surface.model.mb.get_connectivity(tri)
        indices = [
            vertex_mapping[surface.model]["map"][vert] for vert in verts
        ]
        new_verts = [new_vertices[i] for i in indices]
        new_tri = merged_model.mb.create_element(types.MBTRI, new_verts)
        merged_model.mb.add_entities(new_surface.handle, [new_tri])
    surface_mapping[new_surface.id] = (surface.model, surface.id)

merged_model.write_file("all_surfaces.vtk")

# create a new volume for each volume in the model
volume_mapping = {}
for model in [origin_cube, shifted_cube]:
    volume_mapping[model] = {}
    for volume in model.volumes:
        new_volume = dagmc.Volume.create(merged_model)
        volume_mapping[model][volume.id] = new_volume.id

print(volume_mapping.values())

# surface sense stuff
for surface in merged_model.surfaces:
    original_model, original_id = surface_mapping[surface.id]
    surf_sens = []
    print(surface)
    for vol in original_model.surfaces_by_id[original_id].surf_sense:
        if vol is None:
            surf_sens.append(vol)
        else:
            surf_sens.append(
                merged_model.volumes_by_id[
                    volume_mapping[original_model][vol.id]
                ]
            )
    surface.surf_sense = surf_sens


# group stuff
for volume in list(origin_cube.volumes) + list(shifted_cube.volumes):
    model = volume.model
    group = volume.groups[0]
    new_volume = merged_model.volumes_by_id[volume_mapping[model][volume.id]]
    new_group = dagmc.Group.create(merged_model, name=group.name)
    new_group.add_set(new_volume)

print(merged_model.groups)

merged_model.write_file("merged.vtk")
merged_model.write_file("merged.h5m")

for surface in merged_model.surfaces:
    print(surface)
    print(surface.surf_sense)
    print("\n")
