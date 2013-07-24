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

import mosaicthread

from ui_umdmosaicdialogbase import Ui_Dialog

class UmdMosaicDialog(QDialog, Ui_Dialog):
  def __init__(self, plugin):
    QDialog.__init__(self)
    self.setupUi(self)

    self.plugin = plugin
    self.iface = plugin.iface

    self.btnOk = self.buttonBox.button(QDialogButtonBox.Ok)
    self.btnClose = self.buttonBox.button(QDialogButtonBox.Close)

    self.workThread = None
    self.model = QStandardItemModel()
    self.filterModel = QSortFilterProxyModel()

    self.btnBrowse.clicked.connect(self.selectOutput)

    self.manageGui()

  def manageGui(self):
    self.filterModel.setSourceModel(self.model)
    self.lstMetrics.setModel(self.filterModel)

    settings = QSettings("NextGIS", "UMD")
    dataDir = settings.value("lastDataDir", "")
    self.loadMetrics(unicode(dataDir))
    self.filterModel.sort(0)

  def loadMetrics(self, directory):
    self.model.clear()

    metrics = dict()
    self.usedDirs = []
    fileCount = 0
    template = QRegExp("^[0-9]{3}_[0-9]{3}$")
    for root, dirs, files in os.walk(directory):
      if not template.exactMatch(root[-7:]):
        continue

      names = ["*.vrt", "*.VRT"]
      vrts = QDir(root).entryList(names, QDir.Files)
      for vrt in vrts:
        fName = os.path.normpath(os.path.join(root, unicode(vrt)))
        f = QFile(fName)
        if not f.open(QIODevice.ReadOnly | QIODevice.Text):
          QMessageBox.warning(self,
                              self.tr("Load error"),
                              self.tr("Cannot read file %s:\n%s.") % (fileName, fl.errorString())
                            )
          continue

        if root not in self.usedDirs:
          self.usedDirs.append(root)

        doc = QDomDocument()
        setOk, errorString, errorLine, errorColumn = doc.setContent(f, True)
        f.close()
        if not setOk:
          QMessageBox.warning(self,
                              self.tr("Load error"),
                              self.tr("Parse error at line %d, column %d:\n%s") % (errorLine, errorColumn, errorString)
                            )
          continue

        fileCount += 1

        # parse file
        r = doc.documentElement()
        bands = r.elementsByTagName("VRTRasterBand")
        for i in xrange(0, bands.length()):
          b = bands.at(i)
          e = b.toElement()
          dataType = e.attribute("dataType")
          bandNo = e.attribute("band")
          descr = e.firstChildElement("Description").text()
          if descr not in metrics:
            data = {"type" : dataType,
                    "band" : bandNo,
                    "fileName" : vrt,
                    "count": 1
                   }
            metrics[descr] = data
          else:
            d = metrics[descr]
            if dataType != d["type"]:
              continue
            d["count"] += 1
            metrics[descr] = d

    for k, v in metrics.iteritems():
      if v["count"] != fileCount:
        continue

      item = QStandardItem(k)
      item.setCheckable(True)
      item.setData(v["type"], Qt.UserRole + 1)
      item.setData(v["band"], Qt.UserRole + 2)
      item.setData(v["fileName"], Qt.UserRole + 3)
      self.model.appendRow(item)

  def selectOutput(self):
    settings = QSettings("NextGIS", "UMD")
    lastDirectory = settings.value("lastVRTDir", ".")

    outPath = QFileDialog.getSaveFileName(self,
                                          self.tr("Select directory"),
                                          lastDirectory,
                                          self.tr("Virtual raster (*.vrt *.VRT)")
                                        )
    if outPath == "":
      return

    if not outPath.lower().endswith(".vrt"):
      outPath += ".vrt"

    self.leOutput.setText(outPath)
    settings.setValue("lastVRTDir", QFileInfo(outPath).absoluteDir().absolutePath())

  def reject(self):
    QDialog.reject(self)

  def accept(self):
    self.outputFileName = self.leOutput.text()
    if self.outputFileName == "":
      QMessageBox.warning(self,
                          self.tr("No output"),
                          self.tr("Output file is not set. Please enter correct filename and try again.")
                        )
      return


    metrics = dict()
    bandTypes = []
    for row in xrange(self.model.rowCount()):
      for col in xrange(self.model.columnCount()):
        item = self.model.item(row, col)
        if item.checkState() == Qt.Checked:
          descr = unicode(item.text())

          if descr not in metrics:
            info = {"band" : item.data(Qt.UserRole + 2),
                    "file" : item.data(Qt.UserRole + 3)
                   }
            bt = unicode(item.data(Qt.UserRole + 1))
            if bt not in bandTypes:
              bandTypes.append(item.data(Qt.UserRole + 1))
            metrics[descr] = info

    if len(metrics) == 0:
      QMessageBox.warning(self,
                          self.tr("No metrics"),
                          self.tr("Metrics for mosaic are not selected. Please select at least one metric an try again.")
                        )
      return

    if len(bandTypes) > 1:
      res = QMessageBox.warning(self,
                                self.tr("Incompatible data types"),
                                self.tr("Selected metrics have different data types. This will cause slow rendering of mosaic. Continue?"),
                                QMessageBox.Yes | QMessageBox.No
                              )
      if res == QMessageBox.No:
        return

    settings = QSettings("NextGIS", "UMD")
    projDir = unicode(settings.value("lastProjectDir", "."))
    cfgPath = os.path.join(projDir, "settings.ini")
    if os.path.exists(cfgPath):
      cfg = ConfigParser.SafeConfigParser()
      cfg.read(cfgPath)

      if not cfg.has_section("Metrics"):
        cfg.add_section("Metrics")

      cfg.set("Metrics", "tiles", ",".join(self.usedDirs))
      cfg.set("Metrics", "metrics", ",".join(metrics.keys()))

      with open(cfgPath, 'wb') as f:
        cfg.write(f)

    self.workThread = mosaicthread.MosaicThread(metrics,
                                                self.usedDirs,
                                                self.outputFileName
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

  def setProgressRange(self, maxValue):
    self.progressBar.setRange(0, maxValue)

  def updateProgress(self):
    self.progressBar.setValue(self.progressBar.value() + 1)

  def processFinished(self):
    self.stopProcessing()
    self.restoreGui()

    if self.chkAddToCanvas.isChecked():
      newLayer = QgsRasterLayer(self.outputFileName, QFileInfo(self.outputFileName).baseName())

      if newLayer.isValid():
        QgsMapLayerRegistry.instance().addMapLayer(newLayer)
      else:
        QMessageBox.warning(self,
                            self.tr("Can't open file"),
                            self.tr("Error loading output VRT-file:\n%s") % (unicode(self.outputFileName))
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
