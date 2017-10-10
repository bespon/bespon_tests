# -*- coding: utf-8 -*-
#
# Copyright (c) 2017, Geoffrey M. Poore
# All rights reserved.
#
# Licensed under the BSD 3-Clause License:
# http://opensource.org/licenses/BSD-3-Clause
#

'''
Run all BespON encoding tests using bespon package for Python.

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
import fractions
if sys.version_info.major == 2:
    from io import open
    str = unicode


parser = argparse.ArgumentParser()
parser.add_argument('--basic', default=False, action='store_true', help='Only run basic tests')
parser.add_argument('--bespon_py', help='Use bespon package at specified path, rather than installed bespon package')
parser.add_argument('--verbose', default=False, action='store_true', help='More detailed error messages')
args = parser.parse_args()

if os.path.isdir('bespon_tests'):
    test_dir = os.path.abspath(os.path.join('bespon_tests', 'tests', 'encoding'))
elif os.path.isdir('../bespon_tests') and os.path.isdir('tests'):
    test_dir = os.path.abspath(os.path.join('tests', 'encoding'))
else:
    sys.exit('Could not find directory "tests"')


if args.bespon_py is None:
    import bespon
else:
    sys.path.insert(1, os.path.abspath(os.path.expanduser(os.path.expandvars(args.bespon_py))))
    import bespon


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
        decoder_kwargs = test_val.get('options', {})
        if test_val['status'] == 'valid':
            # All data must successfully load
            error = False
            try:
                bespon_data = [bespon.loads(x, **decoder_kwargs) for x in raw_data]
            except Exception as e:
                error = True
                failed_count += 1
                failed_subtest_numbers = []
                for n, x in enumerate(raw_data):
                    try:
                        bespon.loads(x, **decoder_kwargs)
                    except Exception as e:
                        failed_subtest_numbers.append(n+1)
                if args.verbose:
                    failed_tests[fname].append('{0} (subtest {1})\n    {2}'.format(test_key, failed_subtest_numbers[0], e))
                else:
                    if len(failed_subtest_numbers) == 1:
                        failed_tests[fname].append(test_key + ' (subtest {0})'.format(', '.join(str(x) for x in failed_subtest_numbers)))
                    else:
                        failed_tests[fname].append(test_key + ' (subtests {0})'.format(', '.join(str(x) for x in failed_subtest_numbers)))
            if not error:
                encoder_kwargs = test_val.get('encoder_options', {})
                bespon_encoded = [bespon.dumps(x, **encoder_kwargs) for x in bespon_data]
                raw_encoded = test_val.get('encoded_bespon', raw_data)
                if isinstance(raw_encoded, str):
                    raw_encoded = [raw_encoded]
                if len(bespon_encoded) != len(raw_encoded):
                    raise ValueError('Missing encoded values in test "{0}" in "{1}"'.format(test_key, fname))
                equivalence_tests = [b == r for b, r in zip(bespon_encoded, raw_encoded)]
                if not all(equivalence_tests):
                    failed_count += 1
                    if len(bespon_encoded) == 1:
                        failed_tests[fname].append(test_key)
                    else:
                        failed_subtest_numbers = []
                        for n, t in enumerate(equivalence_tests):
                            if not t:
                                failed_subtest_numbers.append(n+1)
                        if len(failed_subtest_numbers) == 1:
                            failed_tests[fname].append(test_key + ' (subtest {0})'.format(', '.join(str(x) for x in failed_subtest_numbers)))
                        else:
                            failed_tests[fname].append(test_key + ' (subtests {0})'.format(', '.join(str(x) for x in failed_subtest_numbers)))
        elif test_val['status'] == 'invalid':
            bespon_data = [bespon.loads(x, **decoder_kwargs) for x in raw_data]
            encoder_kwargs = test_val.get('encoder_options', {})
            # All data must fail to save
            error_count = 0
            for x in bespon_data:
                try:
                    bespon.dumps(x, **encoder_kwargs)
                except Exception as e:
                    error_count += 1
            if error_count != len(raw_data):
                failed_count += 1
                failed_tests[fname].append(test_key)
        else:
            raise ValueError


print('Found {0} tests with {1} subtests in {2} files'.format(test_count, subtest_count, file_count))
print('Passed:  {0}    Failed:  {1}'.format(test_count - failed_count, failed_count))
if failed_tests:
    for fname, messages in failed_tests.items():
        print('\nIn {0}:{1}'.format(fname, ''.join('\n* {0}'.format(m) for m in messages)))


if test_count == 0 or failed_tests:
    sys.exit(1)
