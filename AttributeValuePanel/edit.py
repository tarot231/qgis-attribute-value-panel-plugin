# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Attribute Value Panel
                                 A QGIS plugin
 Lists attribute values of selected features vertically
                             -------------------
        begin                : 2025-11-30
        copyright            : (C) 2025 by Tarot Osuji
        email                : tarot@sdf.org
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import math
from qgis.PyQt.QtCore import QRegularExpression
from qgis.PyQt.QtGui import QValidator
from qgis.gui import QgsFilterLineEdit

class IntLengthValidator(QValidator):
    regex = QRegularExpression(r'^0$|' r'^-?[1-9]\d*$')

    def __init__(self, length, is_legacy, parent=None):
        super().__init__(parent)
        self.length = length
        self.is_legacy = is_legacy

    def validate(self, input, pos):
        if not input:
            return (QValidator.State.Acceptable, input, pos)
        if self.regex.match(input).hasMatch():
            if self.length <= 0:
                return (QValidator.State.Acceptable, input, pos)
            v = int(input)
            if len(input) <= self.length + (not self.is_legacy and v < 0):
                return (QValidator.State.Acceptable, input, pos)
        if input == '-':
            if not (self.is_legacy and self.length == 1):
                return (QValidator.State.Intermediate, input, pos)
        return (QValidator.State.Invalid, input, pos)


class IntFilterLineEdit(QgsFilterLineEdit):
    def __init__(self, length=0, is_legacy=False, parent=None):
        super().__init__(parent)
        self.setValidator(IntLengthValidator(length, is_legacy, self))


def calc_max_float_value(length, prec):
    if length <= 15:
        f = (10 ** length - 1) / (10 ** prec)
    else:
        f = math.nextafter(10 ** (length - prec), -math.inf)
    return f


class DoubleLengthValidator(QValidator):
    regex = QRegularExpression(r'^-?\.\d+$|'
                               r'^-?0(\.\d*)?$|'
                               r'^-?[1-9]\d*(\.\d*)?$')

    def __init__(self, length, prec, is_legacy, parent=None):
        super().__init__(parent)
        self.length = length
        self.prec = prec
        self.is_legacy = is_legacy
        self.top = calc_max_float_value(length, prec)
        self.bottom = -calc_max_float_value(length - is_legacy, prec)

    def validate(self, input, pos):
        if not input:
            return (QValidator.State.Acceptable, input, pos)
        if self.regex.match(input).hasMatch():
            if self.length <= 0:
                return (QValidator.State.Acceptable, input, pos)
            v = float(input)
            try:
                idx = input.index('.')
            except ValueError:
                idx = len(input)
            # Include the minus sign
            length_ = self.length + (not self.is_legacy and v < 0)
            if (idx <= length_ - self.prec) and \
                    (len(input) <= idx + 1 + self.prec):
                if self.bottom <= v <= self.top:
                    return (QValidator.State.Acceptable, input, pos)
                else:
                    return (QValidator.State.Intermediate, input, pos)
        if input == '-':
            if not (self.is_legacy and (self.length - self.prec) == 1):
                return (QValidator.State.Intermediate, input, pos)
        return (QValidator.State.Invalid, input, pos)

    def fixup(self, input):
        try:
            f = float(input)
        except ValueError:
            return input
        if f > self.top:
            f = self.top
        else:
            f = self.bottom
        s = ('%%.%df' % self.prec) % f
        return s


class DoubleFilterLineEdit(QgsFilterLineEdit):
    def __init__(self, length=0, prec=0, is_legacy=False, parent=None):
        super().__init__(parent)
        self.setValidator(DoubleLengthValidator(length, prec, is_legacy, self))


class ByteLengthValidator(QValidator):
    def __init__(self, byte_length, encoding, parent=None):
        super().__init__(parent)
        self.byte_length = byte_length
        self.encoding = encoding
        self.prev_value = None

    def validate(self, input, pos):
        try:
            if not input:
                return (QValidator.State.Acceptable, input, pos)
            try:
                if len(input.encode(self.encoding)) <= self.byte_length:
                    return (QValidator.State.Acceptable, input, pos)
                fixed = self.fixup(input)
                if fixed != self.prev_value:
                    return (QValidator.State.Acceptable, fixed, min(pos, len(fixed)))
            except UnicodeEncodeError:
                pass
            return (QValidator.State.Invalid, input, pos)
        finally:
            self.prev_value = input

    def fixup(self, input):
        encoded = input.encode(self.encoding)
        if len(encoded) > self.byte_length:
            truncated = encoded[:self.byte_length]
            while truncated:
                try:
                    return truncated.decode(self.encoding)
                except UnicodeDecodeError:
                    truncated = truncated[:-1]
        return input


class ByteFilterLineEdit(QgsFilterLineEdit):
    def __init__(self, byte_length=0xFFFF, encoding='utf-8', is_legacy=False, parent=None):
        super().__init__(parent)
        if is_legacy:
            self.setValidator(ByteLengthValidator(byte_length, encoding, self))
        elif byte_length > 0:
            self.setMaxLength(byte_length)


if __name__ == '__main__':
    from qgis.PyQt.QtWidgets import QApplication, QWidget, QVBoxLayout
    app = QApplication([])
    vbox = QVBoxLayout()

    edit = IntFilterLineEdit(2, is_legacy=True)
    edit.setValue('IntFilterLineEdit')
    vbox.addWidget(edit)

    edit = DoubleFilterLineEdit(3, 1, is_legacy=True)
    edit.setValue('DoubleFilterLineEdit')
    vbox.addWidget(edit)

    edit = ByteFilterLineEdit(10, is_legacy=True)
    edit.setValue('ByteFilterLineEdit')
    vbox.addWidget(edit)

    w = QWidget()
    w.setLayout(vbox)
    w.show()
    app.exec()
