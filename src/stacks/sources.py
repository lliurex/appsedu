#!/usr/bin/python3
import sys
import os,subprocess,time,shutil
from PySide6.QtWidgets import QApplication, QLabel, QWidget, QPushButton,QGridLayout,QTableWidget,QHeaderView,QHBoxLayout,QCheckBox,QProgressBar
from PySide6 import QtGui
from PySide6.QtCore import Qt,QSignalMapper,QSize,QThread,Signal
#from appconfig.appConfigStack import appConfigStack as confStack
from appconfig import manager
from QtExtraWidgets import QStackedWindowItem
from rebost import store
import dbus
import dbus.service
import dbus.mainloop.glib
import json
import random
import gettext
_ = gettext.gettext
QString=type("")

ICON_SIZE=128

i18n={
	"CCACHE":_("Clear cache"),
	"CCACHE_TOOLTIP":_("Remove all files from cache, as per exemple icons or another related stuff"),
	"CONFIG":_("Sources"),
	"DESC":_("Show software sources"),
	"MENU":_("Configure software sources"),
	"NEWDATA":_("Updating info"),
	"PROGRESS":_("Configuring software sources"),
	"RELOAD":_("Reload catalogues"),
	"RELOAD_TOOLTIP":_("Reload info from sources"),
	"RESET":_("Restart database"),
	"RESET_TOOLTIP":_("Forces a refresh of all the info from sources resetting all previous stored information"),
	"RESTARTFAILED":_("Service could not be reloaded. Check credentials"),
	"SOURCE_AI":_("Include appimages"),
	"SOURCE_FP":_("Include flatpaks"),
	"SOURCE_PK":_("Include native packages"),
	"SOURCE_SN":_("Include snaps"),
	"TOOLTIP":_("Configuration")
	}

class thWriteConfig(QThread):
	def __init__(self,parent,appconfig,chkSnap,chkFlatpak,chkApt,chkImage):
		QThread.__init__(self,parent)
		self.parent=parent
		self.appconfig=appconfig
		self.chkSnap=chkSnap
		self.chkFlatpak=chkFlatpak
		self.chkApt=chkApt
		self.chkImage=chkImage
	#def __init__

	def run(self):
		#self.appconfig.level="user"
		#self.appconfig.saveChanges('config','user',level='user')
		data={}
		for wdg in [self.chkSnap,self.chkFlatpak,self.chkApt,self.chkImage]:
			key=""
			if wdg==self.chkApt:
				key="packageKit"
			elif wdg==self.chkFlatpak:
				key="flatpak"
			elif wdg==self.chkImage:
				key="appimage"
			elif wdg==self.chkSnap:
				key="snap"
			data.update({key:wdg.isChecked()})
		if len(data)>0:
			self.appconfig.writeConfig(data)
	#def run
#class thWriteConfig

class reloadCatalogue(QThread):
	def __init__(self,force,parent=None):
		QThread.__init__(self,parent)
		self.rc=store.client()
		self.force=force
	#def __init__

	def run(self):
		self.rc.update(force=self.force)
	#def run
#class reloadCatalogue

