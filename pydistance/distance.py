# Copyright 2024 Flavien Solt, ETH Zurich.
# Licensed under the General Public License, Version 3.0, see LICENSE for details.
# SPDX-License-Identifier: GPL-3.0-only

from tqdm import trange

# For each cell, we determine its distance from the input port.
# A distance of 0 means that the cell is directly connected to the input port.
# Assume that we know the distance of all previous cells.
def __get_cell_distance_from_input_port(cell_id, netlist_dict, distances_of_previous_cells):
    all_connections = netlist_dict['connections']

    # Filter all connections to only those that are connected to the cell
    connections_to_this_cell = list(filter(lambda c: c[0] == cell_id, all_connections))
    curr_distance = cell_id # This is the maximal possible distance
    for connection in connections_to_this_cell:
        src_cell_id = connection[3]
        assert src_cell_id < cell_id, "The source cell must have a lower ID than the destination cell"
        if src_cell_id == -1:
            # The source is the input port
            return 0
        else:
            curr_distance = min(curr_distance, distances_of_previous_cells[src_cell_id] + 1)

    return curr_distance

def get_cell_distances_from_input_port(netlist_dict):
    num_cells = len(netlist_dict['cell_types'])
    distances_of_previous_cells = [-1] * num_cells
    for cell_id in trange(num_cells):
        distances_of_previous_cells[cell_id] = __get_cell_distance_from_input_port(cell_id, netlist_dict, distances_of_previous_cells)
    return distances_of_previous_cells
