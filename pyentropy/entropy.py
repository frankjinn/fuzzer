# Copyright 2024 Flavien Solt, ETH Zurich.
# Licensed under the General Public License, Version 3.0, see LICENSE for details.
# SPDX-License-Identifier: GPL-3.0-only

from collections import defaultdict
import json
import os
import numpy as np
import multiprocessing as mp
from pycellgenerator.allcells import get_all_cell_types
from pybackend.backend import build_executable_worker, run_executable_worker
from pyentropy.vcdanalysis import analyze_vcd_for_toggle_results
from pyentropy.celloutsizes import get_all_cell_out_sizes, get_all_cell_out_sizes_of_given_type, get_all_cell_out_sizes_of_given_type_and_distance
from pycommon.runparams import SimulatorType
from pydistance.distance import get_cell_distances_from_input_port

DISCRIMINATE_DISTANCE = False
DISTANCES_TO_PLOT = [0, 1, 2, 3, 4]

def do_plot_toggle_rate_over_time(netlist_dict_arr, cumulated_toggles_per_cell_id_arr):
    assert len(netlist_dict_arr) == len(cumulated_toggles_per_cell_id_arr), f"len(netlist_dict_arr)={len(netlist_dict_arr)}, len(cumulated_toggles_per_cell_id_arr)={len(cumulated_toggles_per_cell_id_arr)}"
    assert len(netlist_dict_arr) > 0, f"len(netlist_dict_arr)={len(netlist_dict_arr)}"

    TIME_UPPER_BOUND = 50
    curr_time_upper_bound = TIME_UPPER_BOUND
    X_toggle_over_time = list(range(curr_time_upper_bound))
    Y_toggle_over_time_arr = []
    for experiment_id in range(len(netlist_dict_arr)):
        cumulated_toggles_per_cell_id = cumulated_toggles_per_cell_id_arr[experiment_id]
        first_cell_id = min(cumulated_toggles_per_cell_id.keys())
        assert len(cumulated_toggles_per_cell_id[first_cell_id]) >= curr_time_upper_bound, f"len(cumulated_toggles_per_cell_id[first_cell_id])={len(cumulated_toggles_per_cell_id[first_cell_id])}, CURR_TIME_UPPER_BOUND={curr_time_upper_bound}"

        Y_toggle_over_time = []
        for time_step_id in range(curr_time_upper_bound):
            Y_toggle_over_time.append(0)
            for cell_id in cumulated_toggles_per_cell_id.keys():
                Y_toggle_over_time[-1] += bin(cumulated_toggles_per_cell_id[cell_id][time_step_id]).count('1')

        Y_toggle_over_time_arr.append(Y_toggle_over_time)

        # Normalize relatively to the total number of output bits
        present_cell_ids = list(cumulated_toggles_per_cell_id.keys())
        num_outbits = get_all_cell_out_sizes(netlist_dict_arr[experiment_id], present_cell_ids)
        Y_toggle_over_time_arr[-1] = [(y_toggle / num_outbits if num_outbits else 0) for y_toggle in Y_toggle_over_time_arr[-1]]

        print(f"Y_toggle_over_time_arr[{experiment_id}]: {Y_toggle_over_time_arr[-1]}")

    import matplotlib.pyplot as plt

    Y_toggle_over_time_avg = np.mean(Y_toggle_over_time_arr, axis=0)
    Y_toggle_over_time_min = np.min(Y_toggle_over_time_arr, axis=0)
    Y_toggle_over_time_max = np.max(Y_toggle_over_time_arr, axis=0)

    print(f"Y_toggle_over_time_avg: {Y_toggle_over_time_avg}")
    print(f"Y_toggle_over_time_min: {Y_toggle_over_time_min}")
    print(f"Y_toggle_over_time_max: {Y_toggle_over_time_max}")

    plt.plot(X_toggle_over_time, Y_toggle_over_time_avg, label='Average')
    plt.plot(X_toggle_over_time, Y_toggle_over_time_min, label='Min')
    plt.plot(X_toggle_over_time, Y_toggle_over_time_max, label='Max')
    plt.xlabel('Input')
    plt.ylabel('Toggle rate')
    plt.title('Toggle rate over time')
    plt.legend()
    plt.savefig('toggle_rate_over_time.png')


