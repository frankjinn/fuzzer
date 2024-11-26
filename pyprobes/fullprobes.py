# Copyright 2024 Flavien Solt, ETH Zurich.
# Licensed under the General Public License, Version 3.0, see LICENSE for details.
# SPDX-License-Identifier: GPL-3.0-only

from pycellgenerator.allcells import get_output_port_name, get_output_port_size

################
# Spray probes
################

def get_full_probe_width(netlist_dict: dict):
    num_cells = len(netlist_dict['cell_types'])
    num_cells_to_probe = num_cells

    # For each cell, find the output port and insert a probe
    curr_bit_in_probes = 0

    for cell_id_to_probe in range(num_cells_to_probe):
        curr_cell_type = netlist_dict['cell_types'][cell_id_to_probe]
        curr_cell_dimension = netlist_dict['cell_dimensions'][cell_id_to_probe]
        # Find the name and width of the output ports
        output_port_name = get_output_port_name(curr_cell_type)
        output_port_width = get_output_port_size(curr_cell_type, curr_cell_dimension)
        # Add a probe wire
        curr_bit_in_probes += output_port_width

    curr_bit_in_probes = max(curr_bit_in_probes, 32)

    return curr_bit_in_probes

# @return a pair (probe_connections, probe_connection_start_per_cell)
def gen_all_probe_connections(netlist_dict):
    # For each cell, find the output port and insert a probe
    curr_bit_in_probes = 0
    probe_connections = []

    probe_connection_start_per_cell = [-1] * len(netlist_dict['cell_types'])

    for cell_id_to_probe in range(len(netlist_dict['cell_types'])):
        curr_cell_type = netlist_dict['cell_types'][cell_id_to_probe]
        curr_cell_dimension = netlist_dict['cell_dimensions'][cell_id_to_probe]
        # Find the name and width of the output ports
        output_port_name = get_output_port_name(curr_cell_type)
        output_port_width = get_output_port_size(curr_cell_type, curr_cell_dimension)
        # Add a probe wire
        probe_connections.append((-1, 'P', curr_bit_in_probes, cell_id_to_probe, output_port_name, 0, output_port_width))
        probe_connection_start_per_cell[cell_id_to_probe] = curr_bit_in_probes
        curr_bit_in_probes += output_port_width

    return probe_connections
