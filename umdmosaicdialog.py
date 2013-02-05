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

import os.path

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtXml import *

from qgis.core import *

from ui_umdmosaicdialogbase import Ui_Dialog

class UmdMosaicDialog(QDialog, Ui_Dialog):
  def __init__(self, plugin):
    QDialog.__init__(self)
    self.setupUi(self)

    self.plugin = plugin
    self.iface = plugin.iface

    self.btnOk = self.buttonBox.button(QDialogButtonBox.Ok)
    self.btnClose = self.buttonBox.button(QDialogButtonBox.Close)

    self.model = QStandardItemModel()

    self.btnBrowse.clicked.connect(self.selectOutput)

    self.manageGui()

  def manageGui(self):
    self.lstMetrics.setModel(self.model)

    settings = QSettings("NextGIS", "UMD")
    dataDir = settings.value("lastDataDir", "").toString()
    self.loadMetrics(unicode(dataDir))

  def loadMetrics(self, directory):
    self.model.clear()

    metrics = dict()
    fileCount = 0
    template = QRegExp("^[0-9]{3}_[0-9]{3}$")
    for root, dirs, files in os.walk(directory):
      if not template.exactMatch(QString(root[-7:])):
        print "No match"
        continue

      # try to open VRT and read metrics from it
      fName = os.path.normpath(os.path.join(root, "metric.vrt"))
      f = QFile(fName)
      if not f.open(QIODevice.ReadOnly | QIODevice.Text):
        QMessageBox.warning(self,
                            self.tr("Load error"),
                            self.tr("Cannot read file %1:\n%2.")
                            .arg(fileName)
                            .arg(fl.errorString())
                           )
        continue

      doc = QDomDocument()
      setOk, errorString, errorLine, errorColumn = doc.setContent(f, True)
      if not setOk:
        QMessageBox.warning(self,
                            self.tr("Load error"),
                            self.tr("Parse error at line %1, column %2:\n%3")
                            .arg(errorLine)
                            .arg(errorColumn)
                            .arg(errorString)
                           )
        f.close()
        continue

        fl.close()

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
      self.model.appendRow(item)

  def selectOutput(self):
    settings = QSettings("NextGIS", "UMD")
    lastDirectory = settings.value("lastVRTDir", ".").toString()

    outPath = QFileDialog.getSaveFileName(self,
                                          self.tr("Select directory"),
                                          lastDirectory,
                                          self.tr("Virtual raster (*.vrt *.VRT)")
                                         )
    if outPath.isEmpty():
      return

    if not outPath.toLower().endsWith(".vrt"):
      outPath += ".vrt"

    self.leOutput.setText(outPath)
    settings.setValue("lastVRTDir", QFileInfo(outPath).absoluteDir().absolutePath())

  def accept(self):
    if self.leOutput.text().isEmpty():
      QMessageBox.warning(self,
                          self.tr("No output"),
                          self.tr("Output file is not set. Please enter correct filename and try again.")
                         )
      return

    # check for selected items
    selectedItemsCount = 0
    for row in xrange(self.model.rowCount()):
      for col in xrange(self.model.columnCount()):
        item = self.model.item(row, col)
        if item.checkState() == Qt.Checked:
          selectedItemsCount += 1

    if selectedItemsCount == 0:
      QMessageBox.warning(self,
                          self.tr("No metrics"),
                          self.tr("Metrics for mosaic are not selected. Please select at least one metric an try again.")
                         )
      return

    # write output
