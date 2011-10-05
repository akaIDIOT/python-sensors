#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sensors


def main():
    sensors.init(sensors.DEFAULT_CONFIG_FILENAME)
    
    #chip_a = Chip('k8temp-pci-00c3')
    #chip_b = Chip('k8temp-*')
    #chip_c = Chip('test-*')
    #print repr(chip_a)
    #print repr(chip_b)
    #print repr(chip_c)

    #print chip_a.has_wildcards
    #print chip_b.has_wildcards

    #print chip_a.adapter_name
    #print chip_b.adapter_name

    for chip in sensors.iter_detected_chips():
        print chip
        print 'Adapter:', chip.adapter_name
        for feature in chip:
            print '%s (%r): %.1f' % (
                feature.name, feature.label, feature.get_value()
            )
            for subfeature in feature:
                print '  %s: %.1f' % (subfeature.name, subfeature.get_value())
        print
    
    sensors.cleanup()


if __name__ == '__main__':
    main()
