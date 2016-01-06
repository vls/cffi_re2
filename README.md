# cffi_re2
[![Build Status](https://travis-ci.org/vls/cffi_re2.png)](https://travis-ci.org/vls/cffi_re2)

cffi_re2 is a cffi-based high-level Python binding for Google's [re2](https://github.com/google/re2) library.

### Installation

Before installing cffi_re2, you will need to install re2. On Ubuntu/Debian you can do that using

```bash
sudo apt-get install libre2-dev
```

Else, you can simply install the current version from the git repository:

```bash
git clone https://github.com/google/re2.git
make
make test
sudo make install
```

See the [re2 repository](https://github.com/google/re2) for further information.

After installing re2, you can install cffi_re2:

```bash
pip install cffi_re2
```
or from a local copy:
```bash
sudo python setup.py install
```

*cffi_re2* is fully compatbile with both *Python3.x* as well as [*PyPy*](pypy.org) (including *PyPy3*). 

You can run the unit tests using:
```bash
sudo python setup.py test
```

### Using cffi_re2

*cffi_re2* is mostly compatible to the *re* module from the Python standard library and exposes the same interface. In almost all cases you can use the same source code for both libraries. The flags in `cffi_re2` are exactly the same as those in `re`, so you can e.g. use `re.IGNORECASE` in `cffi_re2.compile` and vice versa.

One way to use *cffi_re2* is:

```python
import cffi_re2 as re
```

Note however, that, due to the design of the [*RE2*](https://github.com/google/re2) library, some syntax elements like zero-width lookaheads or lookbehinds are [not supported](https://github.com/google/re2/wiki/Syntax).

When using those syntax elements, the backend reports a syntax error when calling `cffi_re2.compile`, for example:

```
ValueError: invalid perl operator: (?<
```

One workaround is to convert your regex into a group-capturing form and select the appropriate group later. For larger sets of complex regular expressions, this is often not feasible, however.

In this case, it is recommended to use a hybrid approach, i.e. falling back to *re* if *cffi_re2* fails to compile an expression.

```python
import re
import cffi_re2

def compileRegex(rgx, flags=0):
    try:
        return cffi_re2.compile(rgx, flags)
    except ValueError:
        return re.compile(rgx, flags)
``` 

Note that in the current implementation there are still several known and unknown incompatibilities between *cffi_re2* and *re*. If you encounter issues, please report them as a bug.

### Benchmarks

### About

*cffi_re2* was originally developed by [Liang Zhaohao](https://github.com/vls). Many new features and improvements were contributed by [Uli Köhler](https://github.com/ulikoehler).

The library is licensed under the MIT license (see LICENSE file).
