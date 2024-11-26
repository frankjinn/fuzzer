# Copyright 2024 Flavien Solt, ETH Zurich.
# Licensed under the General Public License, Version 3.0, see LICENSE for details.
# SPDX-License-Identifier: GPL-3.0-only

from vcdvcd import VCDVCD

def analyze_vcd_for_toggle_results(fuzzerstate, path_to_vcd):
    vcd = VCDVCD(path_to_vcd)

    cumulated_toggles_per_cell_id = {}
    largest_time = 0

    for signal_name in vcd.signals:
        if 'celloutsig_' in signal_name:
            cell_id = int(signal_name.split('[')[0].split('celloutsig_')[-1])
            init_val = int(vcd[signal_name].tv[0][1].replace('z', '0'), 2)

            prev_timeval = 0
            prev_val = init_val

            for timeval, valstr in vcd[signal_name].tv[1:]:
                val = int(valstr.replace('z', '0'), 2)
                # Also populate the previous time values
                if timeval - prev_timeval > 1:
                    if cell_id in cumulated_toggles_per_cell_id and len(cumulated_toggles_per_cell_id[cell_id]):
                        cumulated_toggles_per_cell_id[cell_id].extend([cumulated_toggles_per_cell_id[cell_id][-1] for i in range(prev_timeval + 1, timeval)])
                    else:
                        cumulated_toggles_per_cell_id[cell_id] = [init_val for i in range(prev_timeval + 1, timeval)]
                prev_timeval = timeval

                if cell_id in cumulated_toggles_per_cell_id and len(cumulated_toggles_per_cell_id[cell_id]):
                    cumulated_toggles_per_cell_id[cell_id].append(cumulated_toggles_per_cell_id[cell_id][-1] | (init_val ^ val))
                else:
                    cumulated_toggles_per_cell_id[cell_id] = [init_val ^ val]
            largest_time = max(largest_time, vcd[signal_name].tv[-1][0])

    # Extend all traces to the largest time
    for cell_id in cumulated_toggles_per_cell_id:
        cumulated_toggles_per_cell_id[cell_id].extend([cumulated_toggles_per_cell_id[cell_id][-1] for i in range(len(cumulated_toggles_per_cell_id[cell_id]), largest_time + 1)])

    # for cell_id in cumulated_toggles_per_cell_id:
    #     print(f"Length of cell {cell_id}: {len(cumulated_toggles_per_cell_id[cell_id])}")

    return cumulated_toggles_per_cell_id
