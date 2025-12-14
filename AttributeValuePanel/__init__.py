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

import os
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.core import *
from qgis.gui import *
from .ui import AttributeValueDock
from .dock_utils import get_all_tabified, is_user_visible


class AttributeValuePanel(QObject):
    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.translator = QTranslator()
        if self.translator.load(QgsApplication.locale(),
                os.path.join(os.path.dirname(__file__), 'i18n')):
            QgsApplication.installTranslator(self.translator)

    def initGui(self):
        self.name = self.tr('Attribute Value')
        self.dock = AttributeValueDock()
        self.dock.setWindowTitle(self.name)
        self.dock.setObjectName(self.__class__.__name__.replace('Panel', ''))
        self.model = self.dock.view.model()

        self.current_layer = None
        self.iface.currentLayerChanged.connect(self.slot_currentLayerChanged)
        self.slot_currentLayerChanged(self.iface.activeLayer())

        self.restore_dock_state()

    def restore_dock_state(self):
        mainwin = self.iface.mainWindow()
        for dock in mainwin.findChildren(QDockWidget, self.dock.objectName()):
            mainwin.removeDockWidget(dock)

        st = QgsSettings()
        st.beginGroup(self.__class__.__name__)
        area = st.value('dockArea', Qt.DockWidgetArea.RightDockWidgetArea,
                Qt.DockWidgetArea)
        order = st.value('dockOrder', [], list)
        isVisible = st.value('visible', True, bool)
        isRaised = st.value('raised', True, bool)
        st.endGroup()

        self.iface.addTabifiedDockWidget(area, self.dock, order, isRaised)  # QGIS >= 3.14
        self.dock.setVisible(isVisible)
        tabified = mainwin.tabifiedDockWidgets(self.dock)

        try:
            idx = order.index(self.dock.objectName())
        except ValueError:
            return
        # Remove elements after myself, then re-add them back
        for name in order[idx + 1:]:
            docks = mainwin.findChildren(QDockWidget, name)
            if len(docks) != 1:
                continue
            dock = docks[0]
            if dock in tabified:
                visible = dock.isVisible()
                raised = is_user_visible(dock)
                self.iface.removeDockWidget(dock)
                self.iface.addTabifiedDockWidget(area, dock, order, raised)
                dock.setVisible(visible)

    def save_dock_state(self):
        mainwin = self.iface.mainWindow()
        st = QgsSettings()
        st.remove(self.__class__.__name__)
        st.beginGroup(self.__class__.__name__)
        st.setValue('raised', is_user_visible(self.dock))
        st.setValue('visible', self.dock.isVisible())
        self.dock.setVisible(True)
        st.setValue('dockOrder',
                [x.objectName() for x in get_all_tabified(self.dock)])
        st.setValue('dockArea', mainwin.dockWidgetArea(self.dock))
        st.endGroup()

    def slot_currentLayerChanged(self, layer):
        try:
            if self.current_layer:
                self.current_layer.selectionChanged.disconnect(self.slot_selectionChanged)
        except RuntimeError:
            # RuntimeError: wrapped C/C++ object of type QgsVectorLayer has been deleted
            pass
        self.clear_model()
        self.current_layer = layer if isinstance(layer, QgsVectorLayer) else None
        if self.current_layer:
            try:
                self.current_layer.selectionChanged.connect(self.slot_selectionChanged)
                self.slot_selectionChanged()
            except Exception as e:
                # DEBUG
                QgsMessageLog.logMessage(f'{self.__class__.__name__}: '
                        f'slot_currentLayerChanged: {type(e)} {e}', 'Debug', level=Qgis.Info)
                pass

    def clear_model(self):
        self.model.removeRows(0, self.model.rowCount())

    def slot_selectionChanged(self):
        self.clear_model()
        try:
            features = self.current_layer.selectedFeatures()
        except Exception as e:
            # DEBUG
            QgsMessageLog.logMessage(f'{self.__class__.__name__}: '
                    f'slot_selectionChanged: {type(e)} {e} {self.current_layer}', 'Debug', level=Qgis.Info)
            features = []
        if not features:
            return
        for field in features[0].fields():
            field_name = field.name()
            key_item = QStandardItem(field_name)
            value_item = QStandardItem()
            value_item.setData([f.attribute(field_name) for f in features],
                    Qt.ItemDataRole.DisplayRole)
            self.model.appendRow([key_item, value_item])

    def unload(self):
        self.iface.currentLayerChanged.disconnect(self.slot_currentLayerChanged)
        try:
            self.current_layer.selectionChanged.disconnect(self.slot_selectionChanged)
        except (AttributeError, RuntimeError):
            # AttributeError: 'QgsRasterLayer' object has no attribute 'selectionChanged'
            # AttributeError: 'NoneType' object has no attribute 'selectionChanged'
            # RuntimeError: wrapped C/C++ object of type QgsVectorLayer has been deleted
            pass
        except Exception as e:
            # DEBUG
            QgsMessageLog.logMessage(f'{self.__class__.__name__}: '
                    f'unload: {type(e)} {e}', 'Debug', level=Qgis.Info)
            pass
        self.save_dock_state()


def classFactory(iface):
    return AttributeValuePanel(iface)