def do_plot_toggle_rate_over_time_per_distance(netlist_dict_arr, cumulated_toggles_per_cell_id_arr):
    assert len(netlist_dict_arr) == len(cumulated_toggles_per_cell_id_arr), f"len(netlist_dict_arr)={len(netlist_dict_arr)}, len(cumulated_toggles_per_cell_id_arr)={len(cumulated_toggles_per_cell_id_arr)}"
    assert len(netlist_dict_arr) > 0, f"len(netlist_dict_arr)={len(netlist_dict_arr)}"

    print('Getting distances')
    with mp.Pool(min(mp.cpu_count(), len(netlist_dict_arr))) as pool:
        all_distances_in_experiments = pool.map(get_cell_distances_from_input_port, netlist_dict_arr)

    DISTANCES_TO_PLOT = [0, 1, 2, 3, 4, 5]
    TIME_UPPER_BOUND = 50
    curr_time_upper_bound = TIME_UPPER_BOUND
    Y_toggle_over_time_arr = []
    for experiment_id in range(len(netlist_dict_arr)):
        cumulated_toggles_per_cell_id = cumulated_toggles_per_cell_id_arr[experiment_id]
        first_cell_id = min(cumulated_toggles_per_cell_id.keys())
        assert len(cumulated_toggles_per_cell_id[first_cell_id]) >= curr_time_upper_bound, f"len(cumulated_toggles_per_cell_id[first_cell_id])={len(cumulated_toggles_per_cell_id[first_cell_id])}, CURR_TIME_UPPER_BOUND={curr_time_upper_bound}"

        Y_toggle_over_time = {distance: [] for distance in DISTANCES_TO_PLOT}
        cell_ids_with_distance = dict()
        for time_step_id in range(curr_time_upper_bound):
            for considered_distance in DISTANCES_TO_PLOT:
                Y_toggle_over_time[considered_distance].append(0)

            for cell_id in cumulated_toggles_per_cell_id.keys():
                curr_distance = all_distances_in_experiments[experiment_id][cell_id]
                if curr_distance not in cell_ids_with_distance:
                    cell_ids_with_distance[curr_distance] = set()
                if curr_distance not in DISTANCES_TO_PLOT:
                    continue
                cell_ids_with_distance[curr_distance].add(cell_id)
                Y_toggle_over_time[curr_distance][-1] += bin(cumulated_toggles_per_cell_id[cell_id][time_step_id]).count('1')

        Y_toggle_over_time_arr.append(Y_toggle_over_time)

        # Normalize relatively to the total number of output bits
        for distance in DISTANCES_TO_PLOT:
            if distance not in cell_ids_with_distance:
                Y_toggle_over_time_arr[-1][distance] = [0 for _ in range(curr_time_upper_bound)]
                continue
            present_cell_ids = list(cell_ids_with_distance[distance])
            num_outbits = get_all_cell_out_sizes(netlist_dict_arr[experiment_id], present_cell_ids)
            Y_toggle_over_time_arr[-1][distance] = [(y_toggle / num_outbits if num_outbits else 0) for y_toggle in Y_toggle_over_time_arr[-1][distance]]

        print(f"Y_toggle_over_time_arr[{experiment_id}]: {Y_toggle_over_time_arr}")

    import matplotlib.pyplot as plt

    # Compute the average over all experiments
    X_toggle_over_time = list(range(curr_time_upper_bound))
    Y_toggle_over_time_avg = dict()
    for distance in DISTANCES_TO_PLOT:
        if distance not in cell_ids_with_distance:
            continue
        Y_toggle_over_time_avg[distance] = np.mean([Y_toggle_over_time[distance] for Y_toggle_over_time in Y_toggle_over_time_arr], axis=0)
        plt.plot(X_toggle_over_time, Y_toggle_over_time_avg[distance], label=f'Distance {distance}')

    plt.xlabel('Input')
    plt.ylabel('Toggle rate')
    plt.title('Toggle rate over time')
    plt.legend()
    plt.savefig('toggle_rate_over_time.png')


