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

from qgis.PyQt.QtCore import Qt, QDate, QTime, QDateTime
from qgis.PyQt.QtGui import QPalette, QStandardItemModel
from qgis.PyQt.QtWidgets import *
from qgis.core import Qgis, QgsApplication, NULL
from qgis.gui import QgsFilterLineEdit, QgsDateEdit, QgsTimeEdit, QgsDateTimeEdit
if Qgis.QGIS_VERSION_INT >= 33800:
    FieldOrigin = Qgis.FieldOrigin
else:
    from qgis.core import QgsFields
    FieldOrigin = QgsFields.FieldOrigin
    FieldOrigin.Provider = FieldOrigin.OriginProvider
    FieldOrigin.Edit = FieldOrigin.OriginEdit
if __package__:
    from .edit import IntFilterLineEdit, DoubleFilterLineEdit, ByteFilterLineEdit
    from .compat_type import CompatType
else:
    from edit import IntFilterLineEdit, DoubleFilterLineEdit, ByteFilterLineEdit
    from compat_type import CompatType


def str_to_bool(s):
    if s.lower() in {'n', 'no', 'f', 'false', 'off', '0'}:
        return False
    return bool(s)


class AttributeValueModel(QStandardItemModel):
    FIELD_COLUMN = 0
    VALUE_COLUMN = 1

    def __init__(self):
        super().__init__()
        self.setHorizontalHeaderLabels([self.tr('Field'), self.tr('Value')])

    def flags(self, index):
        flags = super().flags(index)
        if index.column() == self.VALUE_COLUMN:
            field_index = index.siblingAtColumn(self.FIELD_COLUMN)
            field = field_index.data(Qt.ItemDataRole.EditRole)
            origin = field_index.data(Qt.ItemDataRole.UserRole)
            if origin in (FieldOrigin.Provider, FieldOrigin.Edit):
                if field.type() in (
                        CompatType.Bool,
                        CompatType.Int,
                        CompatType.LongLong,
                        CompatType.Double,
                        CompatType.QString,
                        CompatType.QDate,
                        CompatType.QTime,
                        CompatType.QDateTime,
                ):
                    return flags | Qt.ItemFlag.ItemIsEditable
        return flags & ~Qt.ItemFlag.ItemIsEditable


