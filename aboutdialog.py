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

from ui_aboutdialogbase import Ui_Dialog

import resources_rc

class AboutDialog(QDialog, Ui_Dialog):
  def __init__(self):
    QDialog.__init__(self)
    self.setupUi(self)

    self.btnHelp = self.buttonBox.button(QDialogButtonBox.Help)

    cfg = ConfigParser.SafeConfigParser()
    cfg.read(os.path.join(os.path.dirname(__file__), "metadata.txt"))
    version = cfg.get("general", "version")

    self.lblLogo.setPixmap(QPixmap(":/icons/new.png"))
    self.lblVersion.setText(self.tr("Version: %s") % (version))
    doc = QTextDocument()
    doc.setHtml(self.getAboutText())
    self.textBrowser.setDocument(doc)
    self.textBrowser.setOpenExternalLinks(True)

    self.buttonBox.helpRequested.connect(self.openHelp)

  def reject(self):
    QDialog.reject(self)

  def openHelp(self):
      QDesktopServices.openUrl(QUrl("http://glad.geog.umd.edu/qgis"))

  def getAboutText(self):
      return self.tr(
      """
      <p>The Landsat time-sequential metric visualization and classification
      module was developed by the Global Land Analysis & Discovery (GLAD) team
      at the University of Maryland, College Park, USA and the NEXTGIS R&amp;D
      Company, Moscow, Russia. This module is designed to work with tiled
      Landsat composite data produced by the GLAD team.</p>
      <p>The classification module is built on the basis of open source tools:
      Minimalist GNU for Windows (licensed by GNU General Public License);
      Geospatial Data Abstraction Library (licensed by Open Source Geospatial
      Foundation); Classification and Regression Trees (author: Brian Ripley).
      The visualization and classification module is distributed by
      <a href="http://glad.geog.umd.edu/">glad.geog.umd.edu</a>. You are free to
      use, modify and copy this package as long as you credit the code source.
      The module is distributed without warranty of any kind.</p>
      <p>Suggested reference: "The Landsat time-sequential metric visualization
      and classification tool for QGIS developed by the Global Land Analysis
      &amp; Discovery (GLAD) team at the University of Maryland and the NEXTGIS
      R&amp;D Company and available from
      <a href="http://glad.geog.umd.edu/qgis">http://glad.geog.umd.edu/qgis</a>".</p>
      <p>Product developers: Alexander Bruy; Dmitry Baryshnikov; Maxim Dubinin;
      Junchang Ju; Alexander Krylov; Matthew Hansen; Peter Potapov.</p>
      <p>For updates, manuals and tutorials please visit
      <a href="http://glad.geog.umd.edu/qgis">http://glad.geog.umd.edu/qgis</a>.</p>
      <p>For Landsat time-sequential metric data sets visit
      <a href="http://glad.geog.umd.edu/data">http://glad.geog.umd.edu/data</a>.</p>
      """
      )