def do_plot_toggle_rate_over_time_per_cell_type(netlist_dict_arr, cumulated_toggles_per_cell_id_arr):
    assert len(netlist_dict_arr) == len(cumulated_toggles_per_cell_id_arr), f"len(netlist_dict_arr)={len(netlist_dict_arr)}, len(cumulated_toggles_per_cell_id_arr)={len(cumulated_toggles_per_cell_id_arr)}"
    assert len(netlist_dict_arr) > 0, f"len(netlist_dict_arr)={len(netlist_dict_arr)}"

    TIME_UPPER_BOUND = 50

    Y_toggle_over_time_arr = []

    if DISCRIMINATE_DISTANCE:
        print('Getting distances')
        with mp.Pool(min(mp.cpu_count(), len(netlist_dict_arr))) as pool:
            all_distances_in_experiments = pool.map(get_cell_distances_from_input_port, netlist_dict_arr)

    for experiment_id in range(len(netlist_dict_arr)):
        cumulated_toggles_per_cell_id = cumulated_toggles_per_cell_id_arr[experiment_id]

        if not len(cumulated_toggles_per_cell_id.keys()):
            print(f"Warning: no cells found with toggles")
            continue
        first_cell_id = min(cumulated_toggles_per_cell_id.keys())

        curr_time_upper_bound = min(len(cumulated_toggles_per_cell_id[first_cell_id]), TIME_UPPER_BOUND)

        if len(cumulated_toggles_per_cell_id[first_cell_id]) < curr_time_upper_bound:
            print(f"Warning: len(cumulated_toggles_per_cell_id[first_cell_id])={len(cumulated_toggles_per_cell_id[first_cell_id])}, CURR_TIME_UPPER_BOUND={curr_time_upper_bound}")
        assert len(cumulated_toggles_per_cell_id[first_cell_id]) >= curr_time_upper_bound, f"len(cumulated_toggles_per_cell_id[first_cell_id])={len(cumulated_toggles_per_cell_id[first_cell_id])}, CURR_TIME_UPPER_BOUND={curr_time_upper_bound}"

        if not DISCRIMINATE_DISTANCE:
            Y_toggle_over_time = []
            for time_step_id in range(curr_time_upper_bound):
                Y_toggle_over_time.append(defaultdict(int))
                for cell_id in cumulated_toggles_per_cell_id.keys():
                    Y_toggle_over_time[-1][netlist_dict_arr[experiment_id]['cell_types'][cell_id]] += bin(cumulated_toggles_per_cell_id[cell_id][time_step_id]).count('1')
            Y_toggle_over_time_arr.append(Y_toggle_over_time)
        else:
            Y_toggle_over_time_per_distance = []
            for time_step_id in range(curr_time_upper_bound):
                Y_toggle_over_time_per_distance.append(defaultdict(lambda: defaultdict(int)))
                for cell_id in cumulated_toggles_per_cell_id.keys():
                    curr_distance = all_distances_in_experiments[experiment_id][cell_id]
                    Y_toggle_over_time_per_distance[-1][curr_distance][netlist_dict_arr[experiment_id]['cell_types'][cell_id]] += bin(cumulated_toggles_per_cell_id[cell_id][time_step_id]).count('1')
            Y_toggle_over_time_arr.append(Y_toggle_over_time_per_distance)

        present_cell_ids = list(cumulated_toggles_per_cell_id.keys())
        # Normalize relatively to the total number of output bits
        if not DISCRIMINATE_DISTANCE:
            for cell_type in get_all_cell_types():
                num_outbits = get_all_cell_out_sizes_of_given_type(netlist_dict_arr[experiment_id], present_cell_ids, cell_type)
                if num_outbits:
                    Y_toggle_over_time_arr[-1][-1][cell_type] /= num_outbits
                else:
                    assert Y_toggle_over_time_arr[-1][-1][cell_type] == 0, f"Y_toggle_over_time_arr[-1][-1][cell_type]={Y_toggle_over_time_arr[-1][-1][cell_type]}"
        else:
            for distance in range(len(Y_toggle_over_time_arr[-1])):
                for cell_type in get_all_cell_types():
                    num_outbits = get_all_cell_out_sizes_of_given_type_and_distance(netlist_dict_arr[experiment_id], present_cell_ids, cell_type, distance, all_distances_in_experiments[experiment_id])
                    if num_outbits:
                        Y_toggle_over_time_arr[-1][distance][-1][cell_type] /= num_outbits
                    else:
                        assert Y_toggle_over_time_arr[-1][distance][-1][cell_type] == 0, f"Y_toggle_over_time_arr[-1][distance][-1][cell_type]={Y_toggle_over_time_arr[-1][distance][-1][cell_type]}"

        # Y_toggle_over_time_arr[-1] = [y_toggle / num_outbits for y_toggle in Y_toggle_over_time_arr[-1]]

    # Average over all experiments
    if not DISCRIMINATE_DISTANCE:
        Y_toggle_over_time_avg = dict()
        for cell_type in get_all_cell_types():
            Y_toggle_over_time_avg[cell_type] = np.mean([Y_toggle_over_time[-1][cell_type] for Y_toggle_over_time in Y_toggle_over_time_arr], axis=0)
        print(f"End results: {Y_toggle_over_time_avg}")
    else:
        Y_toggle_over_time_avg = dict()
        for distance in DISTANCES_TO_PLOT:
            Y_toggle_over_time_avg[distance] = dict()
            for cell_type in get_all_cell_types():
                Y_toggle_over_time_avg[distance][cell_type] = np.mean([Y_toggle_over_time_per_distance[-1][distance][cell_type] for Y_toggle_over_time_per_distance in Y_toggle_over_time_arr], axis=0)
        print(f"End results: {Y_toggle_over_time_avg}")

    import matplotlib.pyplot as plt

    # Make a bar plot, where each bar is for a cell type

    tick_names = list(Y_toggle_over_time_avg.keys())
    Ys = [Y_toggle_over_time_avg[cell_type] for cell_type in tick_names]

    # Sort tick_names and Ys by Ys
    tick_names, Ys = zip(*sorted(zip(tick_names, Ys), key=lambda pair: pair[1]))

    plt.xticks(rotation=90)  # Rotate X labels by 90 degrees

    plt.bar(tick_names, Ys)
    plt.xlabel('Cell type')
    plt.ylabel('Toggle rate')
    plt.title('Toggle rate over time')
    plt.tight_layout()
    plt.savefig('toggle_rate_over_time_per_cell_type.png')


