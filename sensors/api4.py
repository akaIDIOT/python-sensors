#!/usr/bin/env python
# -*- coding: utf-8 -*-
from ctypes import *

from sensors import common
from sensors import stdc
from sensors.common import *


__all__ = ['API_VERSION', 'DEFAULT_CONFIG_FILENAME', 'iter_detected_chips']

API_VERSION = 4
common.DEFAULT_CONFIG_FILENAME = DEFAULT_CONFIG_FILENAME = '/etc/sensors3.conf'


class Subfeature(Structure):
    _fields_ = [
        ('_name', c_char_p),
        ('number', c_int),
        ('type', c_int),
        ('mapping', c_int),
        ('flags', c_uint),
    ]

    def __repr__(self):
        return '<%s name=%r number=%d type=%d mapping=%d flags=%08x>' % (
            self.__class__.__name__,
            self.name,
            self.number,
            self.type,
            self.mapping,
            self.flags
        )

    @property
    def name(self):
        return stdc.really_str(self._name)

    def get_value(self):
        result = c_double()
        _get_value(byref(self.parent.chip), self.number, byref(result))
        return result.value


SUBFEATURE_P = POINTER(Subfeature)


class Feature(Structure):
    _fields_ = [
        ('_name', c_char_p),
        ('number', c_int),
        ('type', c_int),
        ('_first_subfeature', c_int),
        ('_padding1', c_int),
    ]

    def __repr__(self):
        return '<%s name=%r number=%r type=%r>' % (
            self.__class__.__name__,
            self.name,
            self.number,
            self.type
        )

    def __iter__(self):
        number = c_int(0)
        while True:
            result_p = _get_all_subfeatures(
                byref(self.chip),
                byref(self),
                byref(number)
            )
            if not result_p:
                break
            result = result_p.contents
            result.chip = self.chip
            result.parent = self
            yield result

    @property
    def name(self):
        return stdc.really_str(self._name)

    @property
    def label(self):
        #
        # TODO Maybe this is a memory leak!
        #
        return stdc.really_str(_get_label(byref(self.chip), byref(self)))

    def get_value(self):
        #
        # TODO Is the first always the correct one for all feature types?
        #
        return next(iter(self)).get_value()


FEATURE_P = POINTER(Feature)


class Bus(Structure):
    TYPE_ANY = -1
    NR_ANY = -1

    _fields_ = [
        ('type', c_short),
        ('nr', c_short),
    ]

    def __str__(self):
        return (
            '*' if self.type == self.TYPE_ANY
            else stdc.really_str(_get_adapter_name(byref(self)))
        )

    def __repr__(self):
        return '%s(%r, %r)' % (self.__class__.__name__, self.type, self.nr)

    @property
    def has_wildcards(self):
        return self.type == self.TYPE_ANY or self.nr == self.NR_ANY


BUS_P = POINTER(Bus)


class Chip(Structure):
    #
    # TODO Move common stuff into `AbstractChip` class.
    #
    _fields_ = [
        ('prefix', c_char_p),
        ('bus', Bus),
        ('addr', c_int),
        ('path', c_char_p),
    ]

    PREFIX_ANY = None
    ADDR_ANY = -1

    def __new__(cls, *args):
        result = super(Chip, cls).__new__(cls)
        if args:
            _parse_chip_name(stdc.arg(args[0]), byref(result))
        return result

    def __init__(self, *_args):
        Structure.__init__(self)
        #
        # Need to bind the following to the instance so it is available in
        #  `__del__()` when the interpreter shuts down.
        #
        self._free_chip_name = _free_chip_name
        self.byref = byref

    def __del__(self):
        if self._b_needsfree_:
            self._free_chip_name(self.byref(self))

    def __repr__(self):
        return '<%s prefix=%r bus=%r addr=%r path=%r>' % (
            (
                self.__class__.__name__,
                self.prefix,
                self.bus,
                self.addr,
                self.path
            )
        )

    def __str__(self):
        buffer_size = 200
        result = create_string_buffer(buffer_size)
        used = _snprintf_chip_name(result, len(result), byref(self))
        # FIXME: _snprintf_chip_name returns None in python 3, fails the assertion
        # assert used < buffer_size
        return stdc.really_str(result.value)

    def __iter__(self):
        number = c_int(0)
        while True:
            result_p = _get_features(byref(self), byref(number))
            if not result_p:
                break
            result = result_p.contents
            result.chip = self
            yield result

    @property
    def adapter_name(self):
        return str(self.bus)

    @property
    def has_wildcards(self):
        return (
            self.prefix == self.PREFIX_ANY
            or self.addr == self.ADDR_ANY
            or self.bus.has_wildcards
        )


CHIP_P = POINTER(Chip)

_parse_chip_name = SENSORS_LIB.sensors_parse_chip_name
_parse_chip_name.argtypes = [c_char_p, CHIP_P]
_parse_chip_name.restype = c_int
_parse_chip_name.errcheck = _error_check

_free_chip_name = SENSORS_LIB.sensors_free_chip_name
_free_chip_name.argtypes = [CHIP_P]
_free_chip_name.restype = None

_snprintf_chip_name = SENSORS_LIB.sensors_snprintf_chip_name
_snprintf_chip_name.argtypes = [c_char_p, c_size_t, CHIP_P]
_snprintf_chip_name.restype = c_int
_snprintf_chip_name.errcheck = _error_check

_get_adapter_name = SENSORS_LIB.sensors_get_adapter_name
_get_adapter_name.argtypes = [BUS_P]
_get_adapter_name.restype = c_char_p

_get_label = SENSORS_LIB.sensors_get_label
_get_label.argtypes = [CHIP_P, FEATURE_P]
_get_label.restype = c_char_p

_get_value = SENSORS_LIB.sensors_get_value
_get_value.argtypes = [CHIP_P, c_int, POINTER(c_double)]
_get_value.restype = c_int
_get_value.errcheck = _error_check

#
# TODO sensors_set_value()
# TODO sensors_do_chip_sets()
#

_get_detected_chips = SENSORS_LIB.sensors_get_detected_chips
_get_detected_chips.argtypes = [CHIP_P, POINTER(c_int)]
_get_detected_chips.restype = CHIP_P

_get_features = SENSORS_LIB.sensors_get_features
_get_features.argtypes = [CHIP_P, POINTER(c_int)]
_get_features.restype = FEATURE_P

_get_all_subfeatures = SENSORS_LIB.sensors_get_all_subfeatures
_get_all_subfeatures.argtypes = [CHIP_P, FEATURE_P, POINTER(c_int)]
_get_all_subfeatures.restype = SUBFEATURE_P

#
# TODO sensors_get_subfeature() ?
#


def iter_detected_chips(chip_name='*-*'):
    chip = Chip(chip_name)
    number = c_int(0)
    while True:
        result = _get_detected_chips(byref(chip), byref(number))
        if not result:
            break
        yield result.contents
