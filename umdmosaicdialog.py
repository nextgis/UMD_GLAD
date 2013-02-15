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
    self.filterModel = QSortFilterProxyModel()

    self.btnBrowse.clicked.connect(self.selectOutput)

    self.manageGui()

  def manageGui(self):
    self.filterModel.setSourceModel(self.model)
    self.lstMetrics.setModel(self.filterModel)

    settings = QSettings("NextGIS", "UMD")
    dataDir = settings.value("lastDataDir", "").toString()
    self.loadMetrics(unicode(dataDir))
    self.filterModel.sort(0)

  def loadMetrics(self, directory):
    self.model.clear()

    metrics = dict()
    self.usedDirs = []
    fileCount = 0
    template = QRegExp("^[0-9]{3}_[0-9]{3}$")
    for root, dirs, files in os.walk(directory):
      if not template.exactMatch(QString(root[-7:])):
        continue

      names = QStringList() << "*.vrt" << "*.VRT"
      vrts = QDir(root).entryList(names, QDir.Files)
      print "FOUND VRTs", unicode(vrts.join(" "))
      for vrt in vrts:
        fName = os.path.normpath(os.path.join(root,unicode(vrt)))
        f = QFile(fName)
        if not f.open(QIODevice.ReadOnly | QIODevice.Text):
          QMessageBox.warning(self,
                              self.tr("Load error"),
                              self.tr("Cannot read file %1:\n%2.")
                              .arg(fileName)
                              .arg(fl.errorString())
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
                              self.tr("Parse error at line %1, column %2:\n%3")
                              .arg(errorLine)
                              .arg(errorColumn)
                              .arg(errorString)
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


    metrics = dict()
    bandTypes = []
    for row in xrange(self.model.rowCount()):
      for col in xrange(self.model.columnCount()):
        item = self.model.item(row, col)
        if item.checkState() == Qt.Checked:
          descr = unicode(item.text())

          if descr not in metrics:
            info = {"band" : item.data(Qt.UserRole + 2).toString(),
                    "file" : item.data(Qt.UserRole + 3).toString()
                   }
            bt = unicode(item.data(Qt.UserRole + 1).toString())
            if bt not in bandTypes:
              bandTypes.append(item.data(Qt.UserRole + 1).toString())
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

    print metrics

    # write output
    lstMosaic = []
    lstBands = []
    for k, v in metrics.iteritems():
      for d in self.usedDirs:
        tmp = os.path.join(d, unicode(v["file"]))
        print "VRT PATH", tmp
        lstMosaic.append(tmp)
        if v["band"] not in lstBands:
          lstBands.append(v["band"])

    # save filepaths to tmp file
    tmpFile = QTemporaryFile()
    #tmpFile = QFile("/tmp/mytempfile.txt")
    if not tmpFile.open(QIODevice.WriteOnly | QIODevice.Text):
      return

    out = QTextStream(tmpFile)
    for i in lstMosaic:
      out << i << "\n"

    # now we can run gdalbuildvrt
    self.process = QProcess(self)
    self.process.error.connect(self.processError)
    self.process.finished.connect(self.processFinished)

    self.__setProcessEnvironment(self.process)

    args = QStringList()

    args << "-input_file_list"
    args << tmpFile.fileName()
    for b in lstBands:
      args << "-b"
      args << b
    args << self.leOutput.text()

    self.process.start("/opt/gdal/bin/gdalbuildvrt", args, QIODevice.ReadOnly)

    if self.process.waitForFinished(-1):
      tmpFile.close()

    # then build overviews for tiles
    for i in lstMosaic:
      args.clear()
      for b in lstBands:
        args << "-b"
        args << b
      args << i
      args << "2 4 8 16"
      self.process.start("/opt/gdal/bin/gdaladdo", args, QIODevice.ReadOnly)

      if self.process.waitForFinished(-1):
        pass

    # and whole mosaic
    #args.clear()
    #args << self.leOutput.text()
    #args << "8 16 32 64 128 256 512 1024 2018"
    #self.process.start("/opt/gdal/bin/gdaladdo", args, QIODevice.ReadOnly)

    #if self.process.waitForFinished(-1):
    #  print "Finished"

  def processError(self, error):
    if error == QProcess.FailedToStart:
      print "Failed to start"
    elif error == QProcess.Crashed:
      print "Crashed"
    else:
      print "Unknown error"

  def processFinished(self, exitCode, status):
    if status == QProcess.CrashExit:
      print "crash"

    msg = QString.fromLocal8Bit(self.process.readAllStandardError())
    if msg.isEmpty():
      msg = QString.fromLocal8Bit(self.process.readAllStandardOutput())

    print unicode(msg)

    self.process.kill()

  def __setProcessEnvironment(self, process):
    envVars = {
               "GDAL_FILENAME_IS_UTF8" : "NO",
               "LD_LIBRARY_PATH" : "/opt/gdal/lib"
              }

    sep = os.pathsep

    for name, value in envVars.iteritems():
      if value is None or value == "":
        continue

      envval = os.getenv(name)
      if envval is None or envval == "":
        envval = unicode(value)
      elif not QString(envval).split(sep).contains(value, Qt.CaseInsensitive):
        envval += "%s%s" % (sep, unicode(value))
      else:
        envval = None

      if envval is not None:
        os.putenv(name, envval)
