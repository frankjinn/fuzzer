# Copyright 2024 Flavien Solt, ETH Zurich.
# Licensed under the General Public License, Version 3.0, see LICENSE for details.
# SPDX-License-Identifier: GPL-3.0-only

# Return a list of 32-bit masks
def gen_useful_input_bits_mask_words(netlist_dict: dict):
    # Find the input ports in the connections list
    ret_masks = [0] * (netlist_dict['in_width'] // 32)
    for connection in netlist_dict['connections']:
        if connection[3] == -1 and connection[4] == 'I':
            # Input port
            # cell_id = connection[0]
            # port_name = connection[1]
            # port_offset = connection[2]
            input_port_offset = connection[5]
            port_width = connection[6]
            assert input_port_offset + port_width <= netlist_dict['in_width']
            min_bit_id = input_port_offset
            max_bit_id = input_port_offset + port_width - 1
            min_word_id = min_bit_id // 32
            max_word_id = max_bit_id // 32
            if min_word_id == max_word_id:
                ret_masks[min_word_id] |= (2 ** (max_bit_id % 32 + 1) - 1) - (2 ** (min_bit_id % 32) - 1)
            else:
                ret_masks[min_word_id] |= (0xFFFFFFFF << (min_bit_id % 32)) & 0xFFFFFFFF
                ret_masks[max_word_id] |= 0xFFFFFFFF >> (32 - max_bit_id % 32 - 1)
                for word_id in range(min_word_id + 1, max_word_id):
                    ret_masks[word_id] = 0xFFFFFFFF
    return ret_masks

# Little test
if __name__ == '__main':
    netlist_dict = {
        'in_width': 128,
        'connections': [
            (None, None, None, -1, 'I', 5, 64),
        ],
    }
    ret = gen_useful_input_bits_mask_words(netlist_dict)
    print('\n', map(hex, ret))
