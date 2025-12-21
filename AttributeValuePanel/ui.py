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

from qgis.PyQt.QtCore import Qt, QVariant, QDate, QTime, QDateTime
from qgis.PyQt.QtGui import QPalette, QStandardItemModel
from qgis.PyQt.QtWidgets import *
from qgis.core import QgsDateTimeFieldFormatter
from qgis.gui import QgsFilterLineEdit


def to_str(x):
    if isinstance(x, QDate):
        return x.toString(QgsDateTimeFieldFormatter.DATE_FORMAT)
    elif isinstance(x, QTime):
        return x.toString(QgsDateTimeFieldFormatter.TIME_FORMAT)
    elif isinstance(x, QDateTime):
        return x.toString(QgsDateTimeFieldFormatter.DATETIME_FORMAT)
    try:
        return str(x)
    except Exception as e:
        # DEBUG
        from qgis.core import QgsMessageLog
        QgsMessageLog.logMessage(f'ui.py: '
                f'to_str: {type(e)} {e}', 'Debug', level=Qgis.Info)
        return '<%s>' % x.__class__.__name__


class AttributeValueModel(QStandardItemModel):
    def __init__(self):
        super().__init__()
        self.setHorizontalHeaderLabels([self.tr('Field'), self.tr('Value')])


class AttributeValueView(QTreeView):
    def __init__(self):
        super().__init__()
        self.setAlternatingRowColors(True)
        self.setRootIsDecorated(False)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.header().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        # https://stackoverflow.com/q/27248148
        self.setItemDelegateForColumn(0, self.FieldItemDelegate(self))
        self.setItemDelegateForColumn(1, self.ValueItemDelegate(self))

    def set_editable(self, editable):
        self.setEditTriggers(
                QTreeView.EditTrigger.AllEditTriggers
                if editable else
                QTreeView.EditTrigger.NoEditTriggers)

    class FieldItemDelegate(QStyledItemDelegate):
        def createEditor(self, parent, option, index):
            return None

    class ValueItemDelegate(QStyledItemDelegate):
        def displayText(self, value, locale=None):
            return ', '.join(set(
                    to_str(x) if x is not None else 'NULL' for x in value))

        def initStyleOption(self, option, index):
            super().initStyleOption(option, index)
            value = index.data()
            if None in value or any(x != value[0] for x in value):
                option.font.setItalic(True)
                option.palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.gray)

        def createEditor(self, parent, option, index):
            editor = QgsFilterLineEdit(parent)
            editor.setShowClearButton(True)
            return editor

        def setEditorData(self, editor, index):
            editor.setText(self.displayText(index.data()))

        def setModelData(self, editor, model, index):
            model.setData(index, [editor.text()])


class AttributeValueDock(QDockWidget):
    def __init__(self):
        super().__init__()
        self.view = AttributeValueView()
        self.view.setModel(AttributeValueModel())
        self.setWidget(self.view)


if __name__ == '__main__':
    from qgis.PyQt.QtGui import QStandardItem
    app = QApplication([])
    dock = AttributeValueDock()
    for k, v in [('k1', [1]),
                 ('k2', ['2', '3']),
                 ('k3', [QVariant()]),
                 ('k4', [4, QVariant(), 5, 4]),
                 ('k5', [QDateTime.currentDateTime()])]:
        k_item = QStandardItem(k)
        v_item = QStandardItem()
        v_item.setData(v, Qt.ItemDataRole.DisplayRole)
        dock.view.model().appendRow([k_item, v_item])
    dock.show()
    app.exec()
