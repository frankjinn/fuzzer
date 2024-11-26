# Copyright 2024 Flavien Solt, ETH Zurich.
# Licensed under the General Public License, Version 3.0, see LICENSE for details.
# SPDX-License-Identifier: GPL-3.0-only

# This script helps to find out which cell outputs have a path to the output port at all.

import os
import numpy as np

from pycellgenerator.allcells import get_output_port_size

def get_cell_path_to_output_proportions(netlist_dict):
    cell_output_masks = [0 for _ in netlist_dict['cell_types']]

    # Compute the cell output widths 
    cell_output_widths = []
    for cell_id in range(len(netlist_dict['cell_types'])):
        curr_cell_type = netlist_dict['cell_types'][cell_id]
        curr_cell_dimension = netlist_dict['cell_dimensions'][cell_id]
        cell_output_widths.append(get_output_port_size(curr_cell_type, curr_cell_dimension))

    # For each cell output bit, we determine whether it has a path to the output port.
    # For that, we look at all connections, starting from the end of the design. We then backtrack to mark all relevant bits in the output masks

    all_connections = netlist_dict['connections']
    pool_to_explore_next = list(filter(lambda c: c[0] == -1 and c[1] == 'O', all_connections))
    visited_cells = {-1}

    while pool_to_explore_next:
        # Get the next connection to explore
        curr_connection = pool_to_explore_next.pop()
        curr_src_cell_id = curr_connection[3]
        curr_src_port_offset = curr_connection[5]
        curr_src_port_width = curr_connection[6]

        # If the source is the input port, then we are done
        if curr_src_cell_id == -1:
            continue

        cell_output_masks[curr_src_cell_id] |= ((1 << curr_src_port_width) - 1) << curr_src_port_offset

        # Find all connections that have the current destination cell as the source
        if curr_src_cell_id not in visited_cells:
            visited_cells.add(curr_src_cell_id)
            pool_to_explore_next += list(filter(lambda c: c[0] == curr_src_cell_id, all_connections))

    # Compute the proportion
    total_num_bits_with_path_to_output = sum(map(lambda m: bin(m).count('1'), cell_output_masks))
    total_num_bits = sum(cell_output_widths)
    proportion = total_num_bits_with_path_to_output / total_num_bits
    return proportion

def get_cell_path_to_output_proportions_filtered(fuzzerstate, netlist_dict):
    cell_output_masks = [0 for _ in netlist_dict['cell_types']]

    # Compute the cell output widths 
    cell_output_widths = []
    for cell_id in range(len(netlist_dict['cell_types'])):
        curr_cell_type = netlist_dict['cell_types'][cell_id]
        curr_cell_dimension = netlist_dict['cell_dimensions'][cell_id]
        cell_output_widths.append(get_output_port_size(curr_cell_type, curr_cell_dimension))

    # For each cell output bit, we determine whether it has a path to the output port.
    # For that, we look at all connections, starting from the end of the design. We then backtrack to mark all relevant bits in the output masks

    all_connections = netlist_dict['connections']
    pool_to_explore_next = list(filter(lambda c: c[0] == -1 and c[1] == 'O', all_connections))
    visited_cells = {-1}

    while pool_to_explore_next:
        # Get the next connection to explore
        curr_connection = pool_to_explore_next.pop()
        curr_src_cell_id = curr_connection[3]
        curr_src_port_offset = curr_connection[5]
        curr_src_port_width = curr_connection[6]

        # If the source is the input port, then we are done
        if curr_src_cell_id == -1:
            continue

        cell_output_masks[curr_src_cell_id] |= ((1 << curr_src_port_width) - 1) << curr_src_port_offset

        # Find all connections that have the current destination cell as the source
        if curr_src_cell_id not in visited_cells:
            visited_cells.add(curr_src_cell_id)
            pool_to_explore_next += list(filter(lambda c: c[0] == curr_src_cell_id, all_connections))

    # Filter out the cell outputs that have been optimized away
    with open(os.path.join(fuzzerstate.workdir, 'top.sv'), 'r') as f:
        yosys_output = f.read()

    cell_ids_to_remove = []
    for cell_id in range(len(netlist_dict['cell_types'])):
        if f"celloutsig_{cell_id}z;" not in yosys_output:
            cell_ids_to_remove.append(cell_id)
    cell_output_masks = np.delete(cell_output_masks, cell_ids_to_remove)
    cell_output_widths = np.delete(cell_output_widths, cell_ids_to_remove)

    # Compute the proportion
    total_num_bits_with_path_to_output = sum(map(lambda m: bin(m).count('1'), cell_output_masks))
    total_num_bits = sum(cell_output_widths)
    proportion = total_num_bits_with_path_to_output / total_num_bits
    return proportion


################
# Path per cell ID
################

def get_cell_path_to_output_proportions_per_cell_id(fuzzerstate, netlist_dict):
    cell_output_masks = [0 for _ in netlist_dict['cell_types']]

    # Compute the cell output widths 
    cell_output_widths = []
    for cell_id in range(len(netlist_dict['cell_types'])):
        curr_cell_type = netlist_dict['cell_types'][cell_id]
        curr_cell_dimension = netlist_dict['cell_dimensions'][cell_id]
        cell_output_widths.append(get_output_port_size(curr_cell_type, curr_cell_dimension))

    # For each cell output bit, we determine whether it has a path to the output port.
    # For that, we look at all connections, starting from the end of the design. We then backtrack to mark all relevant bits in the output masks

    all_connections = netlist_dict['connections']
    pool_to_explore_next = list(filter(lambda c: c[0] == -1 and c[1] == 'O', all_connections))
    visited_cells = {-1}

    while pool_to_explore_next:
        # Get the next connection to explore
        curr_connection = pool_to_explore_next.pop()
        curr_src_cell_id = curr_connection[3]
        curr_src_port_offset = curr_connection[5]
        curr_src_port_width = curr_connection[6]

        # If the source is the input port, then we are done
        if curr_src_cell_id == -1:
            continue

        cell_output_masks[curr_src_cell_id] |= ((1 << curr_src_port_width) - 1) << curr_src_port_offset

        # Find all connections that have the current destination cell as the source
        if curr_src_cell_id not in visited_cells:
            visited_cells.add(curr_src_cell_id)
            pool_to_explore_next += list(filter(lambda c: c[0] == curr_src_cell_id, all_connections))

    # Filter out the cell outputs that have been optimized away
    with open(os.path.join(fuzzerstate.workdir, 'top.sv'), 'r') as f:
        yosys_output = f.read()

    cell_ids_to_remove_by_opt = []
    for cell_id in range(len(netlist_dict['cell_types'])):
        if f"celloutsig_{cell_id}z;" not in yosys_output:
            cell_ids_to_remove_by_opt.append(cell_id)
    # Do not remove from the list.
    # cell_output_masks = np.delete(cell_output_masks, cell_ids_to_remove_by_opt)
    # cell_output_widths = np.delete(cell_output_widths, cell_ids_to_remove_by_opt)

    # Compute the proportion
    ret = list(map(lambda m: bin(m).count('1'), cell_output_masks))

    return ret, cell_ids_to_remove_by_opt
