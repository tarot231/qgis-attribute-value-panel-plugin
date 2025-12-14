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

from qgis.PyQt.QtCore import Qt, QVariant, QLocale
from qgis.PyQt.QtGui import QPalette, QStandardItemModel
from qgis.PyQt.QtWidgets import *
from qgis.gui import QgsFilterLineEdit


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

        self.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)

    class FieldItemDelegate(QStyledItemDelegate):
        def createEditor(self, parent, option, index):
            return None

    class ValueItemDelegate(QStyledItemDelegate):
        def displayText(self, value, locale):
            return ', '.join(map(str,
                    set(x if x is not None else 'NULL' for x in value)))

        def initStyleOption(self, option, index):
            super().initStyleOption(option, index)
            data = index.data()
            if None in data or len(set(data)) > 1:
                option.font.setItalic(True)
                option.palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.gray)

        def createEditor(self, parent, option, index):
            editor = QgsFilterLineEdit(parent)
            editor.setShowClearButton(True)
            return editor

        def setEditorData(self, editor, index):
            editor.setText(self.displayText(index.data(), QLocale()))

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
                 ('k4', [4, QVariant(), 5, 4])]:
        k_item = QStandardItem(k)
        v_item = QStandardItem()
        v_item.setData(v, Qt.ItemDataRole.DisplayRole)
        dock.view.model().appendRow([k_item, v_item])
    dock.show()
    app.exec()
