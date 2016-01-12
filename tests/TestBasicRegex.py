#!/usr/bin/env python
# -*- coding: utf-8 -*-
import cffi_re2
import sys
import re as pyre
if sys.version_info < (2, 7):
    from nose.tools import raises
    from nose_extra_tools import assert_is_not_none, assert_is_none, assert_equal, assert_true, assert_false
else:
    from nose.tools import raises, assert_is_not_none, assert_is_none, assert_equal, assert_true, assert_false

class TestBasicRegex(object):
    def test_basic_search(self):
        robj = cffi_re2.compile(r'b+')
        assert_is_not_none(robj.search('abbcd'))

    def test_basic_match(self):
        # Search-type regex should NOT match full string
        robj = cffi_re2.compile(r'b+')
        assert_is_none(robj.match('abbcd'))
        # This regex only matches the left end
        robj = cffi_re2.compile(r'[abc]+$')
        assert_is_none(robj.match('abbcd'))
        # Full match regex should match
        robj = cffi_re2.compile(r'[abcd]+')
        assert_is_not_none(robj.match('abbcd'))
        # Regex match should be left-anchored, not both-anchored
        robj = cffi_re2.compile(r'a+')
        assert_is_not_none(robj.match('aaab'))
        assert_is_none(robj.match('baaab'))

    def test_re_compatibility(self):
        """Test compatibility with the Python re library"""
        cm = cffi_re2.match(r'b+', 'abbcd')
        rm = pyre.match(r'b+', 'abbcd')
        assert_equal(cm, rm)
        # Match without groups
        cm = cffi_re2.match(r'[abc]+', 'abbcd')
        rm = pyre.match(r'[abc]+', 'abbcd')
        assert_equal(cm.groups(), rm.groups())
        # Full match regex should match
        cm = cffi_re2.match(r'([abc]+)', 'abbcd')
        rm = pyre.match(r'([abc]+)', 'abbcd')
        assert_equal(cm.groups(), rm.groups())
        assert_equal(cm.group(0), rm.group(0))
        assert_equal(cm.group(1), rm.group(1))
        cm = cffi_re2.match(r'([ab]+)(c+)', 'abbcd')
        rm = pyre.match(r'([ab]+)(c+)', 'abbcd')
        assert_equal(cm.groups(), rm.groups())
        assert_equal(cm.group(0), rm.group(0))
        assert_equal(cm.group(1), rm.group(1))
        assert_equal(cm.group(2), rm.group(2))

    def test_sub_basic(self):
        robj = cffi_re2.compile(r'b+')
        assert_equal(robj.sub('', 'abbcbbd'), 'acd')

    def test_basic_groups(self):
        robj = cffi_re2.compile(r'a(b+)')
        mo = robj.search("abbc")
        assert_is_not_none(mo)
        assert_equal(mo.groups(), ("bb",))

    def test_basic_findall(self):
        robj = cffi_re2.compile(r'a(b+)')
        mo = robj.findall("abbcdefabbbbca")
        assert_is_not_none(mo)
        assert_equal(mo, ["bb", "bbbb"])

    def test_findall_subgroups(self):
        mo = cffi_re2.findall(r'ab+', "abbcdefabbbbca")
        assert_equal(mo, ["abb", "abbbb"])
        mo = cffi_re2.findall(r'a(b+)', "abbcdefabbbbca")
        assert_equal(mo, ["bb", "bbbb"])
        mo = cffi_re2.findall(r'(a)(b+)', "abbcdefabbbbca")
        assert_equal(mo, [("a", "bb"), ("a", "bbbb")])
        mo = cffi_re2.findall(r'(a)(b)(b+)', "abbcdefabbbbca")
        assert_equal(mo, [("a", "b", "b"), ("a", "b", "bbb")])

    def test_medium_complexity(self):
        """Check some medium complexity regexes. Examples from github.com/ulikoehler/KATranslationCheck"""
        # 1
        rgx = cffi_re2.compile(r"\b[Ii]nto\b")
        assert_is_not_none(rgx.search("Into the darkness"))
        assert_is_not_none(rgx.search("I went into the darkness"))
        assert_is_none(rgx.search("abcde beintoaqe aqet"))
        # 2
        rgx = cffi_re2.compile(r"\d+\$\s*dollars?")
        assert_is_not_none(rgx.search("12$ dollars"))
        assert_is_not_none(rgx.match("12$ dollars"))
        assert_is_not_none(rgx.match("1$ dollar"))
        assert_is_not_none(rgx.match("1$  dollar"))
        assert_is_not_none(rgx.match("1$  dollars"))

    def test_module_level_functions(self):
        """
        Quick test of module-level functions.
        These are generally expected to call the compiled counterparts,
         so these tests do not check all aspects
        """
        assert_equal(cffi_re2.findall(r'a(b+)', "abbcdefabbbbca"), ["bb", "bbbb"])
        assert_equal(cffi_re2.sub(r'b+', '', 'abbcbbd'), 'acd')
        assert_is_not_none(cffi_re2.search(r'b+', 'abbcbbd'))
        assert_is_none(cffi_re2.match(r'b+', 'abbcbbd'))
        assert_is_not_none(cffi_re2.match(r'b+', 'bbbbb'))

class TestFlags(object):
    def test_flag_ignorecase(self):
        rgx_ci = cffi_re2.compile(r'a(b+)$', flags=cffi_re2.IGNORECASE)
        rgx_cs = cffi_re2.compile(r'a(b+)$')
        # Check case sensitive
        assert_is_none(rgx_cs.match("AB"))
        assert_is_none(rgx_cs.match("Ab"))
        assert_is_none(rgx_cs.match("aB"))
        assert_is_none(rgx_cs.match("aBb"))
        assert_is_none(rgx_cs.match("abB"))
        assert_is_not_none(rgx_cs.match("ab"))
        assert_is_not_none(rgx_cs.match("abb"))
        # Check case insensitive
        assert_is_not_none(rgx_ci.match("AB"))
        assert_is_not_none(rgx_ci.match("Ab"))
        assert_is_not_none(rgx_ci.match("aB"))
        assert_is_not_none(rgx_ci.match("aBb"))
        assert_is_not_none(rgx_ci.match("abB"))
        assert_is_not_none(rgx_ci.match("ab"))
        assert_is_not_none(rgx_ci.match("abb"))

class TestChineseRegex(object):
    """Written by Github user @vls"""
    def test_match_chinese(self):
        robj = cffi_re2.compile('梦[^一-龥]*幻[^一-龥]*西[^一-龥]*游')

        assert_true(robj.search('梦1幻2西3游'))
        assert_false(robj.search('梦倩女幻幽魂西2游'))
    def test_sub_chinese(self):
        robj = cffi_re2.compile('梦[^一-龥]*幻[^一-龥]*西[^一-龥]*游')
        assert_equal(robj.sub('倩女', '梦幻西游好玩吗?'), u'倩女好玩吗?')

    @raises(ValueError)
    def test_invalid_regex(self):
        p = '(?!=.*[没不])'
        robj = cffi_re2.compile(p)

    @raises(ValueError)
    def test_invalid_regex_2(self):
        p = '(?<![没不])'
        robj = cffi_re2.compile(p)
