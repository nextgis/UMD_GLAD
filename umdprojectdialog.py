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

import os
import ConfigParser

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

from ui_umdprojectdialogbase import Ui_UmdProjectDialog

import umd_utils as utils

class UmdProjectDialog(QDialog, Ui_UmdProjectDialog):
  def __init__(self, plugin):
    QDialog.__init__(self)
    self.setupUi(self)

    self.plugin = plugin
    self.iface = plugin.iface

    self.settings = QSettings("NextGIS", "UMD")
    self.gbGeneral.setSettings(self.settings)
    self.gbProjection.setSettings(self.settings)
    self.gbProcessing.setSettings(self.settings)
    self.gbMetrics.setSettings(self.settings)

    self.btnOk = self.buttonBox.button(QDialogButtonBox.Ok)
    self.btnClose = self.buttonBox.button(QDialogButtonBox.Close)

    self.btnSelectProject.clicked.connect(self.__selectDirectory)
    self.btnSelectData.clicked.connect(self.__selectDirectory)

    self.manageGui()

  def manageGui(self):
    # TODO:
    #  - load metrics from file (seems not necessary?)
    #  - load projections from file (need projections file!)

    projDir = unicode(self.settings.value("lastProjectDir", ".").toString())
    if os.path.exists(os.path.join(projDir, "settings.ini")):
        self.leProjectDir.setText(projDir)
        self.leProjectData.setText(self.settings.value("lastDataDir", ".").toString())

        cfg = ConfigParser.SafeConfigParser()
        cfg.read(os.path.join(projDir, "settings.ini"))
        self.leProjectName.setText(cfg.get("General", "projectName"))
        self.spnTilesThreads.setValue(cfg.getint("General", "threads"))
        self.spnTreesThreads.setValue(cfg.getint("General", "treethreads"))
        self.spnUlx.setValue(cfg.getint("General", "ulxgrid"))
        self.spnUly.setValue(cfg.getint("General", "ulygrid"))
        self.spnTileSide.setValue(cfg.getint("General", "tileside"))
        self.spnTileBuffer.setValue(cfg.getint("General", "tilebuffer"))
        self.spnPixelSize.setValue(cfg.getint("General", "pixelsize"))

        QgsProject.instance().read(os.path.join(projDir, unicode(self.leProjectName.text())))

  def reject(self):
    QDialog.reject(self)

  def accept(self):
    if self.leProjectName.text().isEmpty():
      QMessageBox.warning(self,
                          self.tr("No title"),
                          self.tr("Project title is not set. Please enter valid project title and try again.")
                         )
      return

    if self.leProjectDir.text().isEmpty():
      QMessageBox.warning(self,
                          self.tr("No project directory"),
                          self.tr("Project directory is not set. Please enter valid project directory and try again.")
                         )
      return

    if self.leProjectData.text().isEmpty():
      QMessageBox.warning(self,
                          self.tr("No project data"),
                          self.tr("Project data path is not set. Please enter valid path to project data and try again.")
                         )
      return

    cfg = ConfigParser.SafeConfigParser()
    cfgPath = os.path.join(unicode(self.leProjectDir.text()), "settings.ini")

    if QFile(self.leProjectDir.text() + "/settings.ini").exists():
      res = QMessageBox.warning(self,
                                self.tr("Settings exists"),
                                self.tr("This directory already contains project settings file. Do you want to change it?"),
                                QMessageBox.Yes | QMessageBox.No
                               )

      if res == QMessageBox.No:
        return

      # read existing file and update it accordingly
      cfg.read(cfgPath)

    self.__writeConfigFile(cfg, cfgPath)

    # TODO: don't create shapes if existing project opened
    self.createShapes()

    QgsProject.instance().title(self.leProjectName.text())
    QgsProject.instance().setFileName(QString("%1/%2.qgs").arg(self.leProjectDir.text()).arg(self.leProjectName.text()))
    QgsProject.instance().write()

    QDialog.accept(self)

  def createShapes(self):
    symbol = QgsSymbolV2.defaultSymbol(QGis.Polygon)
    symbol.setColor(Qt.red)
    renderer = QgsSingleSymbolRendererV2(symbol)
    fPath = QFileInfo(self.leProjectDir.text() + "/target.shp").absoluteFilePath()
    utils.createPolygonShapeFile(fPath, "")
    layer = QgsVectorLayer(fPath, "target", "ogr")
    layer.setRendererV2(renderer)
    QgsMapLayerRegistry.instance().addMapLayers([layer])

    symbol = QgsSymbolV2.defaultSymbol(QGis.Polygon)
    symbol.setColor(Qt.blue)
    renderer = QgsSingleSymbolRendererV2(symbol)
    fPath = QFileInfo(self.leProjectDir.text() + "/background.shp").absoluteFilePath()
    utils.createPolygonShapeFile(fPath, "")
    layer = QgsVectorLayer(fPath, "background", "ogr")
    layer.setRendererV2(renderer)
    QgsMapLayerRegistry.instance().addMapLayers([layer])

  def __selectDirectory(self):
    senderName = self.sender().objectName()

    if senderName == "btnSelectProject":
      lastDirectory = self.settings.value("lastProjectDir", ".").toString()
    else:
      lastDirectory = self.settings.value("lastDataDir", ".").toString()

    outPath = QFileDialog.getExistingDirectory(self,
                                               self.tr("Select directory"),
                                               lastDirectory,
                                               QFileDialog.ShowDirsOnly
                                              )
    if outPath.isEmpty():
      return

    if senderName == "btnSelectProject":
      self.leProjectDir.setText(outPath)
      self.settings.setValue("lastProjectDir", QDir(outPath).absolutePath())
    else:
      self.leProjectData.setText(outPath)
      self.settings.setValue("lastDataDir", QDir(outPath).absolutePath())

  def __writeConfigFile(self, cfg, filePath):
      if not cfg.has_section("General"):
        cfg.add_section("General")

      cfg.set("General", "projectName", unicode(self.leProjectName.text()))
      cfg.set("General", "threads", unicode(self.spnTilesThreads.value()))
      cfg.set("General", "treethreads", unicode(self.spnTreesThreads.value()))
      cfg.set("General", "region", unicode(""))
      cfg.set("General", "ulxgrid", unicode(self.spnUlx.value()))
      cfg.set("General", "ulygrid", unicode(self.spnUly.value()))
      cfg.set("General", "prolong", unicode(""))
      cfg.set("General", "tileside", unicode(self.spnTileSide.value()))
      cfg.set("General", "tilebuffer", unicode(self.spnTileBuffer.value()))
      cfg.set("General", "pixelsize", unicode(self.spnPixelSize.value()))

      with open(filePath, 'wb') as f:
        cfg.write(f)
