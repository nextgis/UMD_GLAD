# -*- coding: utf-8 -*-

#******************************************************************************
#
# UMD GLAD classifier
# ---------------------------------------------------------
# Landsat time-sequential metric visualization and classification
#
# Copyright (C) 2013 NextGIS (info@nextgis.org)
#
# This source is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 2 of the License, or (at your option)
# any later version.
#
# This code is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# A copy of the GNU General Public License is available on the World Wide Web
# at <http://www.gnu.org/licenses/>. You can also obtain it by writing
# to the Free Software Foundation, 51 Franklin Street, Suite 500 Boston,
# MA 02110-1335 USA.
#
#******************************************************************************

from PyQt4.QtCore import *

from qgis.core import *

def createPolygonShapeFile(filePath, crs):
  fields = QgsFields()
  fields.append(QgsField("id", QVariant.Int))

  writer = QgsVectorFileWriter(filePath, "utf-8", fields, QGis.WKBPolygon, crs)
  del writer

def getVectorLayerByName(layerName):
  layerMap = QgsMapLayerRegistry.instance().mapLayers()
  for name, layer in layerMap.iteritems():
    if layer.type() == QgsMapLayer.VectorLayer and layer.name() == layerName:
      if layer.isValid():
        return layer
      else:
        return None

def getLayerBySource(layerSource):
  layerMap = QgsMapLayerRegistry.instance().mapLayers()
  for name, layer in layerMap.iteritems():
    if layer.source() == layerSource:
      if layer.isValid():
        return layer
      else:
        return None

def getRasterLayerByName(layerName):
  layerMap = QgsMapLayerRegistry.instance().mapLayers()
  for name, layer in layerMap.iteritems():
    if layer.type() == QgsMapLayer.RasterLayer and layer.name() == layerName:
      if layer.isValid():
        return layer
      else:
        return None
