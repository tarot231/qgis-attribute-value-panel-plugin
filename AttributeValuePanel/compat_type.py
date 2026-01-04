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

from qgis.core import Qgis

if Qgis.QGIS_VERSION_INT >= 33800:
    from qgis.PyQt.QtCore import QMetaType
    CompatType = QMetaType.Type
else:
    from qgis.PyQt.QtCore import QVariant
    CompatType = QVariant.Type
    # https://doc.qt.io/qt-6/qvariant-obsolete.html#Type-enum
    CompatType.QString = CompatType.String
    CompatType.QDate = CompatType.Date
    CompatType.QTime = CompatType.Time
    CompatType.QDateTime = CompatType.DateTime
    CompatType.QVariantMap = CompatType.Map
    CompatType.QByteArray = CompatType.ByteArray
