# Copyright 2024 Flavien Solt, ETH Zurich.
# Licensed under the General Public License, Version 3.0, see LICENSE for details.
# SPDX-License-Identifier: GPL-3.0-only

import json
import os
import subprocess
import random
import concurrent.futures

from pybackend.backend import build_executable_worker, run_executable_worker
from pybackend.cleanupnetlist import cleanup_netlist
from pycommon.fuzzparams import FuzzerParams, FuzzerState
from pycommon.runparams import SimulatorType
from pynetgenerator.genonebyone import gen_random_onebyone_netlist, gen_total_num_cells, gen_netlist_from_cells_and_netwires, find_requesters_per_clkin_type
from pynetgenerator.splitsubnetids import split_subnet_ids, ClkInType
from pycellgenerator.allcells import get_output_port_size, randomize_authorized_combinational_cell_types, randomize_authorized_stateful_cell_types, ALL_CELL_PORTS_STATEFUL

from copy import deepcopy

PATH_TO_WORKDIR_ROOT = '/scratch/simufuzz-workdir'

PRIORITIZE_UNUSED = True
DO_TRACE = False

def add_random_wordflip_to_netlist(workload_debug: int, netlist_dict):
    flip_netlist_dict = deepcopy(netlist_dict)

    subnet_id = 0
    # Select random cell
    selected_cell_id = random.randrange(len(flip_netlist_dict['cell_types'][subnet_id]))
    selected_cell_type = flip_netlist_dict['cell_types'][subnet_id][selected_cell_id]
    selected_cell_dimension = flip_netlist_dict['cell_dimensions'][subnet_id][selected_cell_id]
    selected_cell_outwidth = get_output_port_size(selected_cell_type, selected_cell_dimension)
    is_selected_cell_stateful = selected_cell_type in ALL_CELL_PORTS_STATEFUL

    # Find all connections that originate from the selected cell
    all_connections = flip_netlist_dict['connections']
    all_relevant_connection_ids = []
    all_relevant_connections = []
    for connection_id, connection in enumerate(all_connections):
        connection_origin_cell_id = connection[5]
        connection_origin_port_name = connection[6]
        connection_origin_port_offset = connection[7]
        connection_origin_port_width = connection[8]
        if connection_origin_cell_id == selected_cell_id:
            assert connection_origin_port_name in ("Y", "Q")
            all_relevant_connection_ids.append(connection_id)
            all_relevant_connections.append(connection)

    # Add the not cell
    flip_netlist_dict['cell_types'][subnet_id].append('not')
    flip_netlist_dict['cell_dimensions'][subnet_id].append([selected_cell_outwidth, selected_cell_outwidth])
    flip_netlist_dict['cell_params'][subnet_id].append([])
    not_connection_id = len(flip_netlist_dict['cell_types'][subnet_id]) - 1

    # Add connection to the not cell
    flip_netlist_dict['connections'].append([subnet_id, len(flip_netlist_dict['cell_types'][subnet_id]) - 1, "A", 0, subnet_id, selected_cell_id, "Q" if is_selected_cell_stateful else "Y", 0, selected_cell_outwidth])

    # # Add all the connections to the not cell
    # for connection in all_relevant_connections:
    #     subnet_id = 0
    #     connection_origin_cell_id = connection[5]
    #     connection_origin_port_name = connection[6]
    #     connection_origin_port_offset = connection[7]
    #     connection_destination_cell_id = len(flip_netlist_dict['cell_types'][subnet_id]) - 1
    #     is_orig_cell_stateful = flip_netlist_dict['cell_types'][subnet_id][connection_origin_cell_id] in ALL_CELL_PORTS_STATEFUL
    #     flip_netlist_dict['connections'].append([subnet_id, connection_destination_cell_id, "A", 0, subnet_id, connection_origin_cell_id, "Q" if is_orig_cell_stateful else "Y", 0, selected_cell_outwidth])

    #     # Do only a single connection
    #     break
    # else:
    #     print(f"Warning: No connection exists for the flipped bit")


    for connection in all_relevant_connections:
        connection_destination_subnet_id = connection[0]
        connection_destination_cell_id = connection[1]
        connection_destination_port_name = connection[2]
        connection_destination_port_offset = connection[3]
        connection_origin_subnet_id = connection[4]
        connection_origin_cell_id = connection[5]
        connection_origin_port_name = connection[6]
        connection_origin_port_offset = connection[7]
        connection_origin_port_width = connection[8]

        new_connection = [connection_destination_subnet_id, connection_destination_cell_id, connection_destination_port_name, connection_destination_port_offset, connection_origin_subnet_id, not_connection_id, "Y", connection_origin_port_offset, connection_origin_port_width]
        flip_netlist_dict['connections'].append(new_connection)

    for connection_id in reversed(all_relevant_connection_ids):
        del flip_netlist_dict['connections'][connection_id]

    return flip_netlist_dict



