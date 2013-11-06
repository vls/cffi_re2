#!/usr/bin/env python
#encoding=utf-8


import cffi
import imp
_f, soname, _ = imp.find_module('_cre2')
_f.close()

f = cffi.FFI()

f.cdef('''
void* RE2_new(const char* pattern); 
bool PartialMatch(void* re_obj, const char* data);
void RE2_delete(void* re_obj);
''')

libre2 = f.dlopen(soname)


def force_str(s):
    if isinstance(s, unicode):
        return s.encode('utf-8')
    return str(s)

class CRE2:
    def __init__(self, pattern):
        pattern = force_str(pattern)
        self.re2_obj = libre2.RE2_new(pattern)

    def search(self, data):
        return not not libre2.PartialMatch(self.re2_obj, data)

    def close(self):
        if self.re2_obj:
            libre2.RE2_delete(self.re2_obj)

    def __del__(self):
        self.close()

def compile(pattern):
    return CRE2(pattern)
