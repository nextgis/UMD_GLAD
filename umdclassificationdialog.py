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
from PyQt4.QtXml import *

from qgis.core import *

import classificationthread
import umd_utils as utils

from ui.ui_umdclassificationdialogbase import Ui_Dialog

class UmdClassificationDialog(QDialog, Ui_Dialog):
  def __init__(self, plugin):
    QDialog.__init__(self)
    self.setupUi(self)

    self.plugin = plugin
    self.iface = plugin.iface

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

    projPath = QgsProject.instance().fileName()
    cfgPath = os.path.join(QFileInfo(projPath).absolutePath(), "settings.ini")
    if os.path.exists(cfgPath):
      cfg = ConfigParser.SafeConfigParser()
      cfg.read(cfgPath)

      self.outputFile = os.path.join(cfg.get("general", "projpath"), "out.vrt")

      cfg.set("general", "maskfile", self.leMaskFile.text())
      cfg.set("general", "resultfile", self.outputFile)
      if self.rbTarget.isChecked():
        cfg.set("general", "maskclass", "1")
      else:
        cfg.set("general", "maskclass", "2")

      with open(cfgPath, 'wb') as f:
        cfg.write(f)

    self.workThread = classificationthread.ClassificationThread(
                                                                self.outputFile
                                                               )

    self.workThread.logMessage.connect(self.updateMessages)
    self.workThread.processFinished.connect(self.processFinished)
    self.workThread.processInterrupted.connect(self.processInterrupted)

    self.btnOk.setEnabled(False)
    self.btnClose.setText(self.tr("Cancel"))
    self.buttonBox.rejected.disconnect(self.reject)
    self.btnClose.clicked.connect(self.stopProcessing)

    self.edLog.setTextInteractionFlags(Qt.NoTextInteraction)

    # if classification result already there — unload it
    layer = utils.getRasterLayerByName(QFileInfo(self.outputFile).baseName())
    if layer is not None:
      QgsMapLayerRegistry.instance().removeMapLayer(layer.id())

    self.workThread.start()

  def updateMessages(self, message):
    self.edLog.insertPlainText(message)

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
    self.buttonBox.rejected.connect(self.reject)
    self.btnClose.clicked.disconnect(self.stopProcessing)
    self.btnClose.setText(self.tr("Close"))

    self.edLog.setTextInteractionFlags(Qt.TextSelectableByMouse)

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
    settings.setValue("lastProjectDir", QDir(outPath).absolutePath())
