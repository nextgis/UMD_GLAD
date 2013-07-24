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
  processError = pyqtSignal()
  processFinished = pyqtSignal()
  processInterrupted = pyqtSignal()
  logMessage = pyqtSignal(str)

  def __init__(self, outputFile):
    QThread.__init__(self, QThread.currentThread())
    self.mutex = QMutex()
    self.stopMe = 0
    self.interrupted = False

    self.outputFile = outputFile

  def run(self):
    self.mutex.lock()
    self.stopMe = 0
    self.mutex.unlock()

    self.process = QProcess()
    self.__setProcessEnvironment(self.process)

    self.process.error.connect(self.onError)
    self.process.finished.connect(self.onFinished)

    self.runClassification()

    if not self.interrupted:
      self.processFinished.emit()
    else:
      self.processInterrupted.emit()

  def stop(self):
    self.mutex.lock()
    self.stopMe = 1
    self.mutex.unlock()

    QThread.wait(self)

  def runClassification(self):
    settings = QSettings("NextGIS", "UMD")
    projDir = unicode(settings.value("lastProjectDir", "."))
    script = os.path.join(os.path.abspath(projDir), "classification.pl")

    self.process.readyReadStandardOutput.connect(self.getStandardOutput)

    self.process.setProcessChannelMode(QProcess.MergedChannels)
    self.process.setReadChannel(QProcess.StandardOutput)
    self.process.setWorkingDirectory(projDir)

    self.process.start("perl", [script], QIODevice.ReadOnly)

    if self.process.waitForFinished(-1):
      pass

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

  def getStandardOutput(self):
    text = str(self.process.readAllStandardOutput())
    self.logMessage.emit(text)
