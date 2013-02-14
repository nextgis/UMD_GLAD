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
import platform

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

class Executor(QObject):
  error = pyqtSignal(int)
  finished = pyqtSignal(int, int)

  def __init__(self, command="", arguments=QStringList()):
    QObject.__init__(self)

    self.command = command
    self.arguments = arguments

    self.process = QProcess(self)
    self.__setProcessEnvironment(self.process)

    self.process.error.connect(self.processError)
    self.process.finished.connect(self.processFinished)

  def setCommand(self, command):
    self.command = command

  def setArguments(self, arguments):
    self.arguments = arguments

  def start(self):
    self.process.start(self.command, self.arguments, QIODevice.ReadOnly)

  def processError(self, error):
    self.error.emit(error)

  def processFinished(self, exitCode, status):
    self.finished.emit(exitCode, status)

  def stop(self):
    self.process.kill()

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
        envval = unicode(val)
      elif not QString(envval).split(sep).contains(value, Qt.CaseInsensitive):
        envval += "%s%s" % (sep, unicode(value))
      else:
        envval = None

      if envval is not None:
        os.putenv(name, envval)
