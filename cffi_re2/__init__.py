#!/usr/bin/env python
#encoding=utf-8

__version__ = '0.1.4'


import cffi
import imp

import pkg_resources
import os
import re
dirname = pkg_resources.resource_filename('cffi_re2', '')
dirname = os.path.abspath(os.path.join(dirname, '..'))
import glob
search_string = os.path.join(dirname, '_cre2*.so')
flist = glob.glob(search_string)

libre2 = None
if flist:
    soname = flist[0]


    ffi = cffi.FFI()

    ffi.cdef('''
    void* RE2_new(const char* pattern); 
    bool PartialMatch(void* re_obj, const char* data);
    void RE2_delete(void* re_obj);
    void RE2_delete_string_ptr(void* ptr);
    void* RE2_GlobalReplace(void* re_obj, const char* str, const char* rewrite);
    const char* get_c_str(void* ptr_str);
    const char* get_error_msg(void* re_obj);
    bool ok(void* re_obj);
    ''')

    libre2 = ffi.dlopen(soname)


def force_str(s):
    if isinstance(s, unicode):
        return s.encode('utf-8')
    return str(s)

class MatchObject(object):
    pass

RE_COM = re.compile('\(\?\#.*?\)')  

class CRE2:
    def __init__(self, pattern, *args, **kwargs):
        self.pattern = pattern = force_str(pattern)

        if 'compat_comment' in kwargs:
            pattern = RE_COM.sub('', pattern)

        self.re2_obj = ffi.gc(libre2.RE2_new(pattern), libre2.RE2_delete)
        flag = libre2.ok(self.re2_obj)
        if not flag:
            ret = libre2.get_error_msg(self.re2_obj)
            raise ValueError(ffi.string(ret))

        self.libre2 = libre2

    def search(self, data):
        flag_match = not not libre2.PartialMatch(self.re2_obj, data)
        if flag_match:
            m = MatchObject()
            m.re = self
            return m
        

    def sub(self, repl, str, count=0):
        c_p_str = self.libre2.RE2_GlobalReplace(self.re2_obj, str, repl)

        py_string = ffi.string(self.libre2.get_c_str(c_p_str))
        self.libre2.RE2_delete_string_ptr(c_p_str)
        return py_string


def compile(pattern, *args, **kwargs):
    return CRE2(pattern, *args, **kwargs)
