# -*- coding: utf-8 -*-

#******************************************************************************
#
# UMD
# ---------------------------------------------------------
# Classification for UMD
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
from PyQt4.QtGui import *

from qgis.core import *
from qgis.gui import *

from ui_umdprojectdialogbase import Ui_Dialog

import umd_utils as utils

class UmdProjectDialog(QDialog, Ui_Dialog):
  def __init__(self, plugin):
    QDialog.__init__(self)
    self.setupUi(self)

    # plugin is a pointer to UMD plugin instance
    self.plugin = plugin
    self.iface = plugin.iface

    self.btnOk = self.buttonBox.button(QDialogButtonBox.Ok)
    self.btnClose = self.buttonBox.button(QDialogButtonBox.Close)

    self.btnSelectProject.clicked.connect(self.__selectDirectory)
    self.btnSelectData.clicked.connect(self.__selectDirectory)

    self.manageGui()

  def manageGui(self):
    pass

  def reject(self):
    QDialog.reject(self)

  def accept(self):
    # TODO:
    # create project settings file


    # create shapefiles
    self.createShapes()

    # save project
    QgsProject.instance().title(self.leProjectName.text())
    QgsProject.instance().setFileName(QString("%1/%2.qgs").arg(self.leProjectDir.text()).arg(self.leProjectName.text()))
    QgsProject.instance().write()

    # close dialog if all ok
    QDialog.accept(self)

  def createShapes(self):
    symbol = QgsSymbolV2.defaultSymbol(QGis.Polygon)
    symbol.setColor(Qt.red)
    renderer = QgsSingleSymbolRendererV2(symbol)
    fPath = QFileInfo(self.leProjectDir.text() + "/presence.shp").absoluteFilePath()
    utils.createPolygonShapeFile(fPath, "")
    layer = QgsVectorLayer(fPath, "presense", "ogr")
    layer.setRendererV2(renderer)
    QgsMapLayerRegistry.instance().addMapLayers([layer])

    symbol = QgsSymbolV2.defaultSymbol(QGis.Polygon)
    symbol.setColor(Qt.blue)
    renderer = QgsSingleSymbolRendererV2(symbol)
    fPath = QFileInfo(self.leProjectDir.text() + "/absence.shp").absoluteFilePath()
    utils.createPolygonShapeFile(fPath, "")
    layer = QgsVectorLayer(fPath, "absense", "ogr")
    layer.setRendererV2(renderer)
    QgsMapLayerRegistry.instance().addMapLayers([layer])

  def __selectDirectory(self):
    senderName = self.sender().objectName()

    settings = QSettings("NextGIS", "UMD")
    if senderName == "btnSelectProject":
        lastDirectory = settings.value("lastProjectDir", ".").toString()
    else:
        lastDirectory = settings.value("lastDataDir", ".").toString()

    outPath = QFileDialog.getExistingDirectory(self,
                                               self.tr("Select directory"),
                                               lastDirectory,
                                               QFileDialog.ShowDirsOnly
                                              )
    if outPath.isEmpty():
      return

    if senderName == "btnSelectProject":
      self.leProjectDir.setText(outPath)
      settings.setValue("lastProjectDir", QFileInfo(outPath).absoluteDir().absolutePath())
    else:
      self.leProjectData.setText(outPath)
      settings.setValue("lastDataDir", QFileInfo(outPath).absoluteDir().absolutePath())
