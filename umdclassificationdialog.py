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

      self.metrics = cfg.get("Metrics", "metrics").split(",")
      self.usedDirs = cfg.get("Metrics", "tiles").split(",")

    self.btnSelectMask.clicked.connect(self.selectFile)
    self.btnSelectOutput.clicked.connect(self.selectFile)

    self.btnOk = self.buttonBox.button(QDialogButtonBox.Ok)
    self.btnClose = self.buttonBox.button(QDialogButtonBox.Close)

    self.workThread = None

    self.manageGui()

  def manageGui(self):
    pass

  def reject(self):
    QDialog.reject(self)

  def accept(self):
    # TODO: check for necessary vector layers

    maskFile = self.leMaskFile.text()
    if maskFile == "":
      QMessageBox.warning(self,
                          self.tr("File not specified"),
                          self.tr("Mask file is not set. Please specify correct filename and try again")
                         )
      return

    outputFile = self.leMaskFile.text()
    if outputFile == "":
      QMessageBox.warning(self,
                          self.tr("File not specified"),
                          self.tr("Output file is not set. Please specify correct filename and try again")
                         )
      return

    self.workThread = classificationthread.ClassificationThread(self.metrics,
                                                                self.usedDirs,
                                                                maskFile,
                                                                outputFile
                                                               )

    self.workThread.rangeChanged.connect(self.setProgressRange)
    self.workThread.updateProgress.connect(self.updateProgress)
    self.workThread.processFinished.connect(self.processFinished)
    self.workThread.processInterrupted.connect(self.processInterrupted)

    self.btnOk.setEnabled(False)
    self.btnClose.setText(self.tr("Cancel"))
    self.buttonBox.rejected.disconnect(self.reject)
    self.btnClose.clicked.connect(self.stopProcessing)

    self.workThread.start()

  def setProgressRange(self, message, maxValue):
    self.progressBar.setFormat(message)
    self.progressBar.setRange(0, maxValue)

  def updateProgress(self):
    self.progressBar.setValue(self.progressBar.value() + 1)

  def processFinished(self):
    self.stopProcessing()
    self.restoreGui()

    if self.chkAddMask.isChecked():
      maskFile = self.leMaskFile.text()
      newLayer = QgsRasterLayer(maskFile, QFileInfo(maskFile).baseName())

      if newLayer.isValid():
        QgsMapLayerRegistry.instance().addMapLayers([newLayer])
      else:
        QMessageBox.warning(self,
                            self.tr("Can't open file"),
                            self.tr("Error loading output VRT-file:\n%s") % (unicode(maskFile))
                           )

    if self.chkAddOutput.isChecked():
      outputFile = self.leOutputFile.text()
      newLayer = QgsRasterLayer(outputFile, QFileInfo(outputFile).baseName())

      if newLayer.isValid():
        QgsMapLayerRegistry.instance().addMapLayers([newLayer])
      else:
        QMessageBox.warning(self,
                            self.tr("Can't open file"),
                            self.tr("Error loading output VRT-file:\n%s") % (unicode(outputFile))
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

  def selectFile(self):
    senderName = self.sender().objectName()

    settings = QSettings("NextGIS", "UMD")
    lastDir = settings.value("lastRasterDir", ".")
    fileName = QFileDialog.getSaveFileName(self,
                                           self.tr("Save file"),
                                           lastDir,
                                           self.tr("Virtual raster (*.vrt *.VRT)")
                                          )
    if fileName == "":
      return

    if not fileName.lower().endswith(".vrt"):
      fileName += ".vrt"

    if senderName == "btnSelectMask":
      self.leMaskFile.setText(fileName)
    elif senderName == "btnSelectOutput":
      self.leOutputFile.setText(fileName)

    settings.setValue("lastRasterDir", QFileInfo(fileName).absoluteDir().absolutePath())
