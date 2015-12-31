#!/usr/bin/env python
# -*- coding: utf-8 -*-
import cffi_re2
from nose.tools import raises, assert_is_not_none, assert_is_none, assert_equal

class TestBasicRegex(object):
    def test_basic_search(self):
        robj = cffi_re2.compile('b+')
        assert_is_not_none(robj.search('abbcd'))

    def test_basic_match(self):
        # Search-type regex should NOT match full string
        robj = cffi_re2.compile('b+')
        assert_is_none(robj.match('abbcd'))
        # This regex only matches the left end
        robj = cffi_re2.compile('[abc]+')
        assert_is_none(robj.match('abbcd'))
        # Full match regex should match
        robj = cffi_re2.compile('[abcd]+')
        assert_is_not_none(robj.match('abbcd'))

    def test_sub_basic(self):
        robj = cffi_re2.compile('b+')
        assert_equal(robj.sub('', 'abbcbbd'), 'acd')

    def test_basic_groups(self):
        robj = cffi_re2.compile('a(b+)')
        mo = robj.search("abbc")
        assert_is_not_none(mo)
        assert_equal(mo.groups(), ["bb"])

    def test_basic_findall(self):
        robj = cffi_re2.compile('a(b+)')
        mo = robj.findall("abbcdefabbbbca")
        assert_is_not_none(mo)
        assert_equal(mo, ["abb", "abbbb"])

class TestChineseRegex(object):
    """Written by Github user @vls"""
    def test_match_chinese(self):
        robj = cffi_re2.compile('梦[^一-龥]*幻[^一-龥]*西[^一-龥]*游')

        assert robj.search('梦1幻2西3游')
        assert not robj.search('梦倩女幻幽魂西2游')
    def test_sub_chinese(self):
        robj = cffi_re2.compile('梦[^一-龥]*幻[^一-龥]*西[^一-龥]*游')

        assert robj.sub('倩女', '梦幻西游好玩吗?') == '倩女好玩吗?'

    @raises(ValueError)
    def test_invalid_regex(self):
        p = '(?!=.*[没不])'
        robj = cffi_re2.compile(p)

    @raises(ValueError)
    def test_invalid_regex_2(self):
        p = '(?<![没不])'
        robj = cffi_re2.compile(p)