class AttributeValueView(QTreeView):
    def __init__(self):
        super().__init__()
        self.setAlternatingRowColors(True)
        self.setRootIsDecorated(False)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.header().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        # https://stackoverflow.com/q/27248148
        self.setItemDelegateForColumn(
                AttributeValueModel.FIELD_COLUMN, self.FieldItemDelegate(self))
        self.setItemDelegateForColumn(
                AttributeValueModel.VALUE_COLUMN, self.ValueItemDelegate(self))

        self.is_legacy_format = False
        self.encoding = 'utf-8'

    def set_editable(self, editable):
        self.setEditTriggers(
                QTreeView.EditTrigger.AllEditTriggers
                if editable else
                QTreeView.EditTrigger.NoEditTriggers)

    class FieldItemDelegate(QStyledItemDelegate):
        def displayText(self, value, locale=None):
            return value.displayNameWithAlias()

    class ValueItemDelegate(QStyledItemDelegate):
        def displayText_(self, index):
            data = index.data(Qt.ItemDataRole.EditRole)
            field = index.siblingAtColumn(AttributeValueModel.FIELD_COLUMN
                    ).data(Qt.ItemDataRole.EditRole)
            if (field.type() == CompatType.QVariantMap or
                field.typeName().endswith('List')):
                strs = data
            else:
                strs = (field.displayString(x) for x in data)
            return ', '.join(strs)

        def paint(self, painter, option, index):
            opt = QStyleOptionViewItem(option)
            self.initStyleOption(opt, index)

            data = index.data(Qt.ItemDataRole.EditRole)
            if len(data) > 1:
                opt.font.setItalic(True)
            if NULL in data:
                opt.font.setItalic(True)
                opt.palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.gray)
            opt.text = self.displayText_(index)

            style = opt.widget.style() if opt.widget else QApplication.style()
            style.drawControl(style.ControlElement.CE_ItemViewItem, opt, painter)

        def createEditor(self, parent, option, index):
            field = index.siblingAtColumn(AttributeValueModel.FIELD_COLUMN
                    ).data(Qt.ItemDataRole.EditRole)
            if field.type() == CompatType.QDate:
                editor = QgsDateEdit(parent)
                editor.dateValueChanged.connect(
                        lambda: setattr(editor, 'value_changed_', True))
            elif field.type() == CompatType.QTime:
                editor = QgsTimeEdit(parent)
                editor.timeValueChanged.connect(
                        lambda: setattr(editor, 'value_changed_', True))
            else:
                if field.type() == CompatType.QDateTime:
                    editor = QgsDateTimeEdit(parent)
                else:
                    if field.type() in (CompatType.Int, CompatType.LongLong):
                        editor = IntFilterLineEdit(field.length(),
                                self.parent().is_legacy_format, parent)
                    elif field.type() == CompatType.Double:
                        editor = DoubleFilterLineEdit(field.length(), field.precision(),
                                self.parent().is_legacy_format, parent)
                    elif field.type() == CompatType.QString:
                        editor = ByteFilterLineEdit(field.length(), self.parent().encoding,
                                self.parent().is_legacy_format, parent)
                    else:
                        editor = QgsFilterLineEdit(parent)
                    editor.setNullValue(QgsApplication.nullRepresentation())
                editor.valueChanged.connect(
                        lambda: setattr(editor, 'value_changed_', True))
            return editor

        def setEditorData(self, editor, index):
            first = next(iter(index.data()))
            if isinstance(editor, QgsDateEdit):
                if first:
                    editor.setDate(first)
            elif isinstance(editor, QgsTimeEdit):
                if first:
                    editor.setTime(first)
            elif isinstance(editor, QgsDateTimeEdit):
                if first:
                    editor.setDateTime(first)
            else:
                # TODO: https://doc.qt.io/qt-6/qlineedit.html#setValidator
                editor.setText(self.displayText_(index))
            setattr(editor, 'value_changed_', False)

        def setModelData(self, editor, model, index):
            if not getattr(editor, 'value_changed_', False):
                return
            elif editor.isNull():
                value = NULL
            elif isinstance(editor, QgsDateEdit):
                value = editor.date()
            elif isinstance(editor, QgsTimeEdit):
                value = editor.time()
            elif isinstance(editor, QgsDateTimeEdit):
                value = editor.dateTime()
            else:
                text = editor.text()
                field = index.siblingAtColumn(AttributeValueModel.FIELD_COLUMN
                        ).data(Qt.ItemDataRole.EditRole)
                try:
                    if field.type() == CompatType.Bool:
                        value = str_to_bool(text) if len(text) else NULL
                    elif field.type() == CompatType.Int:
                        value = int(text) if len(text) else NULL
                    elif field.type() == CompatType.LongLong:
                        value = int(text) if len(text) else NULL
                    elif field.type() == CompatType.Double:
                        value = float(text) if len(text) else NULL
                    else:
                        value = text
                except ValueError:
                    return
            model.setData(index, (value,))


class AttributeValueDock(QDockWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = AttributeValueView()
        self.view.setModel(AttributeValueModel())
        self.setWidget(self.view)


if __name__ == '__main__':
    from qgis.PyQt.QtGui import QStandardItem
    from qgis.core import QgsField
    app = QApplication([])
    dock = AttributeValueDock()
    for k, v in [(QgsField('bool', CompatType.Bool), {True}),
                 (QgsField('int', CompatType.Int), {NULL}),
                 (QgsField('double', CompatType.Double), {123.45, 678.90}),
                 (QgsField('QString', CompatType.QString), {'abc', 'def', NULL}),
                 (QgsField('QDate', CompatType.QDate), {QDate.currentDate()}),
                 (QgsField('QTime', CompatType.QTime), [QTime.currentTime()]),
                 (QgsField('QDateTime', CompatType.QDateTime), [QDateTime.currentDateTime()]),
                ]:
        k_item = QStandardItem()
        k_item.setData(k, Qt.ItemDataRole.EditRole)
        k_item.setData(FieldOrigin.Provider, Qt.ItemDataRole.UserRole)
        v_item = QStandardItem()
        v_item.setData(v, Qt.ItemDataRole.EditRole)
        dock.view.model().appendRow([k_item, v_item])
    dock.show()
    app.exec()
