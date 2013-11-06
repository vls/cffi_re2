#!/usr/bin/env python
#encoding=utf-8


import cffi
import imp

import pkg_resources
import os
dirname = pkg_resources.resource_filename('cffi_re2', '')
dirname = os.path.abspath(os.path.join(dirname, '..'))
import glob
search_string = os.path.join(dirname, '_cre2*.so')
flist = glob.glob(search_string)
assert flist
soname = flist[0]


ffi = cffi.FFI()

ffi.cdef('''
void* RE2_new(const char* pattern); 
bool PartialMatch(void* re_obj, const char* data);
void RE2_delete(void* re_obj);
void RE2_delete_string_ptr(void* ptr);
void* RE2_GlobalReplace(void* re_obj, const char* str, const char* rewrite);
const char* get_c_str(void* ptr_str);
''')

libre2 = ffi.dlopen(soname)


def force_str(s):
    if isinstance(s, unicode):
        return s.encode('utf-8')
    return str(s)

class CRE2:
    def __init__(self, pattern):
        pattern = force_str(pattern)
        self.re2_obj = libre2.RE2_new(pattern)
        self.libre2 = libre2

    def search(self, data):
        return not not libre2.PartialMatch(self.re2_obj, data)

    def sub(self, repl, str, count=0):
        c_p_str = self.libre2.RE2_GlobalReplace(self.re2_obj, str, repl)

        py_string = ffi.string(self.libre2.get_c_str(c_p_str))
        self.libre2.RE2_delete_string_ptr(c_p_str)
        return py_string

    def close(self):
        if self.re2_obj:
            libre2.RE2_delete(self.re2_obj)

    def __del__(self):
        self.close()

def compile(pattern):
    return CRE2(pattern)
