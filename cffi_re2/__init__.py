#!/usr/bin/env python
#encoding=utf-8

__version__ = '0.1.4'

import cffi
import imp

import pkg_resources
import os
import re
import six

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
    typedef struct {
        bool hasMatch;
        int numGroups;
        char** groups;
    } REMatchResult;

    typedef struct {
        int numMatches;
        bool hasGroupMatches;
        char** matches;
        char*** groupMatches;
    } REMultiMatchResult;

    void FreeREMatchResult(REMatchResult mr);

    void* RE2_new(const char* pattern);
    REMatchResult FindSingleMatch(void* re_obj, const char* data, bool fullMatch);
    void RE2_delete(void* re_obj);
    void RE2_delete_string_ptr(void* ptr);
    void* RE2_GlobalReplace(void* re_obj, const char* str, const char* rewrite);
    const char* get_c_str(void* ptr_str);
    const char* get_error_msg(void* re_obj);
    bool ok(void* re_obj);
    ''')

    libre2 = ffi.dlopen(soname)

class MatchObject(object):
    def __init__(self, re, groups):
        self.re = re
        self._groups = groups
    def group(self, i):
        return self._groups[i]
    def groups(self):
        return self._groups
    def __str__(self):
        return "MatchObject(groups={0})".format(self._groups)

RE_COM = re.compile('\(\?\#.*?\)')  

class CRE2:
    def __init__(self, pattern, *args, **kwargs):
        pattern = CRE2.__convertToBinaryUTF8(pattern)
        self.pattern = pattern

        if 'compat_comment' in kwargs:
            pattern = RE_COM.sub('', pattern)

        self.re2_obj = ffi.gc(libre2.RE2_new(pattern), libre2.RE2_delete)
        flag = libre2.ok(self.re2_obj)
        if not flag:
            ret = libre2.get_error_msg(self.re2_obj)
            raise ValueError(ffi.string(ret))

        self.libre2 = libre2

    @staticmethod
    def __convertToBinaryUTF8(data):
        if isinstance(data, six.text_type):
            return data.encode("utf-8")
        return data

    def search(self, data):
        return self.__search(data, False)  # 0 => UNANCHORED

    def match(self, data):
        return self.__search(data, True)  # 0 => ANCHOR_BOTH

    def __search(self, data, fullMatch=False):
        """
        Search impl that can either be performed in full or partial match
        mode, depending on the anchor argument
        """
        # RE2 needs binary data, so we'll need to encode it
        data = CRE2.__convertToBinaryUTF8(data)

        if isinstance(data, six.text_type):
            data = data.encode("utf-8")

        matchobj = libre2.FindSingleMatch(self.re2_obj, data, fullMatch)
        if matchobj.hasMatch:
            # Capture groups
            groups = [ffi.string(matchobj.groups[i]).decode("utf-8")
                      for i in range(matchobj.numGroups)]
            ret = MatchObject(self, groups)
        else:
            ret = None
        # Cleanup C API objects
        libre2.FreeREMatchResult(matchobj)
        return ret

    def sub(self, repl, s, count=0):
        # Convert all strings to UTF8
        repl = CRE2.__convertToBinaryUTF8(repl)
        s = CRE2.__convertToBinaryUTF8(s)

        c_p_str = self.libre2.RE2_GlobalReplace(self.re2_obj, s, repl)

        py_string = ffi.string(self.libre2.get_c_str(c_p_str))
        # Cleanup C API objects
        self.libre2.RE2_delete_string_ptr(c_p_str)
        return py_string.decode("utf-8")

def compile(pattern, *args, **kwargs):
    return CRE2(pattern, *args, **kwargs)
