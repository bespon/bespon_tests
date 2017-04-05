# -*- coding: utf-8 -*-
#
# Copyright (c) 2017, Geoffrey M. Poore
# All rights reserved.
#
# Licensed under the BSD 3-Clause License:
# http://opensource.org/licenses/BSD-3-Clause
#

'''
Run all BespON decoding tests using bespon package for Python.

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
    test_dir = os.path.abspath(os.path.join('bespon_tests', 'tests', 'decoding'))
elif os.path.isdir('../bespon_tests') and os.path.isdir('tests'):
    test_dir = os.path.abspath(os.path.join('tests', 'decoding'))
else:
    sys.exit('Could not find directory "tests"')


if args.bespon_py is None:
    import bespon
else:
    sys.path.insert(1, os.path.abspath(os.path.expanduser(os.path.expandvars(args.bespon_py))))
    import bespon


def _int64(s, base=10):
    n = int(s, base)
    if not -9223372036854775808 <= n <= 9223372036854775807:
        raise ValueError
    return n

JSON_TYPELIST_PARSERS = {':int64': _int64,
                         ':bigint': int,
                         ':int64:2': lambda x: _int64(x, 2),
                         ':int64:8': lambda x: _int64(x, 8),
                         ':int64:16': lambda x: _int64(x, 16),
                         ':float64': float,
                         ':float64:16': float.fromhex,
                         # Dict is needed to provide mappings with non-string
                         # keys (none, bool, int)
                         ':dict': dict}


def find_json_untyped(obj, parent, index, unresolved):
    '''
    Within loaded data, recursively find all lists of the form
        [":<type>", <data>]
    and add information about them to a list `unresolved`.  This list will
    then be used to replace all such lists, starting at the deepest nesting
    level and working out, with the result of applying `<type>` to `<data>`.
    This provides a way to convert data loaded in JSON format into data
    structures that JSON itself does not support.
    '''
    if isinstance(obj, dict):
        for k, v in obj.items():
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
    '''
    Load a string as JSON data, and process all lists of the form
        [":<type>", <data>]
    by applying `<type>` to `<data>`.  This provides a way to convert data
    loaded in JSON format into data structures that JSON itself does not
    support.
    '''
    raw_json_data = json.loads(s)
    # In case top level isn't a list or dict, provide a wrapper
    json_wrapped = [raw_json_data]
    unresolved = []
    find_json_untyped(raw_json_data, json_wrapped, 0, unresolved)
    if unresolved:
        # Work from deepest nesting level outward; hence `reversed()`
        for typename, obj, parent, index in reversed(unresolved):
            parent[index] = JSON_TYPELIST_PARSERS[typename](obj)
    return json_wrapped[0]


test_fnames = (fname for fname in os.listdir(test_dir) if fname.startswith('test_') and fname.endswith('.bespon'))

file_count = 0
test_count = 0
subtest_count = 0
failed_tests = collections.defaultdict(list)
failed_count = 0

for fname in test_fnames:
    if args.basic and fname != 'test_basic.bespon':
        continue
    file_count += 1
    with open(os.path.join(test_dir, fname), encoding='utf8') as f:
        data = bespon.load(f)
    for test_key, test_val in data.items():
        test_count += 1
        if isinstance(test_val['bespon'], str):
            raw_data = [test_val['bespon']]
        else:
            raw_data = test_val['bespon']
        subtest_count += len(raw_data)
        if test_val['status'] == 'valid':
            # All data must successfully load
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
            if not error:
                if isinstance(test_val['json'], str):
                    json_data = [json_typelist_loads(test_val['json'])]*len(raw_data)
                else:
                    json_data = [json_typelist_loads(x) for x in test_val['json']]
                    if len(json_data) != len(raw_data):
                        raise ValueError('Missing json values in test "{0}" in "{1}"'.format(test_key, fname))
                if not all(b == j or (isinstance(b, float) and math.isnan(b) and math.isnan(j)) for b, j in zip(bespon_data, json_data)):
                    failed_count += 1
                    if len(bespon_data) == 1:
                        failed_tests[fname].append(test_key)
                    else:
                        failed_subtest_numbers = []
                        for n, (b, j) in enumerate(zip(bespon_data, json_data)):
                            if b != j and not (isinstance(b, float) and math.isnan(b) and math.isnan(j)):
                                failed_subtest_numbers.append(n+1)
                        if len(failed_subtest_numbers) == 1:
                            failed_tests[fname].append(test_key + ' (subtest {0})'.format(', '.join(str(x) for x in failed_subtest_numbers)))
                        else:
                            failed_tests[fname].append(test_key + ' (subtests {0})'.format(', '.join(str(x) for x in failed_subtest_numbers)))
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
            # Each individual set of data must either fail to load, or must
            # agree with the corresponding json
            if isinstance(test_val['json'], str):
                json_data = [json_typelist_loads(test_val['json'])]*len(raw_data)
            else:
                json_data = [json_typelist_loads(x) for x in test_val['json']]
                if len(json_data) != len(raw_data):
                    raise ValueError('Missing json values in test "{0}" in "{1}"'.format(test_key, fname))
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


print('Found {0} tests with {1} subtests in {2} files'.format(test_count, subtest_count, file_count))
print('Passed:  {0}    Failed:  {1}'.format(test_count - failed_count, failed_count))
if failed_tests:
    for fname, messages in failed_tests.items():
        print('\nIn {0}:{1}'.format(fname, ''.join('\n* {0}'.format(m) for m in messages)))


if test_count == 0 or failed_tests:
    sys.exit(1)