# This function will run a simulation and return the entropy in function of the cell grouping
# @param cell_group_identifiers: a list of integers, where each integer represents a group.
def do_single_entropy_measurement(fuzzerstate, netlist_dict, random_inputs_list, cell_group_identifiers, simulator_type: SimulatorType):
    assert len(cell_group_identifiers) == len(netlist_dict['cell_types'])

    # Get the probe width
    with open(os.path.join(fuzzerstate.workdir, 'netlist.json'), 'w') as f:
        json.dump(netlist_dict, f)
    # Write random inputs
    with open(os.path.join(fuzzerstate.workdir, 'inputs.txt'), 'w') as f:
        f.write(' '.join(map(str, random_inputs_list)))

    # First, simply run the simulation with probes and get the output probe results
    build_executable_worker(fuzzerstate, netlist_dict, simulator_type, False, True)
    elapsed_time, output_signature, probe_tuples, stderr = run_executable_worker(fuzzerstate, simulator_type)

    vcdpath = os.path.join(fuzzerstate.workdir, 'trace.vcd') if simulator_type == SimulatorType.SIM_VERILATOR else os.path.join(fuzzerstate.workdir, 'icarus_dump.vcd')

    # Analyze the VCD for the toggle results
    cumulated_toggles_per_cell_id = analyze_vcd_for_toggle_results(fuzzerstate, vcdpath)
    return cumulated_toggles_per_cell_id

