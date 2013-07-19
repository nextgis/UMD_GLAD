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
import pickle

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtXml import *

from qgis.core import *

import classificationthread
import umd_utils as utils

from ui_umdclassificationdialogbase import Ui_Dialog

class UmdClassificationDialog(QDialog, Ui_Dialog):
  def __init__(self, plugin):
    QDialog.__init__(self)
    self.setupUi(self)

    self.plugin = plugin
    self.iface = plugin.iface

    settings = QSettings("NextGIS", "UMD")
    projDir = unicode(settings.value("lastProjectDir", "."))
    cfgPath = os.path.join(projDir, "settings.ini")
    if os.path.exists(cfgPath):
      cfg = ConfigParser.SafeConfigParser()
      cfg.read(cfgPath)

      s = cfg.get("Metrics", "metrics_dict")
      self.metrics = pickle.loads(s)
      self.usedDirs = cfg.get("Metrics", "tiles").split(",")

    self.btnSelectMask.clicked.connect(self.selectDir)

    self.btnOk = self.buttonBox.button(QDialogButtonBox.Ok)
    self.btnClose = self.buttonBox.button(QDialogButtonBox.Close)

    self.workThread = None

  def reject(self):
    QDialog.reject(self)

  def accept(self):
    layers = QgsMapLayerRegistry.instance().mapLayers()
    layersFound = False
    for layerName, layer in layers.iteritems():
      if layer.type() == QgsMapLayer.VectorLayer and layer.name() in ["target", "background"]:
        layersFound = True

    if not layersFound:
      QMessageBox.warning(self,
                          self.tr("Missed layer"),
                          self.tr("Target or background layer not found. Please add them and try again.")
                         )
      return

    self.outputFile = None
    settings = QSettings("NextGIS", "UMD")
    projDir = unicode(settings.value("lastProjectDir", "."))
    cfgPath = os.path.join(projDir, "settings.ini")
    if os.path.exists(cfgPath):
      cfg = ConfigParser.SafeConfigParser()
      cfg.read(cfgPath)

      self.outputFile = os.path.join(cfg.get("General", "metricspath"), "out.vrt")

      if not cfg.has_section("Outputs"):
        cfg.add_section("Outputs")

      cfg.set("Outputs", "maskFile", self.leMaskFile.text())
      cfg.set("Outputs", "resultFile", outputFile)

      if self.rbTarget.isChecked():
        cfg.set("Mask", "maskclass", 1)
      else:
        cfg.set("Mask", "maskclass", 2)

      with open(cfgPath, 'wb') as f:
        cfg.write(f)

    self.workThread = classificationthread.ClassificationThread(self.metrics,
                                                                self.usedDirs,
                                                                self.outputFile
                                                               )

    self.workThread.rangeChanged.connect(self.setProgressRange)
    self.workThread.updateProgress.connect(self.updateProgress)
    self.workThread.logMessage.connect(self.updateMessages)
    self.workThread.processFinished.connect(self.processFinished)
    self.workThread.processInterrupted.connect(self.processInterrupted)

    self.btnOk.setEnabled(False)
    self.btnClose.setText(self.tr("Cancel"))
    self.buttonBox.rejected.disconnect(self.reject)
    self.btnClose.clicked.connect(self.stopProcessing)

    # if classification result already there — unload it
    layer = utils.getLayerBySource(self.leOutputFile.text())
    if layer is not None:
      QgsMapLayerRegistry.instance().removeMapLayer(layer.id())

    self.workThread.start()

  def setProgressRange(self, message, maxValue):
    self.progressBar.setFormat(message)
    self.progressBar.setRange(0, maxValue)

  def updateProgress(self):
    self.progressBar.setValue(self.progressBar.value() + 1)

  def updateMessages(self, message):
    self.edLog.appendPlainText(message)

  def processFinished(self):
    self.stopProcessing()
    self.restoreGui()

    if self.chkAddOutput.isChecked():
      newLayer = QgsRasterLayer(self.outputFile, QFileInfo(self.outputFile).baseName())

      if newLayer.isValid():
        QgsMapLayerRegistry.instance().addMapLayer(newLayer)
      else:
        QMessageBox.warning(self,
                            self.tr("Can't open file"),
                            self.tr("Error loading output VRT-file:\n%s") % (unicode(self.outputFile))
                           )

  def processInterrupted(self):
    self.restoreGui()

  def stopProcessing(self):
    if self.workThread != None:
      self.workThread.stop()
      self.workThread = None

  def restoreGui(self):
    self.progressBar.setFormat("%p%")
    self.progressBar.setRange(0, 1)
    self.progressBar.setValue(0)

    self.buttonBox.rejected.connect(self.reject)
    self.btnClose.clicked.disconnect(self.stopProcessing)
    self.btnClose.setText(self.tr("Close"))
    self.btnOk.setEnabled(True)

  def selectDir(self):
    settings = QSettings("NextGIS", "UMD")
    lastDir = settings.value("lastProjectDir", ".")
    outPath = QFileDialog.getExistingDirectory(self,
                                                self.tr("Select directory"),
                                                lastDir,
                                                QFileDialog.ShowDirsOnly
                                               )
    if outPath == "":
      return

    self.leMaskFile.setText(outPath)
    settings.setValue("lastProjectDir", Dir(outPath).absolutePath())
