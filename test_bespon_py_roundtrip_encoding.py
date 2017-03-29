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
    sys.path.insert(0, os.path.abspath(os.path.expanduser(os.path.expandvars(args.bespon_py))))
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
        if test_val['status'] in 'valid':
            # All data must successfully load
            try:
                bespon_data = [bespon.loads(x) for x in raw_data]
            except Exception as e:
                raise Exception('Invalid data (run decoding tests before trying encoding tests again):\n  {0}'.format(e))
            error = False
            for b in bespon_data:
                try:
                    encoded = bespon.dumps(b)
                except Exception as e:
                    error = True
                    break
                if not error:
                    try:
                        bespon.loads(encoded)
                    except Exception as e:
                        error = True
                        break
            if error:
                failed_count += 1
                failed_tests[fname].append(test_key)


print('Found {0} tests with {1} subtests in {2} files'.format(test_count, subtest_count, file_count))
print('Passed:  {0}    Failed:  {1}'.format(test_count - failed_count, failed_count))
if failed_tests:
    for fname, messages in failed_tests.items():
        print('\nIn {0}:{1}'.format(fname, ''.join('\n* {0}'.format(m) for m in messages)))


if test_count == 0 or failed_tests:
    sys.exit(1)
