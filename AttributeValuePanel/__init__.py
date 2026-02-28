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
if Qgis.QGIS_VERSION_INT >= 33800:
    FieldOrigin = Qgis.FieldOrigin
else:
    FieldOrigin = QgsFields.FieldOrigin
    FieldOrigin.Unknown = FieldOrigin.OriginUnknown  # for read-only flag


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

        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self.refresh_model)

        self.current_layer = None
        self.dock.visibilityChanged.connect(self.slot_visibilityChanged)
        self.slot_visibilityChanged(is_user_visible(self.dock))

    def unload(self):
        self.slot_visibilityChanged(False)  # disconnect signals
        self.dock.visibilityChanged.disconnect(self.slot_visibilityChanged)
        self.save_dock_state()
        QgsApplication.removeTranslator(self.translator)

    def slot_visibilityChanged(self, visible):
        self.disconnect_layer_signals()
        try:
            self.iface.currentLayerChanged.disconnect(self.slot_currentLayerChanged)
        except TypeError:
            pass
        if visible:
            self.iface.currentLayerChanged.connect(self.slot_currentLayerChanged)
            self.slot_currentLayerChanged(self.iface.activeLayer())

    def slot_currentLayerChanged(self, layer):
        self.disconnect_layer_signals()
        if isinstance(layer, QgsVectorLayer):
            self.current_layer = layer
        else:
            self.current_layer = None
            self.clear_model()
            return

        self.model.is_legacy_format = bool(
                self.current_layer.dataProvider().storageType() in (
                'ESRI Shapefile', 'MapInfo File'))

        self.current_layer.editingStarted.connect(self.on_editing_state_changed)
        self.current_layer.editingStopped.connect(self.on_editing_state_changed)
        self.on_editing_state_changed()

        self._updating = False
        self.current_layer.selectionChanged.connect(self.on_refresh_model)
        self.current_layer.updatedFields.connect(self.on_refresh_model)  # encoding change
        self.current_layer.attributeValueChanged.connect(self.on_refresh_model)
        self.current_layer.featureDeleted.connect(self.on_refresh_model)

    def on_editing_state_changed(self):
        self.dock.view.set_editable(self.current_layer.isEditable())
        self.refresh_model()

    def on_refresh_model(self):
        if not self._updating:
            self.debounce_timer.start(0)

    def refresh_model(self):
        self.clear_model()
        self.model.encoding = self.current_layer.dataProvider().encoding()
        n_feats = self.current_layer.selectedFeatureCount()
        dp = self.current_layer.dataProvider()
        pks = dp.pkAttributeIndexes()
        fields = self.current_layer.fields()
        for idx in fields.allAttributesList():
            field = fields.at(idx)
            foi = fields.fieldOriginIndex(idx)

            is_autogen = False
            if foi in pks:
                if dp.name() == 'ogr':
                    ctx = 'QgsOgrProvider'
                elif dp.name() == 'spatialite':
                    ctx = 'QgsSpatiaLiteProvider'
                else:
                    ctx = None
                s_autogen = QgsApplication.translate(ctx, 'Autogenerate')
                if dp.defaultValueClause(foi) == s_autogen:
                    is_autogen = True

            key_item = QStandardItem()
            key_item.setData(field, Qt.ItemDataRole.EditRole)
            key_item.setData(fields.fieldOrigin(idx)
                             if not is_autogen else
                             FieldOrigin.Unknown,
                             Qt.ItemDataRole.UserRole)
            if n_feats:
                if ( field.type() == CompatType.QVariantMap or
                    field.typeName().endswith('List') ):
                    conv = lambda x: str(x)
                elif field.type() == CompatType.QByteArray:
                    conv = lambda x: NULL if x == None else True
                elif is_autogen:
                    conv = lambda x: (NULL if x == None else
                            x.defaultValueClause() if isinstance(x, QgsUnsetAttributeValue) else
                            x)
                else:
                    conv = lambda x: NULL if x == None else x
                req = (QgsFeatureRequest()
                        .setSubsetOfAttributes([idx])
                        .setFlags(FeatureRequestFlag.NoGeometry)
                )
                values = {conv(feat.attribute(idx))
                        for feat in self.current_layer.getSelectedFeatures(req)}
                value_item = QStandardItem()
                value_item.setData(values, Qt.ItemDataRole.EditRole)
            else:
                s = field.displayType(showConstraints=True)
                if foi in pks:
                    s = s.replace(' N', ' PK N', 1)
                if ('NOT NULL' not in s) and (' NULL' in s):
                    s = s.replace(' NULL', '')
                values = (s, )
                value_item = QStandardItem()
                value_item.setData(values, Qt.ItemDataRole.DisplayRole)
                value_item.setEnabled(False)

            self.model.appendRow([key_item, value_item])

    def clear_model(self):
        self.model.removeRows(0, self.model.rowCount())

    def slot_itemChanged(self, item):
        # not called by clear_model
        if not self.current_layer.isEditable():
            raise RuntimeError
        value = item.data(Qt.ItemDataRole.EditRole)[0]
        self._updating = True
        self.current_layer.beginEditCommand(self.tr('Attribute value changed'))
        for fid in self.current_layer.selectedFeatureIds():
            res = self.current_layer.changeAttributeValue(fid, item.row(), value)
            if not res:
                self.iface.messageBar().pushCritical(
                        self.__class__.__name__,
                        self.tr('Failed to change attribute value.'))
                self.current_layer.destroyEditCommand()
                break
        else:
            self.current_layer.endEditCommand()
        self._updating = False

    def disconnect_layer_signals(self):
        try:
            self.current_layer.editingStarted.disconnect(self.on_editing_state_changed)
            self.current_layer.editingStopped.disconnect(self.on_editing_state_changed)
            self.current_layer.selectionChanged.disconnect(self.on_refresh_model)
            self.current_layer.updatedFields.disconnect(self.on_refresh_model)
            self.current_layer.attributeValueChanged.disconnect(self.on_refresh_model)
            self.current_layer.featureDeleted.disconnect(self.on_refresh_model)
        except (AttributeError, RuntimeError, TypeError):
            pass

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


def classFactory(iface):
    return AttributeValuePanel(iface)
