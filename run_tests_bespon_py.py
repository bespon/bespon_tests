# -*- coding: utf-8 -*-
#
# Copyright (c) 2017, Geoffrey M. Poore
# All rights reserved.
#
# Licensed under the BSD 3-Clause License:
# http://opensource.org/licenses/BSD-3-Clause
#

'''
Run all BespON tests using bespon package for Python.

Run with `--verbose` for more detailed output.  Run with `--bespon_py` to
specify a path to the bespon package.  This will test the code at the
specified location, rather than any version of the package that may be
installed.
'''


# pylint: disable=C0301

import sys
import os
import argparse
import collections
import json
import math
if sys.version_info.major == 2:
    from io import open
    str = unicode


parser = argparse.ArgumentParser()
parser.add_argument('--basic', default=False, action='store_true',
                    help='Only run basic tests (simple data of all types loads, but is not verified)')
parser.add_argument('--bespon_py', help='Use bespon package at specified path, rather than installed bespon package')
parser.add_argument('--verbose', default=False, action='store_true',
                    help='More detailed error messages')
args = parser.parse_args()

if os.path.isdir('bespon_tests'):
    test_dir = os.path.abspath(os.path.join('bespon_tests', 'tests'))
elif os.path.isdir('../bespon_tests') and os.path.isdir('tests'):
    test_dir = os.path.abspath('tests')
else:
    sys.exit('Could not find directory "tests"')


if args.bespon_py is None:
    import bespon
else:
    sys.path.insert(0, os.path.abspath(os.path.expanduser(os.path.expandvars(args.bespon_py))))
    import bespon


json_typelist_parsers = {':int': int,
                         ':bigint': int,
                         ':int:2': lambda x: int(x, 2),
                         ':int:8': lambda x: int(x, 8),
                         ':int:16': lambda x: int(x, 16),
                         ':float': float,
                         ':float:16': float.fromhex}


def find_json_untyped(obj, parent, index, unresolved):
    if isinstance(obj, dict):
        for k, v in obj:
            find_json_untyped(v, obj, k, unresolved)
    elif isinstance(obj, list):
        if obj and isinstance(obj[0], str) and obj[0][:1] == ':':
            if len(obj) > 2:
                raise TypeError
            unresolved.append((obj[0], obj[1], parent, index))
            find_json_untyped(obj[1], obj, 1, unresolved)
        else:
            for n, elem in enumerate(obj):
                find_json_untyped(elem, obj, n, unresolved)


def json_typelist_loads(s):
    json_data = json.loads(s)
    json_wrapped = [json_data]
    unresolved = []
    find_json_untyped(json_data, json_wrapped, 0, unresolved)
    if unresolved:
        for typename, obj, parent, index in reversed(unresolved):
            parent[index] = json_typelist_parsers[typename](obj)
    return json_wrapped[0]


test_fnames = (fname for fname in os.listdir(test_dir) if fname.startswith('test_') and fname.endswith('.bespon'))

file_count = 0
test_count = 0
subtest_count = 0
failed_tests = collections.defaultdict(list)
failed_count = 0

for fname in test_fnames:
    file_count += 1
    with open(os.path.join(test_dir, fname), encoding='utf8') as f:
        data = bespon.load(f)
    for test_key, test_val in data.items():
        test_count += 1
        if isinstance(test_val['bespon'], str):
            raw_data = [test_val['bespon']]
        else:
            raw_data = test_val['bespon']
        if test_val['status'] in 'valid':
            # All data must successfully load, and if there is json for
            # comparison, the two data sets must agree
            error = False
            try:
                bespon_data = [bespon.loads(x) for x in raw_data]
            except Exception as e:
                error = True
                failed_count += 1
                if args.verbose:
                    failed_tests[fname].append('{0}\n    {1}'.format(test_key, e))
                else:
                    failed_tests[fname].append(test_key)
            if not error and 'json' in test_val:
                if isinstance(test_val['json'], str):
                    json_data = [json_typelist_loads(test_val['json'])]*len(raw_data)
                else:
                    json_data = [json_typelist_loads(x) for x in test_val['json']]
                if not all(b == j or (isinstance(b, float) and math.isnan(b) and math.isnan(j)) for b, j in zip(bespon_data, json_data)):
                    failed_count += 1
                    failed_tests[fname].append(test_key)
        elif test_val['status'] == 'invalid':
            # All data must fail to load
            error_count = 0
            for x in raw_data:
                try:
                    bespon.loads(x)
                except Exception as e:
                    error_count += 1
            if error_count != len(raw_data):
                failed_count += 1
                failed_tests[fname].append(test_key)
        elif test_val['status'] == 'implementation':
            # Each piece of data must either fail to load, or must agree with
            # the corresponding json
            if isinstance(test_val['json'], str):
                json_data = [json_typelist_loads(test_val['json'])]*len(raw_data)
            else:
                json_data = [json_typelist_loads(x) for x in test_val['json']]
            for x, j in zip(raw_data, json_data):
                error = False
                try:
                    b = bespon.loads(x)
                except Exception as e:
                    error = True
                if not error and not (b == j or (isinstance(b, float) and math.isnan(b) and math.isnan(j))):
                    failed_count += 1
                    failed_tests[fname].append(test_key)
                    break
        else:
            raise ValueError


print('Found {0} tests in {1} files'.format(test_count, file_count))
print('Failed tests:  {0}'.format(failed_count))
if failed_tests:
    for fname, messages in failed_tests.items():
        print('\nIn {0}:\n* {1}'.format(fname, ''.join(messages)))


if test_count == 0 or failed_tests:
    sys.exit(1)
