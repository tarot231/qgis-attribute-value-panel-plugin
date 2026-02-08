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

    def __init__(self, length=0, is_legacy=False, parent=None):
        super().__init__(parent)
        self.length = length
        self.is_legacy = is_legacy

    def validate(self, input_, pos):
        if not input_:
            return (QValidator.State.Acceptable, input_, pos)
        if self.regex.match(input_).hasMatch():
            if self.length == 0:
                return (QValidator.State.Acceptable, input_, pos)
            v = int(input_)
            if len(input_) <= self.length + (not self.is_legacy and v < 0):
                return (QValidator.State.Acceptable, input_, pos)
        if input_ == '-':
            if not (self.is_legacy and self.length == 1):
                return (QValidator.State.Intermediate, input_, pos)
        return (QValidator.State.Invalid, input_, pos)


class IntFilterLineEdit(QgsFilterLineEdit):
    def __init__(self, length=0, is_legacy=False, parent=None):
        super().__init__(parent)
        if length < 0:
            length = 0
        self.is_ready = False
        self.validator_ = IntLengthValidator(length, is_legacy, self)
        self.valueChanged.connect(self.slot_valueChanged)

    def slot_valueChanged(self, value):
        if self.hasStateStored():
            # Calling restoreState() causes hasStateStored() to return False.
            self.is_ready = True
        if not self.is_ready:
            return
        state, _, _ = self.validator_.validate(value, 0)
        if state == QValidator.State.Invalid:
            self.blockSignals(True)
            self.restoreState()
            self.blockSignals(False)
        else:
            self.valueChanged.disconnect(self.slot_valueChanged)
            self.setValidator(self.validator_)


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

    def __init__(self, length, prec, is_legacy=False, parent=None):
        super().__init__(parent)
        self.length = length
        self.prec = prec
        self.is_legacy = is_legacy
        self.top = calc_max_float_value(length, prec)
        self.bottom = -calc_max_float_value(length - is_legacy, prec)

    def validate(self, input_, pos):
        if not input_:
            return (QValidator.State.Acceptable, input_, pos)
        if self.regex.match(input_).hasMatch():
            if self.length == 0:
                return (QValidator.State.Acceptable, input_, pos)
            v = float(input_)
            try:
                idx = input_.index('.')
            except ValueError:
                idx = len(input_)
            # Include the minus sign
            length_ = self.length + (not self.is_legacy and v < 0)
            if (idx <= length_ - self.prec) and \
                    (len(input_) <= idx + 1 + self.prec):
                if not (self.bottom <= v <= self.top):
                    return (QValidator.State.Intermediate, input_, pos)
                else:
                    return (QValidator.State.Acceptable, input_, pos)
        if input_ == '-':
            if not (self.is_legacy and (self.length - self.prec) == 1):
                return (QValidator.State.Intermediate, input_, pos)
        return (QValidator.State.Invalid, input_, pos)

    def fixup(self, input_):
        try:
            f = float(input_)
        except ValueError:
            return input_
        if f > self.top:
            f = self.top
        elif f < self.bottom:
            f = self.bottom
        s = ('%%.%df' % self.prec) % f
        return s


class DoubleFilterLineEdit(QgsFilterLineEdit):
    def __init__(self, length=0, prec=0, is_legacy=False, parent=None):
        super().__init__(parent)
        if length < 0:
            length = 0
        self.is_ready = False
        self.validator_ = DoubleLengthValidator(length, prec, is_legacy, self)
        self.valueChanged.connect(self.slot_valueChanged)

    def slot_valueChanged(self, value):
        if self.hasStateStored():
            # Calling restoreState() causes hasStateStored() to return False.
            self.is_ready = True
        if not self.is_ready:
            return
        state, _, _ = self.validator_.validate(value, 0)
        if state == QValidator.State.Invalid:
            self.blockSignals(True)
            self.restoreState()
            self.blockSignals(False)
        else:
            self.valueChanged.disconnect(self.slot_valueChanged)
            self.setValidator(self.validator_)


class ByteLengthValidator(QValidator):
    def __init__(self, byte_length, encoding='utf-8', parent=None):
        super().__init__(parent)
        self.byte_length = byte_length
        self.encoding = encoding

    def validate(self, input_, pos):
        if not input_:
            return (QValidator.State.Acceptable, input_, pos)
        try:
            if len(input_.encode(self.encoding)) <= self.byte_length:
                return (QValidator.State.Acceptable, input_, pos)
            else:
                return (QValidator.State.Intermediate, input_, pos)
        except UnicodeEncodeError:
            return (QValidator.State.Invalid, input_, pos)

    def fixup(self, input_):
        try:
            encoded = input_.encode(self.encoding)
            if len(encoded) > self.byte_length:
                truncated = encoded[:self.byte_length]
                while truncated:
                    try:
                        return truncated.decode(self.encoding)
                    except UnicodeDecodeError:
                        truncated = truncated[:-1]
            return input_
        except:
            return None


class ByteFilterLineEdit(QgsFilterLineEdit):
    def __init__(self, byte_length=0xFFFF, encoding='utf-8', is_legacy=False, parent=None):
        super().__init__(parent)
        if not byte_length:
            return
        self.byte_length = byte_length
        self.is_legacy = is_legacy
        self.is_ready = False
        self.validator_ = ByteLengthValidator(byte_length, encoding, self)
        self.valueChanged.connect(self.slot_valueChanged)
        self._updating = False

    def slot_valueChanged(self, value):
        if self.hasStateStored():
            # Calling restoreState() causes hasStateStored() to return False.
            self.is_ready = True
        if not self.is_ready:
            return
        if not self.is_legacy:
            self.valueChanged.disconnect(self.slot_valueChanged)
            self.setMaxLength(self.byte_length)
            return
        elif not self.validator() is self.validator_:
            self.setValidator(self.validator_)
        if self._updating:
            return
        if not value:
            return
        state, _, _ = self.validator_.validate(value, 0)
        if state == QValidator.State.Intermediate:
            self._updating = True
            cursor_pos = self.cursorPosition()
            fixed_value = self.validator_.fixup(value)
            self.setValue(fixed_value)
            # For character inserton
            self.setCursorPosition(min(cursor_pos, len(fixed_value)))
            self._updating = False


if __name__ == '__main__':
    from qgis.PyQt.QtWidgets import QApplication, QDialog, QVBoxLayout
    app = QApplication([])
    layout = QVBoxLayout()

    edit = IntFilterLineEdit(2, is_legacy=True)
    edit.setText('IntFilterLineEdit')
    edit.storeState()
    layout.addWidget(edit)

    edit = DoubleFilterLineEdit(3, 1, is_legacy=True)
    edit.setText('DoubleFilterLineEdit')
    edit.storeState()
    layout.addWidget(edit)

    edit = ByteFilterLineEdit(10, is_legacy=True)
    edit.setText('ByteFilterLineEdit')
    edit.storeState()
    layout.addWidget(edit)

    dlg = QDialog()
    dlg.setLayout(layout)
    dlg.exec_()
