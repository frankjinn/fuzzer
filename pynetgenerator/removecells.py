# Copyright 2024 Flavien Solt, ETH Zurich.
# Licensed under the General Public License, Version 3.0, see LICENSE for details.
# SPDX-License-Identifier: GPL-3.0-only

from pycellgenerator.allcells import ALL_CELL_PORTS_STATEFUL

################
# Stateful cells
################

def remove_stateful_cells(netlist_dict: dict) -> dict:
    stateful_cell_ids = []
    for subnet_id, subnet in enumerate(netlist_dict['cell_types']):
        for cell_id, cell_type_str in enumerate(netlist_dict['cell_types'][subnet_id]):
            if cell_type_str in ALL_CELL_PORTS_STATEFUL:
                print(f"Removing stateful cell {subnet_id}-{cell_id} of type {cell_type_str}")
                stateful_cell_ids.append((subnet_id, cell_id))
            else:
                print(f"NOT Removing stateful cell {subnet_id}-{cell_id} of type {cell_type_str}")

    # Remove the cell types
    for (subnet_id, cell_id) in reversed(stateful_cell_ids): # stateful cells are already sorted by construction
        del netlist_dict['cell_types'][subnet_id][cell_id]
        del netlist_dict['cell_params'][subnet_id][cell_id]
        del netlist_dict['cell_dimensions'][subnet_id][cell_id]

    netlist_dict['clkin_ports_names'] = []
    netlist_dict['clkin_ports_widths'] = []

    # Remove the cell connections to the stateful cells and relocate down the other ones
    for (subnet_id, cell_id) in reversed(stateful_cell_ids):
        new_connection_netlist = []
        print(f"Subnet {subnet_id} Cell {cell_id}")
        for connection_id, connection in enumerate(netlist_dict['connections']):
            do_insert = True
            if connection[0] == subnet_id:
                if connection[1] == cell_id:
                    do_insert = False # Remove the connection
                elif connection[1] > cell_id:
                    connection[1] -= 1
            if connection[4] == subnet_id:
                if connection[5] == cell_id:
                    do_insert = False # Remove the connection
                elif connection[5] > cell_id:
                    connection[5] -= 1
            if do_insert:
                new_connection_netlist.append(connection)
        netlist_dict['connections'] = new_connection_netlist

    return netlist_dict

################
# Clkins
################

def remove_clkin_inputs(actorid_val_pairs: list, num_subnets: int) -> list:
    ret_pairs = []
    for actorid, val in actorid_val_pairs:
        if actorid < num_subnets:
            ret_pairs.append((actorid, val))
    return ret_pairs

################
# Single cell
################

def remove_single_cell(subnet_id: int, cell_id: int, netlist_dict: dict) -> dict:
    # Remove the cell types
    del netlist_dict['cell_types'][subnet_id][cell_id]
    del netlist_dict['cell_params'][subnet_id][cell_id]
    del netlist_dict['cell_dimensions'][subnet_id][cell_id]

    # Remove the cell connections to the stateful cells and relocate down the other ones
    new_connection_netlist = []
    for connection_id, connection in enumerate(netlist_dict['connections']):
        do_insert = True
        if connection[0] == subnet_id:
            if connection[1] == cell_id:
                do_insert = False # Remove the connection
            elif connection[1] > cell_id:
                connection[1] -= 1
        if connection[4] == subnet_id:
            if connection[5] == cell_id:
                do_insert = False # Remove the connection
            elif connection[5] > cell_id:
                connection[5] -= 1
        if do_insert:
            new_connection_netlist.append(connection)
    netlist_dict['connections'] = new_connection_netlist

    return netlist_dict
