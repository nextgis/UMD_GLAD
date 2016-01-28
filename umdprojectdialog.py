# -*- coding: utf-8 -*-

#******************************************************************************
#
# UMD GLAD classifier
# ---------------------------------------------------------
# Landsat time-sequential metric visualization and classification
#
# Copyright (C) 2013-2016 NextGIS (info@nextgis.com)
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
import shutil
import ConfigParser

from PyQt4 import uic
from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ui/umdprojectdialogbase.ui'))

import umd_utils as utils

class UmdProjectDialog(QDialog, FORM_CLASS):
  def __init__(self, plugin, parent=None):
    super(UmdProjectDialog, self).__init__(parent)
    self.setupUi(self)

    self.plugin = plugin
    self.iface = plugin.iface

    self.settings = QSettings("NextGIS", "UMD")
    self.gbGeneral.setSettings(self.settings)
    self.gbProjection.setSettings(self.settings)
    self.gbProcessing.setSettings(self.settings)

    self.btnOk = self.buttonBox.button(QDialogButtonBox.Ok)
    self.btnClose = self.buttonBox.button(QDialogButtonBox.Close)

    self.btnSelectProject.clicked.connect(self.__selectDirectory)
    self.btnSelectData.clicked.connect(self.__selectDirectory)
    self.btnSelectMingw.clicked.connect(self.__selectCompiler)

    self.manageGui()

  def manageGui(self):
    projDir = unicode(self.settings.value("lastProjectDir", "."))
    if os.path.exists(os.path.join(projDir, "settings.ini")):
      self.leProjectDir.setText(projDir)
      self.leProjectData.setText(self.settings.value("lastDataDir", "."))

      defaults = {"projectname":"",
                  "metricspath":"",
                  "projpath":"",
                  "cpp":"C:\NextGIS_QGIS\MinGW\bin\x86_64-w64-mingw32-g++.exe",
                  "threads":"1",
                  "treethreads":"7",
                  "memsize":"900000000",
                  "sampling":"20",
                  "maxtrees":"7",
                  "ulxgrid":"-4560000",
                  "ulygrid":"2400000",
                  "tileside":"2000",
                  "tilebuffer":"2",
                  "pixelsize":"30"
                 }

      cfg = ConfigParser.SafeConfigParser(defaults)
      cfg.read(os.path.join(projDir, "settings.ini"))
      self.leProjectName.setText(cfg.get("general", "projectname"))
      self.leProjectData.setText(cfg.get("general", "metricspath"))
      self.leProjectDir.setText(cfg.get("general", "projpath"))
      self.leMinGW.setText(cfg.get("general", "cpp"))
      self.spnTilesThreads.setValue(cfg.getint("general", "threads"))
      self.spnTreesThreads.setValue(cfg.getint("general", "treethreads"))
      self.spnMemory.setValue(cfg.getint("general", "memsize"))
      self.spnSampling.setValue(cfg.getint("general", "sampling"))
      self.spnBaggedTrees.setValue(cfg.getint("general", "maxtrees"))
      self.spnUlx.setValue(cfg.getint("general", "ulxgrid"))
      self.spnUly.setValue(cfg.getint("general", "ulygrid"))
      self.spnTileSide.setValue(cfg.getint("general", "tileside"))
      self.spnTileBuffer.setValue(cfg.getint("general", "tilebuffer"))
      self.spnPixelSize.setValue(cfg.getint("general", "pixelsize"))

  def reject(self):
    QDialog.reject(self)

  def accept(self):
    if self.leProjectName.text() == "":
      QMessageBox.warning(self,
                          self.tr("No title"),
                          self.tr("Project title is not set. Please enter valid project title and try again.")
                        )
      return

    if self.leProjectDir.text() == "":
      QMessageBox.warning(self,
                          self.tr("No project directory"),
                          self.tr("Project directory is not set. Please enter valid project directory and try again.")
                        )
      return

    if self.leProjectData.text() == "":
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

    # copy style
    sourceQml = os.path.join(os.path.join("C:/NextGIS_QGIS/UMD", "out.qml"))
    if QFile(sourceQml).exists():
      shutil.copyfile(sourceQml, os.path.join(unicode(self.leProjectDir.text()), "out.qml"))

    # copy other stuff
    tmp = os.path.join(unicode(self.leProjectDir.text()), "config")
    if os.path.exists(tmp):
      shutil.rmtree(tmp)
    shutil.copytree("C:/NextGIS_QGIS/UMD/config", tmp)

    layers = QgsMapLayerRegistry.instance().mapLayers()
    layersFound = False
    for layerName, layer in layers.iteritems():
      if layer.type() == QgsMapLayer.VectorLayer and layer.name() in ["target", "background"]:
        layersFound = True

    # read random tile and get CRS from it
    crs = None
    template = QRegExp("^[0-9]{3}_[0-9]{3}$")
    for root, dirs, files in os.walk(self.leProjectData.text()):
      if not template.exactMatch(root[-7:]):
        continue

      names = ["*.vrt", "*.VRT"]
      vrts = QDir(root).entryList(names, QDir.Files)
      myFile = vrts[0]
      layer = QgsRasterLayer(os.path.join(root, myFile), "tmp")
      if layer.isValid():
        crs = layer.crs()
        break

    if not layersFound:
      self.createShapes(crs)

    # map crs
    self.iface.mapCanvas().mapRenderer().setDestinationCrs(crs)

    QgsProject.instance().title(self.leProjectName.text())
    QgsProject.instance().setFileName(u"%s/%s.qgs" % (self.leProjectDir.text(), self.leProjectName.text()))
    QgsProject.instance().writeEntry("SpatialRefSys", "/ProjectCRSProj4String", crs.toProj4())
    QgsProject.instance().write()

    QDialog.accept(self)

  def createShapes(self, crs):
    symbol = QgsSymbolV2.defaultSymbol(QGis.Polygon)
    symbol.setColor(Qt.blue)
    renderer = QgsSingleSymbolRendererV2(symbol)
    fPath = QFileInfo(self.leProjectDir.text() + "/background.shp").absoluteFilePath()
    utils.createPolygonShapeFile(fPath, crs)
    layer = QgsVectorLayer(fPath, "background", "ogr")
    layer.setRendererV2(renderer)
    QgsMapLayerRegistry.instance().addMapLayers([layer])

    symbol = QgsSymbolV2.defaultSymbol(QGis.Polygon)
    symbol.setColor(Qt.red)
    renderer = QgsSingleSymbolRendererV2(symbol)
    fPath = QFileInfo(self.leProjectDir.text() + "/target.shp").absoluteFilePath()
    utils.createPolygonShapeFile(fPath, crs)
    layer = QgsVectorLayer(fPath, "target", "ogr")
    layer.setRendererV2(renderer)
    QgsMapLayerRegistry.instance().addMapLayers([layer])

  def __selectDirectory(self):
    senderName = self.sender().objectName()

    if senderName == "btnSelectProject":
      lastDirectory = self.settings.value("lastProjectDir", ".")
    else:
      lastDirectory = self.settings.value("lastDataDir", ".")

    outPath = QFileDialog.getExistingDirectory(self,
                                               self.tr("Select directory"),
                                               lastDirectory,
                                               QFileDialog.ShowDirsOnly
                                             )
    if outPath == "":
      return

    if senderName == "btnSelectProject":
      self.leProjectDir.setText(outPath)
      self.settings.setValue("lastProjectDir", QDir(outPath).absolutePath())
    else:
      self.leProjectData.setText(outPath)
      self.settings.setValue("lastDataDir", QDir(outPath).absolutePath())

  def __selectCompiler(self):
    lastDirectory = self.settings.value("lastExeDir", ".")
    fName = QFileDialog.getOpenFileName(self,
                                        self.tr("Select compiler"),
                                        lastDirectory,
                                        self.tr("Executable files (*.exe *.EXE)")
                                       )

    if fName == "":
      return

    self.leMinGW.setText(fName)
    self.settings.setValue("lastExeDir", QFileInfo(fName).absoluteDir().absolutePath())

  def __writeConfigFile(self, cfg, filePath):
    if not cfg.has_section("general"):
      cfg.add_section("general")

    cfg.set("general", "projectName", unicode(self.leProjectName.text()))
    cfg.set("general", "projpath", unicode(QDir.toNativeSeparators(self.leProjectDir.text())))
    cfg.set("general", "metricspath", unicode(QDir.toNativeSeparators(self.leProjectData.text())))
    cfg.set("general", "cpp", unicode(QDir.toNativeSeparators(self.leMinGW.text())))
    cfg.set("general", "threads", unicode(self.spnTilesThreads.value()))
    cfg.set("general", "treethreads", unicode(self.spnTreesThreads.value()))
    cfg.set("general", "memsize", unicode(self.spnMemory.value()))
    cfg.set("general", "sampling", unicode(self.spnSampling.value()))
    cfg.set("general", "maxtrees", unicode(self.spnBaggedTrees.value()))
    cfg.set("general", "ulxgrid", unicode(self.spnUlx.value()))
    cfg.set("general", "ulygrid", unicode(self.spnUly.value()))
    cfg.set("general", "tileside", unicode(self.spnTileSide.value()))
    cfg.set("general", "tilebuffer", unicode(self.spnTileBuffer.value()))
    cfg.set("general", "pixelsize", unicode(self.spnPixelSize.value()))
    cfg.set("general", "Ignore pf flags", u"13,14,15,19,21,22,23,111,112")

    with open(filePath, 'wb') as f:
      cfg.write(f)
