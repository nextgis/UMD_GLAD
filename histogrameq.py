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

from PyQt4.QtCore import *

from qgis.core import *

HISTOGRAM_BINS = 256

class HistogramEq(QgsRasterInterface):
  myHistogram = None

  def bandCount(self):
    return self.input().bandCount()

  def dataType(self, bandNo):
    return self.input().dataType(bandNo)

  def prepare(self):
    self.myHistogram = self.input().histogram(1,
                                              HISTOGRAM_BINS,
                                              float("nan"),
                                              float("nan"),
                                              QgsRectangle(),
                                              0,
                                              False
                                             )

    if self.dataType(1) != QGis.Byte:
      self.binXStep = (self.myHistogram.maximum - self.myHistogram.minimum) / HISTOGRAM_BINS
      self.binX = self.myHistogram.minimum + self.binXStep / 2.0
    else:
      self.binXStep = 1
      self.binX = 0

    self.histLUT = dict()
    for i in xrange(HISTOGRAM_BINS):
      binValue = self.myHistogram.histogramVector().at(i)
      self.histLUT[bixX] = binValue
      self.binX += self.binXStep

    self.cdfLUT = dict()
    for k, v in self.histLUT.iteritems():
      for i in xrange(k):
        self.cdfLUT[k] += self.histLUT[i]

    self.minValue = min(self.cdfLUT.values())
    self.pixelCount = self.input().xSize() * self.input().ySize() - self.minValue

  def block(self, bandNo, extent, width, height):
    print "self.myHistogram", self.myHistogram
    if self.myHistogram is None:
      print "prepare"
      self.prepare()
    print "self.myHistogram after", self.myHistogram

    data = self.input().block(bandNo, extent, width, height)

    for i in range(0, width * height):
      v = data.value(i)
      #nv = round((self.cdfLUT[v] - self.minValue) * 255 / self.pixelCount)
      #data.setValue(i, v + 5)

    return data
