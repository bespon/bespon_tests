# -*- coding: utf-8 -*-
#
# Copyright (c) 2017, Geoffrey M. Poore
# All rights reserved.
#
# Licensed under the BSD 3-Clause License:
# http://opensource.org/licenses/BSD-3-Clause
#

'''
Load all BespON tests, re-encode all valid test data, and then decode it to
check encoding.
'''


# pylint: disable=C0301

import sys
import os
import argparse
import collections
import math
if sys.version_info.major == 2:
    from io import open
    str = unicode


parser = argparse.ArgumentParser()
parser.add_argument('--basic', default=False, action='store_true',
                    help='Only test encoding on basic test data')
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


def equivalent(a, b, circular_cache=None,
               type=type, dict=dict, list=list, float=float, complex=complex,
               len=len, all=all, id=id, zip=zip, isnan=math.isnan):
    '''
    Compare two objects for equivalence, taking into consideration the
    possibility of things like circular references and NaN that would make a
    simple `==` equality test fail.
    '''
    if circular_cache is None:
        circular_cache = set()
    if type(a) != type(b):
        return False
    if isinstance(a, dict) or isinstance(a, list):
        id_a = id(a)
        id_b = id(b)
        pair = (id_a, id_b)
        if pair in circular_cache:
            if len([x for x in circular_cache if x[0] == id_a or x[1] == id_b]) > 1:
                return False
            return True
        circular_cache.update((pair,))
        if len(a) != len(b):
            return False
        if isinstance(a, dict):
            if not all(k in b for k in a):
                return False
            return all(equivalent(a[k], b[k], circular_cache=circular_cache) for k in a)
        if isinstance(a, list):
            return all(equivalent(a_i, b_i, circular_cache=circular_cache) for a_i, b_i in zip(a, b))
        raise Exception
    if isinstance(a, float):
        return a == b or (isnan(a) and isnan(b))
    if isinstance(a, complex):
        return ((a.real == b.real) or (isnan(a.real) and isnan(b.real))) and ((a.imag == b.imag) or (isnan(a.imag) and isnan(b.imag)))
    return a == b


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
        data = bespon.load(f, custom_types=bespon.LoadType(name='parser', compatible_implicit_types=['str'], parser=lambda x: {'int': int, 'float': float, 'str': str}[x]))
    for test_key, test_val in data.items():
        if 'float_overflow_to_inf' in test_key or 'custom_parsers' in test_key:
            continue
        test_count += 1
        if isinstance(test_val['bespon'], str):
            raw_data = [test_val['bespon']]
        else:
            raw_data = test_val['bespon']
        options = test_val.get('options', {})
        subtest_count += len(raw_data)
        if test_val['status'] == 'valid':
            # All data must successfully load
            try:
                bespon_data = [bespon.loads(x, **options) for x in raw_data]
            except Exception as e:
                raise Exception('Invalid data (run decoding tests before trying encoding tests again):\n  {0}'.format(e))
            error = False
            for n, b in enumerate(bespon_data):
                try:
                    encoded = bespon.dumps(b, **options)
                except Exception as e:
                    print(b)
                    error = True
                    subtest_number = n + 1
                    break
                if not error:
                    try:
                        b_roundtripped = bespon.loads(encoded, **options)
                    except Exception as e:
                        error = True
                        subtest_number = n + 1
                        break
                if not error:
                    if not equivalent(b, b_roundtripped):
                        error = True
                        subtest_number = n + 1
                        break
            if error:
                failed_count += 1
                if len(bespon_data) == 1:
                    failed_tests[fname].append(test_key)
                else:
                    failed_tests[fname].append(test_key + ' (subtest {0})'.format(subtest_number))


print('Found {0} tests with {1} subtests in {2} files\n(skipping lossy tests involving float_overflow_to_inf and custom_parsers)'.format(test_count, subtest_count, file_count))
print('Passed:  {0}    Failed:  {1}'.format(test_count - failed_count, failed_count))
if failed_tests:
    for fname, messages in failed_tests.items():
        print('\nIn {0}:{1}'.format(fname, ''.join('\n* {0}'.format(m) for m in messages)))


if test_count == 0 or failed_tests:
    sys.exit(1)
