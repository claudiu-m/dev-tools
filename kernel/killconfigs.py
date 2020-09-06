# SPDX-License-Identifier:  GPL-2.0-or-later
# Copyright 2020 claudiu-m <claudiu.manoil@gmail.com>

# run with Pyhton 3

import sys
import re
from collections import deque, namedtuple

# Given a (Linux kernel) "config" name (i.e. any C preprocessor macro name used to
# conditionally include a block of code a compile time) the script excludes or
# includes (depending on choice) that block of code by clearing all the C preprocessor
# conditional blocks and directives for the given config name from the given C source
# file, preserving the compilability of the source file.
# This is required to be able to manage source files that abuse conditional configuration
# options. Though excessive usage of conditional compilation options is considerred bad
# practice, I had to debug production code littered with tens of such compile time config
# options, many nested, and many of them disbled, thus hindering redability. Hence this script.
#
# The script removes simple #ifdef ... #end (aka "type 1 start") and #ifndef ... #end
# (aka "type 2 start") blocks, as well as #ifdef ... #else ... #end (aka "type 2 ending")
# blocks, so any combination of type 1 and type 2 start and ending blocks, and it can do
# that recursively for nested configs as well.  If presented with an 'Y' before the config
# name it will include the guarded code block and remove the #else blocks.
#
# TODO: #elif case

Blocks = namedtuple('Blocks', ['if_block', 'notif_block', 'ifelse_block', 'notifelse_block'])
# block type helpers
def get_outer_block_start(l, config):
        r = re.match("\s*#if[n]?def\s+%s" % config, l)
        return r

def is_block_start_1(l):
        r = re.match("\s*#ifdef", l)
        return r != None

def is_block_start_2(l):
        r = re.match("\s*#ifndef", l)
        return r != None

def is_block_end_1(l):
        r = re.match("\s*#endif", l)
        return r != None

def is_block_end_2(l):
        r = re.match("\s*#else", l) #TODO: or #elif?
        return r != None

def find_config_iter(d, config):
    for i, l in enumerate(d):
        r = get_outer_block_start(l, config)
        if r != None:
            yield i #DEBUG: , r.string

# find block end depending on type, recursively for nested blocks
def find_block_end(b, extended=False):
    q = deque()
    for i, l in enumerate(b):
        if is_block_start_1(l) or is_block_start_2(l):
            q.append(i)
            continue
        if len(q) > 0 and is_block_end_1(l):
            q.pop()
            continue
        if len(q) == 0:
            if is_block_end_1(l):
                return {'end_type': 1, 'off': i}
            if extended and is_block_end_2(l):
                return {'end_type': 2, 'off': i}

def find_outer_block_end(b):
    e = find_block_end(b[1:], extended=True)

    if e['end_type'] == 1:
        med = -1
        end = e['off'] + 1
    elif e['end_type'] == 2:
        med = e['off'] + 1
        #print("med: %s" % b[med])
        e1 = find_block_end(b[med+1:])
        end = med + e1['off'] + 1
    else:
        raise OuterBlock_end_type_err

    return {'med': med, 'end': end}

# identify block type and return block coordinates based on type
def process_block(b, start, reverse=False):
    if is_block_start_1(b[0]):
        start_type = 1
    elif is_block_start_2(b[0]):
        start_type = 2
    else:
        raise OuterBlock_start_type_err

    e = find_outer_block_end(b)
    if e['med'] == -1:
        end_type = 1
    else:
        end_type = 2

    med = start + e['med']
    end = start + e['end']

    case = Blocks(  if_block = (start_type == 1 and end_type == 1), \
                    notif_block = (start_type == 2 and end_type == 1), \
                    ifelse_block = (start_type == 1 and end_type == 2), \
                    notifelse_block = (start_type == 2 and end_type == 2))
    ret = list()
    if (not reverse and case.if_block) or (reverse and case.notif_block):
        ret = [(start, end)]
    elif (not reverse and case.notif_block) or (reverse and case.if_block):
        ret = [(start, start), (end, end)]
    elif (not reverse and case.ifelse_block) or (reverse and case.notifelse_block):
        ret = [(start, med), (end, end)]
    elif (not reverse and case.notifelse_block) or (reverse and case.ifelse_block):
        ret = [(start, start), (med, end)]

    return ret

# "process" blocks: return coordinates and metadata for all occurences of this block
def extract_block_pos(d, config, reverse=False):
    block_pos = list()
    cfgs = find_config_iter(d, config)
    try:
        start = next(cfgs)
    except StopIteration:
        print("config option not found")
        return None

    for next_start in cfgs:
        #print(start)
        b = d[start:next_start]
        block_pos.extend(process_block(b, start, reverse))
        # iteration end
        start = next_start
    # final block
    b = d[start:]
    block_pos.extend(process_block(b, start, reverse))

    return block_pos

# main
# TODO: [optional] getops() script params (Unix style)
def main():
    FILE_IN = sys.argv[1]
    CONFIG = sys.argv[2]
    FILE_OUT = FILE_IN + "_out"

    # file in:
    f = open(FILE_IN, "r")
    d = f.readlines()
    f.close()

    # go
    reverse = False
    ## handle CONFIG=y case, ie YCONFIG
    if CONFIG[0] == 'Y':
        reverse = True
        CONFIG = CONFIG[1:]

    print("CONFIG is: %s" % CONFIG)
    if reverse:
        print("reversed mode")

    block_pos = extract_block_pos(d, CONFIG, reverse)
    if block_pos is None:
        exit(0)
    #print(block_pos)

    d_out = list()
    s = 0
    for b in block_pos:
        #print(b)
        e = b[0]
        d_out.extend(d[s:e])
        s = b[1] + 1
    d_out.extend(d[s:])

    # file out:
    f = open(FILE_OUT, "w")
    f.writelines(d_out)
    f.close()

if __name__ == "__main__":
    main()