def testpropagflipword_wrapper(workload, min_num_cells, max_num_cells, simlen: int):
    timeout = 202
    while True:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Submit the function to the executor
            future = executor.submit(__testpropagflipword, workload, min_num_cells, max_num_cells, simlen)

            # Wait for the function to complete or timeout
            try:
                ret = future.result(timeout=timeout)
                if ret is not None:
                    return ret
                else:
                    workload += 1000000
            except concurrent.futures.TimeoutError:
                workload += 1000000

# For a single workload, flip a single bit and see whether the output has changed
def __testpropagflipword(workload, min_num_cells, max_num_cells, simlen: int):
    try:
        random.seed(workload)
        workdir = os.path.join(PATH_TO_WORKDIR_ROOT, f"tmp/obj_dir_example_testpropagflip_{workload}")

        num_cells = gen_total_num_cells(min_num_cells, max_num_cells)
        authorized_combinational_cell_types = randomize_authorized_combinational_cell_types([])
        authorized_stateful_cell_types      = randomize_authorized_stateful_cell_types(True, [])
        proportion_final_cells_connected_to_output = random.uniform(FuzzerParams.ProportionFinalCellsConnectedToOutputMin, FuzzerParams.ProportionFinalCellsConnectedToOutputMax)
        fuzzerstate = FuzzerState(workdir, FuzzerParams.CellMinDimension, FuzzerParams.CellMaxDimension, True, min_num_cells, max_num_cells, FuzzerParams.MinInputWidthWords, max(FuzzerParams.MinOutputWidthWords, proportion_final_cells_connected_to_output), simlen, DO_TRACE, authorized_combinational_cell_types, authorized_stateful_cell_types)

        BASE_SUBNET_ID = 0 # Be careful if you modify this because stuff does not get mixed up in netlist.json (which cells belong to which subnet)
        all_cells_base, all_netwires_base = gen_random_onebyone_netlist(fuzzerstate, BASE_SUBNET_ID, num_cells)

        # Create the subnets
        all_requesters_per_clkin_type = find_requesters_per_clkin_type([all_cells_base], [BASE_SUBNET_ID])

        # Split the clocks
        splitted_requesters_per_clkin_type = split_subnet_ids(all_requesters_per_clkin_type)
        del all_requesters_per_clkin_type

        all_cells_list = [all_cells_base]
        all_netwires_list = [all_netwires_base]
        netlist_dict = gen_netlist_from_cells_and_netwires(fuzzerstate, all_cells_list, all_netwires_list, splitted_requesters_per_clkin_type)
        num_subnets = len(netlist_dict['cell_types'])
        num_subnets_or_clkins = num_subnets + len(netlist_dict['clkin_ports_names'])


        # all_cells_first, all_netwires_first = gen_random_onebyone_netlist(fuzzerstate, num_cells_clockdrivers, None)
        # all_cells_list, all_netwires_list = [all_cells_first, all_cells_base], [all_netwires_first, all_netwires_base]

        # Generate the random inputs. This is a list of pairs (subnet_or_clkin_id, input id)
        random_inputs_list = []
        # Actually, we start by setting all the clocks to 0 so all the posedge events are understood equally by all simulators.
        curr_clkin_id = num_subnets
        for clkin_type in splitted_requesters_per_clkin_type:
            for clkin_subnet_id, clkin_subnet in enumerate(splitted_requesters_per_clkin_type[clkin_type]):
                random_inputs_list.append((curr_clkin_id, 0))
                curr_clkin_id += 1

        for _ in range(fuzzerstate.simlen):
            curr_rand = random.random()
            curr_is_subnet = num_subnets_or_clkins == num_subnets or curr_rand < FuzzerParams.ProbaToggleSubnet
            if curr_is_subnet:
                curr_subnet_or_clkin_id = random.randint(0, num_subnets - 1)
            else:
                curr_subnet_or_clkin_id = random.randint(num_subnets, num_subnets_or_clkins - 1)

            curr_is_subnet = curr_subnet_or_clkin_id < num_subnets
            if curr_is_subnet and fuzzerstate.is_input_full_random:
                new_line = tuple([curr_subnet_or_clkin_id] + [random.randint(0, 2 ** 32 - 1) for _ in range(fuzzerstate.num_input_words)])
                random_inputs_list.append(new_line)
            else:
                random_inputs_list.append((curr_subnet_or_clkin_id, random.randint(0, 2 ** 32 - 1)))
        inputs_str_lines = [str(len(random_inputs_list))]
        for curr_tuple in random_inputs_list:
            inputs_str_lines.append(' '.join(map(lambda val: hex(val)[2:], curr_tuple)))

        os.makedirs(workdir, exist_ok=True)
        # Write netlist
        netlist_dict = cleanup_netlist(netlist_dict)

        # Generate the tuples for the clkin-type inputs
        template_input_port_tuples = []
        for clkin_type in splitted_requesters_per_clkin_type:
            for clkin_subnet_id, clkin_subnet in enumerate(splitted_requesters_per_clkin_type[clkin_type]):
                template_input_port_tuples.append((f"{ClkInType.to_char(clkin_type)}{clkin_subnet_id}", max(map(lambda c: c[3], clkin_subnet))))

        with open(os.path.join(workdir, 'netlist.json'), 'w') as f:
            json.dump(netlist_dict, f)
        with open(os.path.join(workdir, 'netlist_noflip.json'), 'w') as f:
            json.dump(netlist_dict, f)

        # Write random inputs
        with open(os.path.join(workdir, 'inputs.txt'), 'w') as f:
            f.write('\n'.join(inputs_str_lines))

        # The first simulator
        build_executable_worker(fuzzerstate, netlist_dict, SimulatorType.SIM_ICARUS, False, True, template_input_port_tuples)
        elapsed_time_noflip, output_signature_noflip, _, stderr_noflip = run_executable_worker(fuzzerstate, SimulatorType.SIM_ICARUS)

        netlist_dict_flip = add_random_wordflip_to_netlist(workload, netlist_dict)
        netlist_dict_flip = cleanup_netlist(netlist_dict_flip)
        with open(os.path.join(workdir, 'netlist.json'), 'w') as f:
            json.dump(netlist_dict_flip, f)
        with open(os.path.join(workdir, 'netlist_flip.json'), 'w') as f:
            json.dump(netlist_dict_flip, f)
        # Write random inputs
        with open(os.path.join(workdir, 'inputs.txt'), 'w') as f:
            f.write('\n'.join(inputs_str_lines))

        # The simulator with flip
        build_executable_worker(fuzzerstate, netlist_dict_flip, SimulatorType.SIM_ICARUS, False, True, template_input_port_tuples)
        elapsed_time_flip, output_signature_flip, _, stderr_flip = run_executable_worker(fuzzerstate, SimulatorType.SIM_ICARUS)

        # Now, flip a bit and see whether the output has changed
        print(f"Outputs identical: {output_signature_noflip == output_signature_flip} ({hex(int(output_signature_noflip))} vs {hex(int(output_signature_flip))})")

        return output_signature_noflip == output_signature_flip
    except subprocess.TimeoutExpired:
        print(f"Timeout exception in workload {workload}")
        return None
