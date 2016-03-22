#!/usr/bin/env python
# -*- coding: utf-8 -*-
import imp
from cffi import FFI
import os
import re
import sys
import six
import sre_compile

# Flags, copied from re.py
I = IGNORECASE = sre_compile.SRE_FLAG_IGNORECASE # ignore case
L = LOCALE = sre_compile.SRE_FLAG_LOCALE # assume current 8-bit locale
U = UNICODE = sre_compile.SRE_FLAG_UNICODE # assume unicode locale
M = MULTILINE = sre_compile.SRE_FLAG_MULTILINE # make anchors look for newline
S = DOTALL = sre_compile.SRE_FLAG_DOTALL # make dot match newline
X = VERBOSE = sre_compile.SRE_FLAG_VERBOSE # ignore whitespace and comments


ffi = FFI()
libre2 = None
ffi.cdef('''
typedef struct {
    int start;
    int end;
} Range;

typedef struct {
    bool hasMatch;
    int numGroups;
    Range* ranges;
} REMatchResult;

typedef struct {
    int numMatches;
    int numGroups;
    Range** ranges;
} REMultiMatchResult;

void FreeREMatchResult(REMatchResult mr);
void FreeREMultiMatchResult(REMultiMatchResult mr);

void* RE2_new(const char* pattern, bool caseInsensitive);
REMatchResult FindSingleMatch(void* re_obj, const char* data, bool fullMatch, int startpos);
REMultiMatchResult FindAllMatches(void* re_obj, const char* data, int anchorArg, int startpos);
void RE2_delete(void* re_obj);
void RE2_delete_string_ptr(void* ptr);
void* RE2_GlobalReplace(void* re_obj, const char* str, const char* rewrite);
const char* get_c_str(void* ptr_str);
const char* get_error_msg(void* re_obj);
bool ok(void* re_obj);
void RE2_SetMaxMemory(int maxmem);
''')

# Open native library
if sys.version_info >= (3, 4):
    import importlib
    soname = importlib.util.find_spec("cffi_re2._cre2").origin
else:
    curmodpath = sys.modules[__name__].__path__
    soname = imp.find_module('_cre2', curmodpath)[1]

libre2 = ffi.dlopen(soname)

class MatchObject(object):
    def __init__(self, re, string, ranges):
        """
        Initialize a MatchObject from ranges (a list of (start, end) tuples, one for every group).
        """
        self.re = re
        self.string = string
        self.ranges = ranges
        self.numGroups = len(ranges)

    def group(self, i):
        start, end = self.ranges[i]
        if start == -1 or end == -1:
            return None
        return self.string[start:end]

    def groups(self):
        return tuple(self.group(i) for i in range(1, self.numGroups))

    def start(self, group):
        return self.ranges[group][0]

    def end(self, group):
        return self.ranges[group][1]

    def span(self, group):
        return self.ranges[group]

    def __str__(self):
        return "MatchObject(groups={0})".format(self.groups())

RE_COM = re.compile('\(\?\#.*?\)')


