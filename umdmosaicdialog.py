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
    mDirs = []
    self.mH = []
    self.mV = []
    fileCount = 0
    template = QRegExp("^[0-9]{3}_[0-9]{3}$")
    for root, dirs, files in os.walk(directory):
      if not template.exactMatch(QString(root[-7:])):
        continue

      # get indexes
      h = int(root[-7:-4])
      v = int(root[-3:])
      if h not in self.mH:
        self.mH.append(h)
      if v not in self.mV:
        self.mV.append(v)

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

      mDirs.append(root)

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

    settings = QSettings("NextGIS", "UMD")
    dataDir = settings.value("lastDataDir", "").toString()

    # read tile dimensions and prjection from settings
    projDir = unicode(settings.value("lastProjectDir", ".").toString())
    if os.path.exists(os.path.join(projDir, "settings.ini")):
        cfg = ConfigParser.SafeConfigParser()
        cfg.read(os.path.join(projDir, "settings.ini"))
        self.ulx = cfg.getint("General", "ulxgrid")
        self.uly = cfg.getint("General", "ulygrid")
        self.tilesize = cfg.getint("General", "tileside")
        self.tilebuffer = cfg.getint("General", "tilebuffer")
        self.pixelsize = cfg.getint("General", "pixelsize")

    # calculate geotransform
    x = self.ulx + min(self.mH) * self.pixelsize * self.tilesize - self.tilebuffer * self.pixelsize
    y = self.uly - min(self.mV) * self.pixelsize * self.tilesize + self.tilebuffer * self.pixelsize

    gt = [str(x),
          str(self.pixelsize),
          str(0),
          str(y),
          str(0),
          str(-self.pixelsize)
         ]

    # calculate mosaic dimensions
    mosaicWidth = self.tilesize * len(self.mH)
    mosaicHeight = self.tilesize * len(self.mV)

    # check for selected items and also sort them by datatype
    bandTypes = dict()
    selectedItemsCount = 0
    for row in xrange(self.model.rowCount()):
      for col in xrange(self.model.columnCount()):
        item = self.model.item(row, col)
        if item.checkState() == Qt.Checked:
          selectedItemsCount += 1

          dt = item.data(Qt.UserRole + 1).toString()
          if dt not in bandTypes:
            bandTypes[dt] = [item]
          else:
            bandTypes[dt].append(item)

    if selectedItemsCount == 0:
      QMessageBox.warning(self,
                          self.tr("No metrics"),
                          self.tr("Metrics for mosaic are not selected. Please select at least one metric an try again.")
                         )
      return

    # write output
    print bandTypes

    for k, v in bandTypes:
      print "Create VRT for type", k

      f = QFile(self.leOutput.text())
      if not f.open(QIODeice.WriteOnly | QIODevice.Text):
        print "Can't open file"
        return

      s = QTextStream(f)
      s << QString("<VRTDataset rasterXSize=\"%1\" rasterYSize=\"%2\">\n").arg(mosaicWidth).arg(mosaicHeight)
      s << QString("<SRS>%1</SRS>\n").arg("PROJCS[&quot;Earth_Sinusoidal&quot;,GEOGCS[&quot;Normal Sphere&quot;,DATUM[&quot;Normal Sphere&quot;,SPHEROID[&quot;Normal Sphere&quot;,6370997,0]],PRIMEM[&quot;Greenwich&quot;,0],UNIT[&quot;Decimal_Degree&quot;,0.017453]],PROJECTION[&quot;Sinusoidal&quot;],PARAMETER[&quot;False_Easting&quot;,0],PARAMETER[&quot;False_Northing&quot;,0],PARAMETER[&quot;Central_Meridian&quot;,-60],PARAMETER[&quot;Longitude_of_center&quot;,-60],UNIT[&quot;Meter&quot;,1]]")
      s << QString("<GeoTransform>%1</GeoTransform>\n").arg(gt)

      bandNum = 1
      for i in v:
        print "processing metric", i.text()
        s << QString("<VRTRasterBand dataType=\"%1\" band=\"%2\">\n").arg(k).arg(bandNum)
        self.__createBand(s, k, i, dataDir)
        s << QString("</VRTRasterBand>\n")
        bandNum += 1

      s << QString("</VRTDataset>\n")
      f.close()

  def __createBand(self, stream, dataType, metric, rootDir):
    template = QRegExp("^[0-9]{3}_[0-9]{3}$")
    for root, dirs, files in os.walk(directory):
      if not template.exactMatch(QString(root[-7:])):
        continue

      fName = os.path.normpath(os.path.join(root, "mymetric.vrt"))

      stream << "<SimpleSource>\n"
      stream << QString("<SourceFilename relativeToVRT=\"0\">%1</SourceFilename>\n").arg(fName)
      stream << QString("<SourceBand>%1</SourceBand>\n").arg(metric.data(Qt.UserRole + 2))
      stream << QString("<SourceProperties RasterXSize=\"%1\" RasterYSize=\"%2\" DataType=\"%3\" BlockXSize=\"%4\" BlockYSize=\"%5\"/>\n").arg(self.tilesize).arg(self.tilesize).arg(dataType).arg(self.tilesize).arg(self.tilebuffer / 2)
      stream << QString("<SrcRect xOff=\"%1\" yOff=\"%2\" xSize=\"%3\" ySize=\"%4\"/>\n").arg(0).arg(0).arg(self.tilesize).arg(self.tilesize)
      stream << "</SimpleSource>\n"
