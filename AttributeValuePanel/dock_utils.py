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

from collections import defaultdict, deque
from qgis.PyQt.QtWidgets import *


def restore_order(parts):
    # collect all nodes
    nodes = {x for seq in parts for x in seq}

    # build graph
    graph = defaultdict(set)
    indeg = {x: 0 for x in nodes}

    for seq in parts:
        for a, b in zip(seq, seq[1:]):
            if b not in graph[a]:
                graph[a].add(b)
                indeg[b] += 1

    # topological sort
    q = deque([x for x in nodes if indeg[x] == 0])
    order = []

    while q:
        x = q.popleft()
        order.append(x)
        for nxt in graph[x]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                q.append(nxt)

    return order


def get_all_tab_titles(target_dock):
    # TODO: Does not handle cases where multiple docks have the same title.
    title = target_dock.windowTitle()
    mainwin = target_dock.parent()
    for tabbar in mainwin.findChildren(QTabBar):
        titles = [tabbar.tabText(i) for i in range(tabbar.count())]
        if title in titles:
            return tuple(titles)
    return None


def get_all_tabified(target_dock):
    mainwin = target_dock.parent()
    tabified = mainwin.tabifiedDockWidgets(target_dock)
    if not tabified:
        if target_dock.isVisible():
            return [target_dock]
        else:
            return []
    parts = [tabified]
    for dock in tabified:
        if not dock.isVisible():
            continue
        parts.append(mainwin.tabifiedDockWidgets(dock))

    if len(parts) == 2:
        titles = get_all_tab_titles(target_dock)
        if len(set(titles)) > 1:
            docks = {x for sub in parts for x in sub}
            kv = {w.windowTitle(): w for w in docks}
            parts.append([kv[x] for x in titles])

    return restore_order(parts)


def is_user_visible(w):
    # https://stackoverflow.com/q/22230042
    return bool(w.visibleRegion())
