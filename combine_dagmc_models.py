import dagmc
from pymoab import core, types
import argparse


def duplicate_vertices(src_mb, dst_mb, vertices):
    """Copy vertices from one PyMOAB core instance to another

    Arguments:
        src_mb (PyMOAB core): PyMOAB core containing original vertices.
        dst_mb (PyMOAB core): PyMOAB core in which to duplicate the vertices.
        vertices (list of MBVERTEX handles): MBVERTEX handles in src_mb to
            to duplicate in dst_mb

    Returns:
        new_vertices (list of MBVERTEX handles): MBVERTEX handles added to
        dst_mb
    """
    coords = src_mb.get_coords(vertices)
    new_vertices = dst_mb.create_vertices(coords)
    return new_vertices


def build_vertex_map(all_models, merged_model):
    """Copies vertices from the list of models to be merged to the merged
    model PyMOAB core instance. Creates a map from original vertices to
    new vertices.

    Arguments:
        all_models (list of dagmc.DAGModel): List of models to be merged.
        merged_model (dagmc.DAGModel): Model in which models will be combined

    Returns:
        vertex_map (dict): {model containing original vertex (dagmc.DAGModel):
                {
                    original vertex handle (MBVERTEX entity handle):
                        corresponding merged_vertices index (int)
                }
            }
        merged_vertices (list of MBVERTEX entity handles): List of vertices in
            merged_model PyMOAB core instance. These are copied from each of
            the models to be merged.
    """

    vert_index = 0

    vertex_map = {}
    merged_vertices = []
    for model in all_models:
        vertex_map[model] = {}
        all_vertices = model.mb.get_entities_by_type(
            model.mb.get_root_set(), types.MBVERTEX
        )
        indices = list(range(vert_index, vert_index + len(all_vertices)))
        vertex_map[model]["map"] = dict(zip(all_vertices, indices))
        vert_index += len(all_vertices)
        merged_vertices.extend(
            duplicate_vertices(model.mb, merged_model.mb, all_vertices)
        )
    return vertex_map, merged_vertices


def build_surface_map(all_models, merged_model, vertex_map, merged_vertices):
    """Duplicates surfaces in each model to be merged in the merged_model.

    Arguments:
        all_models (list of dagmc.DAGModel): List of models to be merged.
        merged_model (dagmc.DAGModel): Model in which models will be combined.
        vertex_map (dict): {model containing original vertex (dagmc.DAGModel):
                {
                    original vertex handle (MBVERTEX entity handle):
                        corresponding merged_vertices index (int)
                }
            }
        merged_vertices (list of MBVERTEX entity handles): List of vertices in
            merged_model PyMOAB core instance. These are copied from each of
            the models to be merged.

        returns:
            surface_map (dict): {
                merged_model surface id (int):
                    (model containing original surface, original surface id)
            }
    """
    surface_map = {}
    for model in all_models:
        for surface in model.surfaces:
            new_surface = dagmc.Surface.create(merged_model)
            for tri in surface.triangle_handles:
                verts = surface.model.mb.get_connectivity(tri)
                indices = [
                    vertex_map[surface.model]["map"][vert] for vert in verts
                ]
                new_verts = [merged_vertices[i] for i in indices]
                new_tri = merged_model.mb.create_element(
                    types.MBTRI, new_verts
                )
                merged_model.mb.add_entities(new_surface.handle, [new_tri])
            surface_map[new_surface.id] = (surface.model, surface.id)
    return surface_map


def build_volume_map(all_models, merged_model):
    """Creates a new volume in the merged_model for each volume in the models
    to be merged. Creates a map from original model and volume id to the new
    volume id.

    Arguments:
        all_models (list of dagmc.DAGModel): List of models to be merged.
        merged_model (dagmc.DAGModel): Model in which models will be combined.

    Returns:
        volume_map (dict): {
            original model (dagmc.DAGMODEL):
                {
                    volume id in original model (int):
                        volume id in merged_model (int)
                }
            }

    """
    volume_map = {}
    for model in all_models:
        volume_map[model] = {}
        for volume in model.volumes:
            new_volume = dagmc.Volume.create(merged_model)
            volume_map[model][volume.id] = new_volume.id
    return volume_map


def apply_surface_sense(surface_map, volume_map, merged_model):
    """Builds volume surface relationship in merged_model using the surface and
    volume maps, along with the surface sense information in the original
    models.

    Arguments:
        surface_map (dict): {
                merged_model surface id (int):
                    (model containing original surface, original surface id)
            }
        volume_map (dict): {
            original model (dagmc.DAGMODEL):
                {
                    volume id in original model (int):
                        volume id in merged_model (int)
                }
            }
        merged_model (dagmc.DAGModel): Model in which models will be combined.
            Must have surface and volume information from build_surface_map()
            and build_volume_map() already.
    """

    for surface in merged_model.surfaces:
        original_model, original_id = surface_map[surface.id]
        surf_sens = []
        for vol in original_model.surfaces_by_id[original_id].surf_sense:
            if vol is None:
                surf_sens.append(vol)
            else:
                surf_sens.append(
                    merged_model.volumes_by_id[
                        volume_map[original_model][vol.id]
                    ]
                )
        surface.surf_sense = surf_sens


def apply_group_information(all_models, merged_model, volume_map):
    """Copy group information from models to be merged to the merged_model.

    Arguments:
        all_models (list of dagmc.DAGModel): List of models to be merged.
        merged_model (dagmc.DAGModel): Model in which models will be combined.
            Must have surface and volume information from build_surface_map()
            and build_volume_map() already.
        volume_map (dict): {
            original model (dagmc.DAGMODEL):
                {
                    volume id in original model (int):
                        volume id in merged_model (int)
                }
            }

    """
    for model in all_models:
        for volume in model.volumes:
            group = volume.groups[0]
            merged_volume = merged_model.volumes_by_id[
                volume_map[model][volume.id]
            ]
            new_group = dagmc.Group.create(merged_model, name=group.name)
            new_group.add_set(merged_volume)


def merge_dagmc_models(all_models):
    """merges a list of dagmc.DAGModels into a single instance. These models
    should not intersect each other.

    Arguments:
        all_models (list of dagmc.DAGModel): Models to be merged.

    Returns:
        merged_model (dagmc.DAGModel): Model containing the surfaces, volumes,
            and groups from the models to be merged.
    """
    mbc = core.Core()
    merged_model = dagmc.DAGModel(mbc)

    vertex_map, merged_vertices = build_vertex_map(all_models, merged_model)
    surface_map = build_surface_map(
        all_models, merged_model, vertex_map, merged_vertices
    )
    volume_map = build_volume_map(all_models, merged_model)
    apply_surface_sense(surface_map, volume_map, merged_model)
    apply_group_information(all_models, merged_model, volume_map)

    return merged_model


def parse_args():
    """Parser for running as a script"""
    parser = argparse.ArgumentParser(prog="combine_dagmc_models")
    parser.add_argument(
        "-f",
        "--files",
        nargs="+",
        help="Space separated list of dagmc models to merge",
        required=True,
    )
    return parser.parse_args()


def main():

    args = parse_args()
    all_models = [dagmc.DAGModel(file) for file in args.files]
    merged_model = merge_dagmc_models(all_models)
    merged_model.write_file("merged.h5m")


if __name__ == "__main__":
    main()
