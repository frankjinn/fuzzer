# Copyright 2024 Flavien Solt, ETH Zurich.
# Licensed under the General Public License, Version 3.0, see LICENSE for details.
# SPDX-License-Identifier: GPL-3.0-only

################
# Generate a complete de-saturated netlist
################

# @return a pair (netlist: dict, random_inputs: list)
def gen_random_backward_netlist_and_inputs(fuzzerstate, num_cells):
    all_cells = [] # The cells are listed backward
    all_netwires = []
    all_prod_requests_notfulfilled = []
    all_prod_requests_fulfilled = []

    raise NotImplementedError("Please implement the generation of backward netlists")
