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
from .compat_type import CompatType
if Qgis.QGIS_VERSION_INT >= 33600:
    FeatureRequestFlag = Qgis.FeatureRequestFlag
else:
    FeatureRequestFlag = QgsFeatureRequest.Flag


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
        self.dock = AttributeValueDock(self.iface.mainWindow())
        self.dock.setWindowTitle(self.name)
        self.dock.setObjectName(self.__class__.__name__.replace('Panel', ''))
        self.restore_dock_state()

        self.model = self.dock.view.model()
        self.model.itemChanged.connect(self.slot_itemChanged)
        self.dock.view.set_editable(False)

        self.current_layer = None
        self.dock.visibilityChanged.connect(self.slot_visibilityChanged)
        self.slot_visibilityChanged(is_user_visible(self.dock))

    def unload(self):
        self.slot_visibilityChanged(False)  # disconnect signals
        self.dock.visibilityChanged.disconnect(self.slot_visibilityChanged)
        self.save_dock_state()
        QgsApplication.removeTranslator(self.translator)

    def slot_visibilityChanged(self, visible):
        if visible:
            self.iface.currentLayerChanged.connect(self.slot_currentLayerChanged)
            self.slot_currentLayerChanged(self.iface.activeLayer())
        else:
            self.disconnect_attributeValueChanged()
            self.disconnect_selectionChanged()
            self.disconnect_editingStateChanged()
            self.disconnect_currentLayerChanged()

    def slot_currentLayerChanged(self, layer):
        self.clear_model()
        self.disconnect_attributeValueChanged()
        self.disconnect_selectionChanged()
        self.disconnect_editingStateChanged()
        self.current_layer = layer if isinstance(layer, QgsVectorLayer) else None
        try:
            self.current_layer.editingStarted.connect(self.slot_editingStateChanged)
            self.current_layer.editingStopped.connect(self.slot_editingStateChanged)
            self.slot_editingStateChanged()

            self.dock.view.is_legacy_format = bool(
                    self.current_layer.dataProvider().storageType() in (
                    'ESRI Shapefile', 'MapInfo File'))
            self.dock.view.encoding = self.current_layer.dataProvider().encoding()

            self.current_layer.selectionChanged.connect(self.slot_selectionChanged)
            self.current_layer.updatedFields.connect(self.slot_selectionChanged)
            self.slot_selectionChanged()

            self.timer = QTimer()
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(self.slot_timeout)
            self.current_layer.attributeValueChanged.connect(self.slot_attributeValueChanged)
            self.current_layer.featureDeleted.connect(self.slot_attributeValueChanged)

        except AttributeError:
            pass
        except Exception as e:
            debug_message(self.__class__.__name__,
                    f'slot_currentLayerChanged: {type(e)} {e}')

    def disconnect_currentLayerChanged(self):
        try:
            self.iface.currentLayerChanged.disconnect(self.slot_currentLayerChanged)
        except TypeError:
            pass
        except Exception as e:
            debug_message(self.__class__.__name__,
                    f'disconnect_currentLayerChanged: {type(e)} {e}')

    def slot_editingStateChanged(self):
        self.dock.view.set_editable(self.current_layer.isEditable())

    def disconnect_editingStateChanged(self):
        try:
            self.current_layer.editingStarted.disconnect(self.slot_editingStateChanged)
            self.current_layer.editingStopped.disconnect(self.slot_editingStateChanged)
        except (AttributeError, RuntimeError, TypeError):
            pass
        except Exception as e:
            debug_message(self.__class__.__name__,
                    f'disconnect_editingStateChanged: {type(e)} {e}')

    def slot_selectionChanged(self):
        self.clear_model()
        try:
            n_feats = self.current_layer.selectedFeatureCount()
        except Exception as e:
            debug_message(self.__class__.__name__,
                    f'slot_selectionChanged: {type(e)} {e}')
            return
        fields = self.current_layer.fields()
        for idx in fields.allAttributesList():
            field = fields.at(idx)
            field_name = field.name()

            key_item = QStandardItem()
            key_item.setData(field, Qt.ItemDataRole.EditRole)
            key_item.setData(fields.fieldOrigin(idx), Qt.ItemDataRole.UserRole)

            if n_feats:
                if ( field.type() == CompatType.QVariantMap or
                    field.typeName().endswith('List') ):
                    conv = lambda x: str(x)
                elif field.type() == CompatType.QByteArray:
                    conv = lambda x: NULL if x == None else True
                else:
                    conv = lambda x: NULL if x == None else x
                req = (QgsFeatureRequest()
                        .setSubsetOfAttributes([idx])
                        .setFlags(FeatureRequestFlag.NoGeometry)
                )
                values = {conv(feat.attribute(field_name))
                        for feat in self.current_layer.getSelectedFeatures(req)}
                value_item = QStandardItem()
                value_item.setData(values, Qt.ItemDataRole.EditRole)
            else:
                s = field.displayType(showConstraints=True)
                if 'NOT NULL' not in s:
                    s = s.replace(' NULL', '')
                values = (s, )
                value_item = QStandardItem()
                value_item.setData(values, Qt.ItemDataRole.DisplayRole)
                value_item.setEnabled(False)

            self.model.appendRow([key_item, value_item])

    def disconnect_selectionChanged(self):
        try:
            self.current_layer.selectionChanged.disconnect(self.slot_selectionChanged)
            self.current_layer.updatedFields.disconnect(self.slot_selectionChanged)
        except (AttributeError, RuntimeError, TypeError):
            # AttributeError: 'Qgs***Layer' object has no attribute 'selectionChanged'
            # AttributeError: 'NoneType' object has no attribute 'selectionChanged'
            # RuntimeError: wrapped C/C++ object of type QgsVectorLayer has been deleted
            # TypeError: 'method' object is not connected
            pass
        except Exception as e:
            debug_message(self.__class__.__name__,
                    f'disconnect_selectionChanged: {type(e)} {e}')

    def slot_attributeValueChanged(self):
        self.timer.start(0)

    def slot_timeout(self):
        self.slot_selectionChanged()

    def disconnect_attributeValueChanged(self):
        try:
            self.current_layer.attributeValueChanged.disconnect(self.slot_attributeValueChanged)
            self.current_layer.featureDeleted.disconnect(self.slot_attributeValueChanged)
        except (AttributeError, RuntimeError, TypeError):
            pass
        except Exception as e:
            debug_message(self.__class__.__name__,
                    f'disconnect_attributeValueChanged: {type(e)} {e}')

    def slot_itemChanged(self, item):
        try:
            assert self.current_layer.isEditable()
        except AssertionError as e:
            debug_message(self.__class__.__name__,
                    f'slot_itemChanged: {type(e)} {e}')
            return
        field_index = item.row()
        value = item.data(Qt.ItemDataRole.EditRole)[0]
        self.current_layer.beginEditCommand(self.tr('Attribute value changed'))
        res = True
        for fid in self.current_layer.selectedFeatureIds():
            res &= self.current_layer.changeAttributeValue(
                    fid, field_index, value)
        if not res:
            debug_message(self.__class__.__name__,
                    'slot_itemChanged: changeAttributeValue failed')
        self.current_layer.endEditCommand()

    def clear_model(self):
        self.model.removeRows(0, self.model.rowCount())

    def restore_dock_state(self):
        mainwin = self.iface.mainWindow()
        for dock in mainwin.findChildren(QDockWidget, self.dock.objectName()):
            mainwin.removeDockWidget(dock)

        st = QgsSettings()
        st.beginGroup(self.__class__.__name__)
        try:
            area = st.value('dockArea',
                    Qt.DockWidgetArea.RightDockWidgetArea, Qt.DockWidgetArea)
        except TypeError:
            area = Qt.DockWidgetArea.RightDockWidgetArea
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


def debug_message(title, text):
    QgsMessageLog.logMessage('%s: %s' % (title, text),
            'Debug', Qgis.MessageLevel.Info)


def classFactory(iface):
    return AttributeValuePanel(iface)
