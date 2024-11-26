# Copyright 2024 Flavien Solt, ETH Zurich.
# Licensed under the General Public License, Version 3.0, see LICENSE for details.
# SPDX-License-Identifier: GPL-3.0-only

from pycellgenerator.allcells import get_output_port_size

def get_all_cell_out_sizes(netlist_dict: dict, present_cell_ids):
    total_size = 0
    for cell_id_to_probe in present_cell_ids:
        curr_cell_type = netlist_dict['cell_types'][cell_id_to_probe]
        curr_cell_dimension = netlist_dict['cell_dimensions'][cell_id_to_probe]
        # Find the name and width of the output ports
        # output_port_name = get_output_port_name(curr_cell_type)
        output_port_width = get_output_port_size(curr_cell_type, curr_cell_dimension)
        # Add a probe wire
        total_size += output_port_width
    return total_size

def get_all_cell_out_sizes_of_given_type(netlist_dict: dict, present_cell_ids, cell_type):
    total_size = 0
    for cell_id_to_probe in present_cell_ids:
        curr_cell_type = netlist_dict['cell_types'][cell_id_to_probe]
        if curr_cell_type != cell_type:
            continue
        curr_cell_dimension = netlist_dict['cell_dimensions'][cell_id_to_probe]
        # Find the name and width of the output ports
        # output_port_name = get_output_port_name(curr_cell_type)
        output_port_width = get_output_port_size(curr_cell_type, curr_cell_dimension)
        # Add a probe wire
        total_size += output_port_width
    return total_size

def get_all_cell_out_sizes_of_given_type_and_distance(netlist_dict: dict, present_cell_ids, cell_type, distance, all_cell_distances):
    total_size = 0
    for cell_id_to_probe in present_cell_ids:
        curr_cell_type = netlist_dict['cell_types'][cell_id_to_probe]
        if curr_cell_type != cell_type or all_cell_distances[cell_id_to_probe] != distance:
            continue
        curr_cell_dimension = netlist_dict['cell_dimensions'][cell_id_to_probe]
        # Find the name and width of the output ports
        # output_port_name = get_output_port_name(curr_cell_type)
        output_port_width = get_output_port_size(curr_cell_type, curr_cell_dimension)
        # Add a probe wire
        total_size += output_port_width
    return total_size
