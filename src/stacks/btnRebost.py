#!/usr/bin/python3
import os
import json
from PySide6.QtWidgets import QLabel, QPushButton,QHBoxLayout
from PySide6.QtCore import Qt,Signal
from PySide6.QtGui import QIcon,QCursor,QMouseEvent,QPixmap,QImage,QPalette,QColor
from QtExtraWidgets import QScreenShotContainer

LAYOUT="appsedu"
class QPushButtonRebostApp(QPushButton):
	clicked=Signal("PyObject","PyObject")
	keypress=Signal()
	def __init__(self,strapp,parent=None,**kwargs):
		QPushButton.__init__(self, parent)
		self.iconSize=kwargs.get("iconSize",128)
		if LAYOUT=="appsedu":
			self.iconSize=self.iconSize/2
		if isinstance(strapp,str):
			self.app=json.loads(strapp)
			if strapp=="{}":
				return(None)
		else:
			self.app=strapp
		self.margin=12
		self.cacheDir=os.path.join(os.environ.get('HOME'),".cache","rebost","imgs")
		self.btn=QPushButton()
		self.btn.setIcon(QIcon.fromTheme("download"))
		if LAYOUT!="appsedu":
			self.btn.setVisible(False)
		if os.path.exists(self.cacheDir)==False:
			os.makedirs(self.cacheDir)
		self.setObjectName("rebostapp")
		self.setAttribute(Qt.WA_StyledBackground, True)
		self.setAttribute(Qt.WA_AcceptTouchEvents)
		self.setAutoFillBackground(True)
		self.setToolTip("<p>{0}</p>".format(self.app.get('summary',self.app.get('name'))))
		text="<strong>{0}</strong><p>{1}</p>".format(self.app.get('name',''),self.app.get('summary'),'')
		self.label=QLabel(text)
		self.label.setWordWrap(True)
		img=self.app.get('icon','')
		self.iconUri=QLabel()
		self.iconUri.setStyleSheet("""QLabel{margin-left: %spx;margin-right:%spx}"""%(self.margin,self.margin))
		self.loadImg(self.app)
		self.setCursor(QCursor(Qt.PointingHandCursor))
		lay=QHBoxLayout()
		lay.addWidget(self.iconUri,0)
		lay.addWidget(self.label,1)
		lay.addWidget(self.btn)
		self.refererApp=None
		self.setDefault(True)
		self.setLayout(lay)
		self.installEventFilter(self)
	#def __init__

	def eventFilter(self,*args):
		ev=args[1]
		if isinstance(ev,QMouseEvent):
			self.activate()
		return(False)

	def updateScreen(self):
		self.setToolTip("<p>{0}</p>".format(self.app.get('summary',self.app.get('name'))))
		text="<strong>{0}</strong><p>{1}</p>".format(self.app.get('name',''),self.app.get('summary'),'')
		self.label.setText(text)
		self._applyDecoration()
	#def updateScreen

	def enterEvent(self,*args):
	   self.setFocus()
	#def enterEvent

	def loadImg(self,app):
		img=app.get('icon','')
		self.aux=QScreenShotContainer()
		self.scr=self.aux.loadScreenShot(img,self.cacheDir)
		icn=''
		if os.path.isfile(img):
			icn=QPixmap.fromImage(QImage(img))
			icn=icn.scaled(self.iconSize,self.iconSize,Qt.KeepAspectRatio,Qt.SmoothTransformation)
		elif img=='':
			icn2=QIcon.fromTheme(app.get('pkgname'),QIcon.fromTheme("appedu-generic"))
			icn=icn2.pixmap(self.iconSize,self.iconSize)
		elif "flathub" in img:
			tmp=img.split("/")
			if "icons" in tmp:
				idx=tmp.index("icons")
				prefix=tmp[:idx-1]
				iconPath=os.path.join("/".join(prefix),"active","/".join(tmp[idx:]))
				if os.path.isfile(iconPath):
					icn=QPixmap.fromImage(iconPath)
					icn=icn.scaled(self.iconSize,self.iconSize,Qt.KeepAspectRatio,Qt.SmoothTransformation)
		if icn:
			wsize=self.iconSize
			if "/usr/share/banners/lliurex-neu" in img:
				wsize*=2
			self.iconUri.setPixmap(icn.scaled(wsize,self.iconSize,Qt.KeepAspectRatio,Qt.SmoothTransformation))
		elif img.startswith('http'):
			self.scr.start()
			self.scr.imageLoaded.connect(self.load)
		self._applyDecoration(app)
	#def loadImg

	def _getStats(self,app):
		stats={}
		for bundle,state in app.get("state",{}).items():
			if bundle=="zomando" and state=="0":
				stats["zomando"]=True
			elif state=="0":
				stats["installed"]=True
			
		if "Forbidden" in app.get("categories",[]):
			stats["forbidden"]=True
		if app["name"]==app["pkgname"] and "zomando" in app.get("state",{}):
			if len(app.get("state",{}))==1:
				stats["installed"]=False
		return(stats)
	#def _getStats

	def _getStyle(self,app):
		stats=self._getStats(app)
		style={"bkgColor":"",
			"brdColor":"",
			"frgColor":""}
		lightnessMod=1
		bkgcolor=QColor(QPalette().color(QPalette.Active,QPalette.Base))
		if hasattr(QPalette,"Accent"):
			bkgAlternateColor=QColor(QPalette().color(QPalette.Active,QPalette.Accent))
		else:
			bkgAlternateColor=QColor(QPalette().color(QPalette.Active,QPalette.Highlight))
		fcolor=QColor(QPalette().color(QPalette.Active,QPalette.Text))
		if stats.get("forbidden",False)==True:
			bkgcolor=QColor(QPalette().color(QPalette.Disabled,QPalette.Mid))
			fcolor=QColor(QPalette().color(QPalette.Disabled,QPalette.BrightText))
		elif stats.get("installed",False)==True:
			bkgcolor=bkgAlternateColor
		elif stats.get("zomando",False)==True:
			bkgcolor=bkgAlternateColor
			lightnessMod=50
		bkgcolorHls=bkgcolor.toHsl()
		bkglightness=bkgcolorHls.lightness()*(1+lightnessMod/100)
		if 255<bkglightness:
			bkglightness=bkgcolorHls.lightness()/lightnessMod
		style["bkgColor"]="{0},{1},{2}".format(bkgcolorHls.hue(),
												bkgcolorHls.saturation(),
												bkglightness)
		style["brdColor"]="{0},{1},{2}".format(bkgcolor.hue(),
												bkgcolor.saturation(),
												bkgcolor.lightness()/2)
		style["frgColor"]="{0},{1},{2}".format(fcolor.red(),
												fcolor.green(),
												fcolor.blue())
		style.update(stats)
		return(style)
	#def _getStyle

	def _applyDecoration(self,app={},forbidden=False,installed=False):
		if app=={}:
			app=self.app
		style=self._getStyle(app)
		brdWidth=6
		if LAYOUT=="appsedu":
			brdWidth=1
		self.setStyleSheet("""#rebostapp {
			background-color: hsl(%s); 
			border-color: hsl(%s); 
			border-style: solid; 
			border-width: 1px; 
			border-radius: 5px;
			}
			#rebostapp:focus:!pressed {
				border-width:%spx;
				}
			QLabel{
				color: rgb(%s);
			}
			"""%(style["bkgColor"],style["brdColor"],brdWidth,style["frgColor"]))
		if style.get("forbidden",False)==True:
			self.iconUri.setEnabled(False)
			self.btn.setEnabled(False)
	#def _applyDecoration

	def _removeDecoration(self):
		self.setObjectName("")
		self.setStyleSheet("")
	#def _removeDecoration
	
	def load(self,*args):
		img=args[0]
		self.iconUri.setPixmap(img.scaled(self.iconSize,self.iconSize))
	#def load
	
	def activate(self):
		self.clicked.emit(self,self.app)
	#def activate

	def keyPressEvent(self,ev):
		if ev.key() in [Qt.Key_Return,Qt.Key_Enter,Qt.Key_Space]:
			self.clicked.emit(self,self.app)
		else:
			self.keypress.emit()
			ev.ignore()
		return True
	#def keyPressEvent(self,ev):

	def mousePressEvent(self,*args):
		self.clicked.emit(self,self.app)
	#def mousePressEvent

	def setApp(self,app):
		self.app=app
#class QPushButtonRebostApp