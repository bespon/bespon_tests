# Language-agnostic tests for BespON


This is a language-agnostic test suite for
[BespON](https://bespon.github.io) encoders and decoders.  The current focus
is on decoders.


## Decoding tests

Decoding tests in `tests/decoding` may be run against the
[`bespon` package for Python](https://github.com/gpoore/bespon_py) using the
included script `test_bespon_py_decoding.py`.  Future implementations in
other languages may use this as a template for working with decoding tests.

Test files are themselves written in BespON.  The top level of each test file
is a dict.  Each key in this dict corresponds to a test name, and each value
to a test.  An example from `test_strings.bespon` is shown below.
```text
|=== test_keylike
status = valid
bespon = ['string', "'string'", '"string"', '`string`']
json = '"string"'
```
In this case, the test is called `test_keylike`.  The test data itself
is in the form of a dict.  Since `status` is `valid`, all of the data
string of BespON data, or a list of BespON data as in this case.  `json`
provides equivalent data in JSON form, to allow the loaded BespON data to
be validated.  If `json` is a string, as in this case, then all data provided
in `bespon` must provide the same result.  If `json` is a list instead, then
the data represented by each element in `json` must be identical to that
in the corresponding index in `bespon`.  Most tests only provide a single
`json` string for comparison, but this functionality is convenient for
testing things like numbers without greatly increasing the overall number of
tests.

Tests may have `status = invalid` instead.  In this case, `json` values are
omitted, and all data in `bespon` must fail to load.  Invalid data should be
designed to be invalid only in one respect, so that each `invalid` test
is only checking one failure mode.

Finally, tests may have `status = implementation`.  In this case, each string
of BespON data in `bespon` must either fail to load, or load with a
value that agrees with the corresponding element in `json`.  Typically,
`implementation` is reserved for use with things like integers, which may
have limited precision in some implementations (say, 32-bit) but unlimited
precision in other implementations (say, automatic promotion from 64-bit to
arbitrary precision).


### Types in JSON validation

JSON supports a more limited range of data types than BespON, particularly
for dict keys.  When types that are not directly supported by JSON are
required, type information is represented in JSON using a two-element list
of the form
```text
[":<type>", <data>]
```
`<data>` may be a literal dict or list.  Other types should be represented
as strings to which typing will be applied.

After the data in the `json` part of a test is loaded, it is searched
recursively for lists of this form, and they are replaced by applying typing
`<type>` to objects `<data>`.  Currently, the following types are provided
using this approach:

  * `:int64` – 64-bit integer
  * `:bigint` – arbitrary precision integer
  * `:int64:2` – 64-bit integer, represented in binary (base 2) form
  * `:int64:8` – 64-bit integer, represented in octal (base 8) form
  * `:int64:16` – 64-bit integer, represented in hex (base 16) form
  * `:float64` – IEEE 754 binary64, represented in decimal form
  * `:float64:16` – IEEE 754 binary64, represented in hex form
  * `:dict` – dict collection; used to convert a list of two-element lists
    into a dict, to create dicts with non-string keys (which are not
    supported by JSON)


## Encoding tests

Currently, encoding tests are limited to loading the valid decoding tests,
encoding them, and then decoding to make sure that the results match.
Additional, more targeted encoding tests may be added in the future.

This encoding check may be run against the
[`bespon` package for Python](https://github.com/gpoore/bespon_py) using the
included script `test_bespon_py_encoding_roundtrip.py`.


## License

All test data is licensed under the
[Creative Commons Attribution 4.0 International Public License](https://creativecommons.org/licenses/by/4.0/legalcode).

All test code is licensed under the
[BSD 3-Clause license](https://opensource.org/licenses/BSD-3-Clause).