class sources(QStackedWindowItem):
	def __init_stack__(self):
		self.dbg=False
		self._debug("sources load")
		self.setProps(shortDesc=i18n.get("MENU"),
			longDesc=i18n.get("DESC"),
			icon="application-x-desktop",
			tooltip=i18n.get("TOOLTIP"),
			index=2,
			visible=True)
		self.index=2
		self.enabled=True
		self.visible=False
		self.rc=store.client()
		self.appconfig=manager.manager(fileformat="json",name="appsedu",relativepath="appsedu")
		#self.appconfig.setConfig(confDirs={'system':os.path.join('/usr/share',"rebost"),'user':os.path.join(os.environ['HOME'],'.config',"rebost")},confFile="store.json")
		self.hideControlButtons()
		self.changed=[]
		self.config={}
		self.app={}
		self.level='user'
		self.oldcursor=self.cursor()
		self.proc=None
		self.conf=None
		dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
	#def __init__

	def __initScreen__(self):
		self.box=QGridLayout()
		self.btnBack=QPushButton()
		icn=QtGui.QIcon.fromTheme("go-previous")
		self.btnBack.setMinimumSize(QSize(int(ICON_SIZE/1.7),int(ICON_SIZE/1.7)))
		self.btnBack.setIcon(icn)
		self.btnBack.setIconSize(self.btnBack.sizeHint())
		self.btnBack.clicked.connect(self._return)
		self.box.addWidget(self.btnBack,0,0,1,1,Qt.AlignTop|Qt.AlignLeft)
		self.chkApt=QCheckBox(i18n.get("SOURCE_PK"))
		self.chkApt.setChecked(True)
		self.chkApt.setEnabled(False)
		self.box.addWidget(self.chkApt,4,1,1,1,Qt.AlignLeft)
		self.chkSnap=QCheckBox(i18n.get("SOURCE_SN"))
		if shutil.which("snap")==None:
			self.chkSnap.setEnabled(False)
		self.box.addWidget(self.chkSnap,1,1,1,1,Qt.AlignLeft)
		self.chkFlatpak=QCheckBox(i18n.get("SOURCE_FP"))
		if shutil.which("flatpak")==None:
			self.chkFlatpak.setEnabled(False)
		self.box.addWidget(self.chkFlatpak,2,1,1,1,Qt.AlignLeft)
		self.chkImage=QCheckBox(i18n.get("SOURCE_AI"))
		self.box.addWidget(self.chkImage,3,1,1,1,Qt.AlignLeft)
		btnClear=QPushButton(i18n.get("CCACHE"))
		btnClear.setToolTip(i18n.get("CCACHE_TOOLTIP"))
		btnClear.clicked.connect(self._clearCache)
		self.box.addWidget(btnClear,1,2,1,1)
		btnReload=QPushButton(i18n.get("RELOAD"))
		btnReload.setToolTip(i18n.get("RELOAD_TOOLTIP"))
		btnReload.clicked.connect(self._reloadCatalogue)
		#self.box.addWidget(btnReload,2,2,1,1)
		btnReset=QPushButton(i18n.get("RESET"))
		btnReset.setToolTip(i18n.get("RESET_TOOLTIP"))
		btnReset.clicked.connect(lambda x:self._resetDB(True))
		self.box.addWidget(btnReset,3,2,1,1)
		self.lblProgress=QLabel(i18n["NEWDATA"])
		self.lblProgress.setVisible(False)
		self.box.addWidget(self.lblProgress,self.box.rowCount(),0,1,3,Qt.AlignCenter|Qt.AlignBottom)
		self.progress=QProgressBar()
		self.progress.setMinimum(0)
		self.progress.setMaximum(0)
		self.box.setRowStretch(self.box.rowCount()-1, 1)
		self.box.addWidget(self.progress,self.box.rowCount(),0,1,3)
		self.progress.setVisible(False)
		self.setLayout(self.box)
		self.btnAccept.clicked.connect(self.writeConfig)
		bus=dbus.SessionBus()
		objbus=bus.get_object("net.lliurex.rebost","/net/lliurex/rebost")
		objbus.connect_to_signal("updatedSignal",self._endReloadCatalogue,dbus_interface="net.lliurex.rebost")
		objbus.connect_to_signal("beginUpdateSignal",self._beginUpdate,dbus_interface="net.lliurex.rebost")
	#def _load_screen

	def _createProgressWidget(self):
		widget=QWidget()
		pg=QProgressBar()
		pg.setTextVisible(True)
		pg.setFormat(i18n.get("PROGRESS"));
		pg.setMinimum(0)
		pg.setMaximum(0)
		lbl=QLabel(i18n["PROGRESS"])
		lay=QGridLayout()
		lay.addWidget(lbl,0,0,1,1)
		lay.addWidget(pg,1,0,1,1)
		widget.setLayout(lay)
		return(widget)

	def _clearCache(self):
		cacheDir=os.path.join(os.environ.get('HOME'),".cache","rebost","imgs")
		self._setEnabled(False)
		if os.path.isdir(cacheDir):
			try:
				shutil.rmtree(cacheDir)
			except Exception as e:
				print("Error removing {0}: {1}".format(cacheDir,e))
		self._setEnabled(True)
	#def _clearCache

	def _setEnabled(self,state=True):
		if state==False:
			cursor=QtGui.QCursor(Qt.WaitCursor)
			self.setCursor(cursor)
			self.progress.setVisible(True)
			self.lblProgress.setVisible(True)
		else:
			self.setCursor(self.oldcursor)
			self.progress.setVisible(False)
			self.lblProgress.setVisible(False)
		for wdg in self.findChildren(QPushButton):
			wdg.setEnabled(state)
		for wdg in self.findChildren(QCheckBox):
			wdg.setEnabled(state)
		#QApplication.processEvents()
	#def _setEnabled

	def _resetDB(self,refresh=False):
		if refresh==True:
			if self.changes:
				self.writeConfig()
		self.btnBack.clicked.connect(self.btnBack.text)
		self.changes=False
		self._setEnabled(False)
		QApplication.processEvents()
		self._reloadCatalogue(True)
	#def _resetDB

	def _beginUpdate(self):
		self._setEnabled(False)
	#def _beginUpdate
		
	def _reloadCatalogue(self,force=False):
		self.btnBack.clicked.connect(self.btnBack.text)
		self.proc=reloadCatalogue(force)
		self.proc.start()
	#def _reloadCatalogue

	def _endReloadCatalogue(self,*args,**kwargs):
		if self.proc!=None:
			if self.proc.isRunning():
				self.proc.wait()
		if self.conf!=None:
			if self.conf.isRunning():
				self.config.wait()
#		self.rc=None
#		try:
#			self.rc=store.client()
#		except:
#			time.sleep(1)
#			try:
#				self.rc=store.client()
#			except:
#				print("UNKNOWN ERROR")
		self._setEnabled(True)
		self.updateScreen()
		self.progress.setVisible(False)
		self.lblProgress.setVisible(False)
	#def _endreloadCatalogue

	def _return(self):
		cursor=QtGui.QCursor(Qt.WaitCursor)
		self.setCursor(cursor)
		self.app={}
		self.parent.setCurrentStack(1,parms="1")
		self.setCursor(self.oldcursor)
	#def _return

	def updateScreen(self):
		self.changes=True
		self.refresh=True
		self.config=self.appconfig.getConfig()
		self.chkSnap.setChecked(True)
		self.chkFlatpak.setChecked(True)
		self.chkImage.setChecked(True)
		for key,value in self.config.get(self.level,{}).items():
			if key=="packageKit":
				#self.chkApt.setChecked(value)
				self.chkApt.setChecked(True)
			if key=="snap":
				self.chkSnap.setChecked(value)
			if key=="flatpak":
				self.chkFlatpak.setChecked(value)
			if key=="appimage":
				self.chkImage.setChecked(value)
	#def _udpate_screen

	def _updateConfig(self,key):
		pass

	def writeConfig(self):
		self.conf=thWriteConfig(self,self.appconfig,self.chkSnap,self.chkFlatpak,self.chkApt,self.chkImage)
		self.conf.finished.connect(self._endWriteConfig)
		self.conf.start()
	#def writeConfig

	def _endWriteConfig(self):
		self.conf.wait()

