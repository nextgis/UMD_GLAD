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
from PyQt4.QtGui import *

from qgis.core import *

import umdprojectdialog
import umdmosaicdialog
import umdclassificationdialog
import aboutdialog

import resources_rc

class UmdPlugin:
  def __init__(self, iface):
    self.iface = iface

    try:
      self.QgisVersion = unicode(QGis.QGIS_VERSION_INT)
    except:
      self.QgisVersion = unicode(QGis.qgisVersion)[ 0 ]

    # For i18n support
    userPluginPath = QFileInfo(QgsApplication.qgisUserDbFilePath()).path() + "/python/plugins/umd"
    systemPluginPath = QgsApplication.prefixPath() + "/python/plugins/umd"

    overrideLocale = QSettings().value("locale/overrideFlag", QVariant(False)).toBool()
    if not overrideLocale:
      localeFullName = QLocale.system().name()
    else:
      localeFullName = QSettings().value("locale/userLocale", QVariant("")).toString()

    if QFileInfo(userPluginPath).exists():
      translationPath = userPluginPath + "/i18n/umd_" + localeFullName + ".qm"
    else:
      translationPath = systemPluginPath + "/i18n/umd_" + localeFullName + ".qm"

    self.localePath = translationPath
    if QFileInfo(self.localePath).exists():
      self.translator = QTranslator()
      self.translator.load(self.localePath)
      QCoreApplication.installTranslator(self.translator)

    self.metrics = None
    self.dirs = None

  def initGui(self):
    if int(self.QgisVersion) < 10900:
      qgisVersion = str(self.QgisVersion[ 0 ]) + "." + str(self.QgisVersion[ 2 ]) + "." + str(self.QgisVersion[ 3 ])
      QMessageBox.warning(self.iface.mainWindow(),
                           QCoreApplication.translate("UMD", "Error"),
                           QCoreApplication.translate("UMD", "Quantum GIS %1 detected.\n").arg(qgisVersion) +
                           QCoreApplication.translate("UMD", "This version of UMD requires at least QGIS version 1.9.0. Plugin will not be enabled."))
      return None

    self.actionNew = QAction(QCoreApplication.translate("UMD", "Create new project"), self.iface.mainWindow())
    self.actionNew.setIcon(QIcon(":/icons/umd.png"))
    self.actionNew.setWhatsThis("Create new or edit current UMD project")

    self.actionMosaic = QAction(QCoreApplication.translate("UMD", "Create mosaic"), self.iface.mainWindow())
    self.actionMosaic.setIcon(QIcon(":/icons/mosaic.png"))
    self.actionMosaic.setWhatsThis("Create mosaic from tiles")

    self.actionClassification = QAction(QCoreApplication.translate("UMD", "Run classification"), self.iface.mainWindow())
    #self.actionClassification.setIcon(QIcon(":/icons/mosaic.png"))
    self.actionClassification.setWhatsThis("Run classification process")

    self.actionAbout = QAction(QCoreApplication.translate("UMD", "About UMD..."), self.iface.mainWindow())
    self.actionAbout.setIcon(QIcon(":/icons/about.png"))
    self.actionAbout.setWhatsThis("About UMD")

    self.iface.addPluginToMenu(QCoreApplication.translate("UMD", "UMD"), self.actionNew)
    self.iface.addPluginToMenu(QCoreApplication.translate("UMD", "UMD"), self.actionMosaic)
    self.iface.addPluginToMenu(QCoreApplication.translate("UMD", "UMD"), self.actionClassification)
    self.iface.addPluginToMenu(QCoreApplication.translate("UMD", "UMD"), self.actionAbout)

    self.toolBar = self.iface.addToolBar(QCoreApplication.translate("UMD", "UMD tools"))
    self.toolBar.setObjectName("UMD tools")
    self.toolBar.addAction(self.actionNew)
    self.toolBar.addAction(self.actionMosaic)
    self.toolBar.addAction(self.actionClassification)

    self.actionNew.triggered.connect(self.newProject)
    self.actionMosaic.triggered.connect(self.createMosaic)
    self.actionClassification.triggered.connect(self.runClassification)
    self.actionAbout.triggered.connect(self.about)

  def unload(self):
    self.iface.removePluginMenu(QCoreApplication.translate("UMD", "UMD"), self.actionNew)
    self.iface.removePluginMenu(QCoreApplication.translate("UMD", "UMD"), self.actionMosaic)
    self.iface.removePluginMenu(QCoreApplication.translate("UMD", "UMD"), self.actionClassification)
    self.iface.removePluginMenu(QCoreApplication.translate("UMD", "UMD"), self.actionAbout)

    del self.toolBar

  def newProject(self):
    d = umdprojectdialog.UmdProjectDialog(self)
    d.show()
    d.exec_()

  def createMosaic(self):
    d = umdmosaicdialog.UmdMosaicDialog(self)
    d.show()
    d.exec_()

  def runClassification(self):
    d = umdclassificationdialog.UmdClassificationDialog(self, self.metrics, self.dirs)
    d.show()
    d.exec_()

  def about(self):
    d = aboutdialog.AboutDialog()
    d.exec_()
