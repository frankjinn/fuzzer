# Copyright 2024 Flavien Solt, ETH Zurich.
# Licensed under the General Public License, Version 3.0, see LICENSE for details.
# SPDX-License-Identifier: GPL-3.0-only

import random

from pycellgenerator.allcells import get_output_port_name, get_output_port_size

################
# Spray probes
################

def insert_spray_toggle_probes(netlist_dict: dict, proportion_cell_outputs_to_probe: float):
    num_cells = len(netlist_dict['cell_types'])
    num_cells_to_probe = round(num_cells * proportion_cell_outputs_to_probe)

    cell_ids_to_probe = random.sample(range(num_cells), num_cells_to_probe)

    # For each cell, find the output port and insert a probe
    curr_bit_in_probes = 0
    new_connections = []

    for cell_id_to_probe in cell_ids_to_probe:
        curr_cell_type = netlist_dict['cell_types'][cell_id_to_probe]
        curr_cell_dimension = netlist_dict['cell_dimensions'][cell_id_to_probe]
        # Find the name and width of the output ports
        output_port_name = get_output_port_name(curr_cell_type)
        output_port_width = get_output_port_size(curr_cell_type, curr_cell_dimension)
        # Add a probe wire
        new_connections.append((-1, 'P', curr_bit_in_probes, cell_id_to_probe, output_port_name, 0, output_port_width))
        curr_bit_in_probes += output_port_width

    netlist_dict['connections'] += new_connections
    return netlist_dict, curr_bit_in_probes
