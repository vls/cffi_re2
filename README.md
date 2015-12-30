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
pip install https://github.com/vls/cffi_re2
```
or from a local copy:
```bash
sudo python3 setup.py install
```

### Using cffi_re2

TODO