class CRE2:
    def __init__(self, pattern, flags=0, *args, **kwargs):
        pattern = CRE2.__convertToBinaryUTF8(pattern)
        self.pattern = pattern

        if 'compat_comment' in kwargs:
            pattern = RE_COM.sub('', pattern)

        self.re2_obj = ffi.gc(libre2.RE2_new(pattern, flags & I != 0),
                              libre2.RE2_delete)
        flag = libre2.ok(self.re2_obj)
        if not flag:
            ret = libre2.get_error_msg(self.re2_obj)
            raise ValueError(ffi.string(ret).decode("utf-8"))

        self.libre2 = libre2

    @staticmethod
    def __convertToBinaryUTF8(data):
        if isinstance(data, six.text_type):
            return data.encode("utf-8")
        return data

    @staticmethod
    def __rangeToTuple(r):
        """Convert a CFFI/CRE2 range object to a Python tuple"""
        return (r.start, r.end)

    def search(self, data, flags=0):
        return self.__search(data, False)  # 0 => UNANCHORED

    def match(self, data, flags=0):
        return self.__search(data, True)  # 0 => ANCHOR_BOTH

    def __search(self, s, fullMatch=False, startidx=0):
        """
        Search impl that can either be performed in full or partial match
        mode, depending on the anchor argument
        """
        # RE2 needs binary data, so we'll need to encode it
        data = CRE2.__convertToBinaryUTF8(s)

        matchobj = libre2.FindSingleMatch(self.re2_obj, data, fullMatch, startidx)
        if matchobj.hasMatch:
            ranges = [CRE2.__rangeToTuple(matchobj.ranges[i])
                      for i in range(matchobj.numGroups)]
            ret = MatchObject(self, s, ranges)
        else:
            ret = None
        # Cleanup C API objects
        libre2.FreeREMatchResult(matchobj)
        return ret

    def findall(self, data, flags=0):
        return list(self.finditer(data, flags))

    def finditer(self, s, flags=0, generateMO=False):
        """
        re.finditer-compatible function.
        Set generateMO to True to generate match objects instead of tuples.
        """
        data = CRE2.__convertToBinaryUTF8(s)

        # Anchor currently fixed to 0 == UNANCHORED
        matchobj = libre2.FindAllMatches(self.re2_obj, data, 0, 0)

        if generateMO:
            for ranges in CRE2.__parseFindallMatchObj(matchobj):
                yield MatchObject(self, s, ranges)
        else:  # Do not generate match objects
            for tp in CRE2.__parseFindallMatchObj(matchobj):
                # len == 1 => No groups, only full match:
                if len(tp) == 1:
                    yield s[slice(*tp[0])]
                elif len(tp) == 2:
                    yield s[slice(*tp[1])]
                else:
                    yield tuple((s[slice(*t)] for t in tp[1:]))

        libre2.FreeREMultiMatchResult(matchobj)

    @staticmethod
    def __parseFindallMatchObj(matchobj):
        # Define
        n = matchobj.numMatches
        m = matchobj.numGroups
        # Iterate
        for i in range(n):
            yield tuple(CRE2.__rangeToTuple(matchobj.ranges[i][j])
                        for j in range(m))

    def _sub_function(self, fn, s, count=0, flags=0):
        """This is internally called if repl in re.sub() is a function"""
        # Find all matches
        ofs = 0  # We might accumulate index shifts if len(replacement) != len(match)
        for match in self.finditer(s, flags, generateMO=True):
            start, end = match.span(0)
            replacement = fn(match)
            #print(match.group(0) + " / " + replacement)
            s = s[:start + ofs] + replacement + s[end + ofs:]
            ofs += len(replacement) - len(match.group(0))
        return s

    def sub(self, repl, s, count=0, flags=0):
        # Handle function repl argument. See re docs for behaviour
        if hasattr(repl, '__call__'):
            return self._sub_function(repl, s, count, flags)

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

def sub(pattern, repl, string, count=0, flags=0):
    """
    Module-level sub function. See re.sub() for details
    Count is currently unsupported.
    """
    rgx = compile(pattern, flags & I)
    return rgx.sub(repl, string, count, flags)

def search(pattern, string, flags=0):
    """
    Module-level sub function. See re.search() for details
    """
    rgx = compile(pattern, flags & I)
    return rgx.search(string, flags)

def match(pattern, string, flags=0):
    """
    Module-level match function. See re.match() for details
    """
    rgx = compile(pattern, flags & I)
    return rgx.match(string, flags)

def finditer(pattern, string, flags=0):
    """
    Module-level finditer function. See re.finditer() for details
    """
    rgx = compile(pattern, flags & I)
    for result in rgx.finditer(string, flags):
        yield result

def findall(pattern, string, flags=0):
    """
    Module-level findall function. See re.findall() for details
    """
    rgx = compile(pattern, flags & I)
    return rgx.findall(string, flags)

def set_max_memory_budget(maxmem):
    """
    Set the default maximum memory budget for new regular expressions.
    The RE2 default is 8 MiB.
    The cffi_re2 default is 128 MiB.
    Under some circumstances it might be required to increase this hard limit.
    Affects only regexes compiled after this call, so it is recommended to do this
    directly after importing cffi_re2.
    """
    libre2.RE2_SetMaxMemory(maxmem)
