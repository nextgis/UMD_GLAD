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

from qgis.core import *

class MosaicThread(QThread):
  rangeChanged = pyqtSignal(int)
  updateProgress = pyqtSignal()

  processError = pyqtSignal()
  processFinished = pyqtSignal()
  processInterrupted = pyqtSignal()

  # TODO: also pass flag indicating shoould we build pyramids for mosaic or not
  # Use band types as indicator
  def __init__(self, metrics, directories, fileName):
    QThread.__init__(self, QThread.currentThread())
    self.mutex = QMutex()
    self.stopMe = 0
    self.interrupted = False

    self.metrics = metrics
    self.directories = directories
    self.outputFile = fileName

  def run(self):
    self.mutex.lock()
    self.stopMe = 0
    self.mutex.unlock()

    self.process = QProcess()
    self.__setProcessEnvironment(self.process)

    self.process.error.connect(self.onError)
    self.process.finished.connect(self.onFinished)

    lstFiles = []
    lstBands = []

    for k, v in self.metrics.iteritems():
      if v["band"] not in lstBands:
        lstBands.append(v["band"])

      for d in self.directories:
        filePath = os.path.join(unicode(d), unicode(v["file"]))
        lstFiles.append(filePath)

    self.rangeChanged.emit(len(lstFiles) + 2)

    # prepare and call GDAL commands
    self.createPyramidsForTiles(lstFiles, lstBands)
    if not self.interrupted:
      self.createMosaic(lstFiles, lstBands)
    if not self.interrupted:
      self.createPyramidsForMosaic()

    if not self.interrupted:
      self.processFinished.emit()
    else:
      self.processInterrupted.emit()

  def stop( self ):
    self.mutex.lock()
    self.stopMe = 1
    self.mutex.unlock()

    QThread.wait(self)

  def createPyramidsForTiles(self, lstFiles, lstBands):
    args = []
    for f in lstFiles:
      for band in lstBands:
        args.append("-b")
        args.append(band)

      args.append(f)
      args.append("2")
      args.append("4")
      args.append("8")
      args.append("16")

      self.process.start("gdaladdo", args, QIODevice.ReadOnly)

      if self.process.waitForFinished(-1):
        args[:] = []
        self.updateProgress.emit()

      self.mutex.lock()
      s = self.stopMe
      self.mutex.unlock()
      if s == 1:
        self.interrupted = True
        break

  def createMosaic(self, lstFiles, lstBands):
    tmpFile = QTemporaryFile()
    if not tmpFile.open(QIODevice.WriteOnly | QIODevice.Text):
      print "I/O error"
      self.interrupted = True
      return

    out = QTextStream(tmpFile)
    for f in lstFiles:
      out << f << "\n"

    tmpFile.close()

    args = []
    args.append("-input_file_list")
    args.append(tmpFile.fileName())
    for b in sorted(lstBands, reverse=True):
      args.append("-b")
      args.append(b)
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
    self.processError.emit()

  def onFinished(self, exitCode, status):
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
