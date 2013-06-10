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

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from osgeo import gdal

from qgis.core import *

import umd_utils as utils

class ClassificationThread(QThread):
  rangeChanged = pyqtSignal(str, int)
  updateProgress = pyqtSignal()

  processError = pyqtSignal()
  processFinished = pyqtSignal()
  processInterrupted = pyqtSignal()

  def __init__(self, metrics, directories, maskFile, outputFile):
    QThread.__init__(self, QThread.currentThread())
    self.mutex = QMutex()
    self.stopMe = 0
    self.interrupted = False

    self.metrics = metrics
    self.directories = directories
    self.maskFile = maskFile
    self.outputFile = outputFile

  def run(self):
    self.mutex.lock()
    self.stopMe = 0
    self.mutex.unlock()

    self.process = QProcess()
    self.__setProcessEnvironment(self.process)

    self.process.error.connect(self.onError)
    self.process.finished.connect(self.onFinished)

    lstFiles = []

    for k, v in self.metrics.iteritems():
      for d in self.directories:
        filePath = os.path.join(unicode(d), unicode(v["file"]))
        lstFiles.append(filePath)

    self.rangeChanged.emit("Rasterization %p%", len(lstFiles) * 3 + 2)

    # prepare and call GDAL commands
    self.createMaskTile(lstFiles)
    if not self.interrupted:
      self.createMosaic(lstFiles)
    if not self.interrupted:
      self.createPyramidsForMosaic()

    # TODO: run classification

    if not self.interrupted:
      self.processFinished.emit()
    else:
      self.processInterrupted.emit()

  def stop(self):
    self.mutex.lock()
    self.stopMe = 1
    self.mutex.unlock()

    QThread.wait(self)

  def createMaskTile(self, lstFiles):
    args = []
    for f in lstFiles:
      # collect some data about tile
      ds = gdal.Open(f)

      xSize = ds.RasterXSize
      ySize = ds.RasterYSize
      gt = ds.GetGeoTransform()
      extent = self.__getExtent(xSize, ySize, gt)

      ds = None

      outPath = os.path.join(unicode(QFileInfo(f).absoluteDir().absolutePath()), unicode(QFileInfo(self.maskFile).baseName()) + ".tif")

      # rasterize target
      args.append("-burn")
      args.append("1")
      args.append("-te")
      args.append(unicode(extent[0]))
      args.append(unicode(extent[1]))
      args.append(unicode(extent[2]))
      args.append(unicode(extent[3]))
      args.append("-ts")
      args.append(unicode(xSize))
      args.append(unicode(ySize))
      args.append("-l")
      args.append("target")
      args.append(unicode(utils.getVectorLayerByName("target").source()))
      args.append(outPath)

      self.process.start("gdal_rasterize", args, QIODevice.ReadOnly)

      if self.process.waitForFinished(-1):
        args.clear()
        self.updateProgress.emit()

      self.mutex.lock()
      s = self.stopMe
      self.mutex.unlock()
      if s == 1:
        self.interrupted = True
        break

      # rasterize background
      args[:] = []
      args.append("-burn")
      args.append("2")
      args.append("-l")
      args.append("background")
      args.append(unicode(utils.getVectorLayerByName("background").source()))
      args.append(outPath)

      self.process.start("gdal_rasterize", args, QIODevice.ReadOnly)

      if self.process.waitForFinished(-1):
        args.clear()
        self.updateProgress.emit()

      self.mutex.lock()
      s = self.stopMe
      self.mutex.unlock()
      if s == 1:
        self.interrupted = True
        break

      # build pyramids
      args = []
      args.append(outPath)
      args.append("2")
      args.append("4")
      args.append("8")
      args.append("16")

      self.process.start("gdaladdo", args, QIODevice.ReadOnly)

      if self.process.waitForFinished(-1):
        args.clear()
        self.updateProgress.emit()

      self.mutex.lock()
      s = self.stopMe
      self.mutex.unlock()
      if s == 1:
        self.interrupted = True
        break

  def createMosaic(self, lstFiles):
    tmpFile = QTemporaryFile()
    if not tmpFile.open(QIODevice.WriteOnly | QIODevice.Text):
      print "I/O error"
      self.interrupted = True
      return

    baseName = unicode(QFileInfo(self.maskFile).baseName()) + ".tif"
    out = QTextStream(tmpFile)
    for f in lstFiles:
      out << os.path.join(unicode(QFileInfo(f).absoluteDir().absolutePath()), baseName) << "\n"

    tmpFile.close()

    args = []
    args.append("-input_file_list")
    args.append(tmpFile.fileName())
    args.append(self.outputFile)

    self.process.start("gdalbuildvrt", args, QIODevice.ReadOnly)

    if self.process.waitForFinished(-1):
      self.updateProgress.emit()

    self.mutex.lock()
    s = self.stopMe
    self.mutex.unlock()
    if s == 1:
      self.interrupted = True

  def createPyramidsForMosaic(self):
    args = []
    args.append(self.outputFile)
    args.append("8")
    args.append("16")
    args.append("32")
    args.append("64")
    args.append("128")
    args.append("256")
    args.append("512")
    args.append("1024")
    args.append("2048")

    self.process.start("gdaladdo", args, QIODevice.ReadOnly)

    if self.process.waitForFinished(-1):
      self.updateProgress.emit()

    self.mutex.lock()
    s = self.stopMe
    self.mutex.unlock()
    if s == 1:
      self.interrupted = True

  def onError(self, error):
    print "process error", error
    self.processError.emit()

  def onFinished(self, exitCode, status):
    print "finished", exitCode, status
    self.processFinished.emit()

  def __setProcessEnvironment(self, process):
    envVars = {
               "GDAL_FILENAME_IS_UTF8" : "NO"
              }

    sep = os.pathsep

    for name, value in envVars.iteritems():
      if value is None or value == "":
        continue

      envval = os.getenv(name)
      if envval is None or envval == "":
        envval = unicode(value)
      elif value.lower() not in envval.lower().split(sep):
        envval += "%s%s" % (sep, unicode(value))
      else:
        envval = None

      if envval is not None:
        os.putenv(name, envval)

  def __getExtent(self, xSize, ySize, gt):
    xMin = gt[0] + gt[1] * 0.0 + gt[2] * 0.0
    yMax = gt[3] + gt[4] * 0.0 + gt[5] * 0.0
    xMax = gt[0] + gt[1] * xSize + gt[2] * ySize
    yMin = gt[3] + gt[4] * xSize + gt[5] * ySize

    return [xMin, yMin, xMax, yMax]
